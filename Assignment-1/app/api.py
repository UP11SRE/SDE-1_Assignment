# app/api.py

import os
import uuid
import csv
import io
import boto3
import httpx
from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException, Form
from app import db, csv_handler, image_utils
from app.models import CSVRow

router = APIRouter()

# AWS S3 configuration from environment variables
AWS_BUCKET = os.getenv("AWS_BUCKET", "compressimageurls")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Create an S3 client using boto3
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

def upload_to_s3(file_bytes: bytes, destination: str) -> str:

    try:
        s3_client.put_object(
            Bucket=AWS_BUCKET,
            Key=destination,
            Body=file_bytes,
            ContentType="image/jpeg",  # Assuming JPEG compressed images
        )
        public_url = f"https://{AWS_BUCKET}.s3.amazonaws.com/{destination}"
        return public_url
    except Exception as e:
        print(f"Failed to upload to S3: {e}")
        raise

async def trigger_webhook(webhook_url: str, payload: dict):

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            response.raise_for_status()
            print(f"Webhook triggered successfully: {response.status_code}")
        except Exception as e:
            print(f"Error triggering webhook at {webhook_url}: {e}")

@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    webhook_url: str = Form(None),  # Optional webhook URL from the client
    background_tasks: BackgroundTasks = None
):

    if file.content_type != "text/csv":
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV allowed.")

    content = await file.read()
    rows = csv_handler.parse_csv(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV parsing failed or no valid rows found.")

    # Generate a unique request id
    request_id = str(uuid.uuid4())

    # Insert a record into the database to track processing status alongside the webhook URL
    query = "INSERT INTO processing_requests (request_id, status, webhook_url) VALUES ($1, $2, $3)"
    await db.execute_query(query, request_id, "pending", webhook_url)

    # Schedule the background task for image processing
    background_tasks.add_task(process_images, request_id, rows)

    return {"request_id": request_id}

async def process_images(request_id: str, rows: list):

    output_rows = []  # Hold dictionaries for each output CSV row

    for row in rows:
        output_image_urls = []  # List of S3 URLs for compressed images for this row
        # Ensure input image URLs are strings
        input_image_urls = [str(url) for url in row.input_image_urls]

        # Process each input image URL
        for url in input_image_urls:
            try:
                # Compress the image using the image_utils function.
                compressed_image_bytes = image_utils.compress_image(url)
                # Generate a unique filename/destination for the compressed image on S3
                destination = f"images/{uuid.uuid4()}.jpg"
                # Upload the compressed image to S3 and get its public URL
                new_url = upload_to_s3(compressed_image_bytes, destination)
                output_image_urls.append(new_url)
            except Exception as e:
                print(f"Error processing image from {url}: {e}")
                continue

        # Prepare the output row matching the expected CSV format.
        output_rows.append({
            "Serial Number": row.serial_number,
            "Product Name": row.product_name,
            "Input Image Urls": ", ".join(input_image_urls),
            "Output Image Urls": ", ".join(output_image_urls)
        })

    # Write the output CSV using an in-memory string buffer
    output_buffer = io.StringIO()
    fieldnames = ["Serial Number", "Product Name", "Input Image Urls", "Output Image Urls"]
    writer = csv.DictWriter(output_buffer, fieldnames=fieldnames)
    writer.writeheader()
    for output_row in output_rows:
        writer.writerow(output_row)
    csv_content = output_buffer.getvalue()

    # Upload the CSV content to S3 under the "csvfile/" folder
    destination_csv = f"csvfile/{request_id}_output.csv"
    try:
        s3_client.put_object(
            Bucket=AWS_BUCKET,
            Key=destination_csv,
            Body=csv_content,
            ContentType="text/csv",
        )
        csv_s3_url = f"https://{AWS_BUCKET}.s3.amazonaws.com/{destination_csv}"
        print(f"CSV uploaded to S3 at: {csv_s3_url}")
    except Exception as e:
        error_message = f"S3 CSV upload error: {e}"
        print(error_message)
        error_query = "UPDATE processing_requests SET status = $1, error = $2 WHERE request_id = $3"
        await db.execute_query(error_query, "failed", error_message, request_id)
        return

    # Update the processing_requests record with a complete status and the CSV S3 URL.
    update_query = "UPDATE processing_requests SET status = $1, processed_images = $2 WHERE request_id = $3"
    await db.execute_query(update_query, "complete", csv_s3_url, request_id)

    # Fetch the webhook URL if provided
    query_webhook = "SELECT webhook_url FROM processing_requests WHERE request_id = $1"
    result = await db.fetch_query(query_webhook, request_id)
    webhook_url = result[0]["webhook_url"] if result and result[0]["webhook_url"] else None

    # Prepare payload for the webhook with the public S3 URL for the CSV
    payload = {
        "request_id": request_id,
        "status": "complete",
        "output_csv": csv_s3_url,
        "message": "Image processing completed successfully."
    }

    # Trigger webhook if a valid URL is available (e.g. a Pipedream URL)
    if webhook_url:
        await trigger_webhook(webhook_url, payload)
        print(f"Webhook scheduled to be triggered for {webhook_url}")

@router.get("/status/{request_id}")
async def get_status(request_id: str):
   
    query = "SELECT request_id, status, processed_images, error FROM processing_requests WHERE request_id = $1"
    result = await db.fetch_query(query, request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Request ID not found")
    record = result[0]
    return {
        "request_id": record["request_id"],
        "status": record["status"],
        "output_csv": record["processed_images"],
        "error": record["error"]
    }

@router.get("/")
async def greetings():

    return {"message": "Welcome to the image processing API!"}