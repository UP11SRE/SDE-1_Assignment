Project: SDE 1 Assignment Backend

---

Objective:
The project is designed to efficiently process image data from CSV files. The system accepts a CSV file containing product data and a list of input image URLs, compresses the images asynchronously, uploads processed images to AWS S3, and stores the results in an output CSV file. A unique request ID is provided immediately after submission, and a status API along with a webhook mechanism (e.g., via Pipedream) notifies the client upon completion.

---

Features:

1. CSV Upload API:

   - Accepts a CSV file in the following format:
     - Column 1: Serial Number
     - Column 2: Product Name
     - Column 3: Input Image Urls (comma-separated URLs)
   - Validates the CSV formatting.
   - Returns a unique request ID immediately after file submission.

2. Asynchronous Image Processing:

   - Processes image URLs asynchronously, compressing each image by 50% of its original quality.
   - Uploads compressed images to AWS S3 under designated folders (e.g., "images/" for processed images, "csvfile/" for output CSV files).
   - Uses direct SQL queries for database interactions to track processing status and store webhook URLs.

3. Status API:

   - Provides an endpoint to query the processing status using the unique request ID.
   - Returns the status, any error messages, and the S3 public URL to the output CSV file containing both input and output image URLs.

4. Webhook Notification:
   - Optionally accepts a webhook URL during CSV upload.
   - Upon completion of processing, the system triggers the webhook (e.g., with a Pipedream endpoint) by sending a POST request with a JSON payload that includes the request ID, processing status, and the public URL to the output CSV.

---

API Documentation:

1. POST /upload

   - Description: Accepts a CSV file upload and, optionally, a webhook URL.
   - Request:
     - Form-data:
       - file: CSV file (must be of type text/csv).
       - use this csv file for testing : https://drive.google.com/file/d/1oG0fFHU3ttufGO_e7X6pqeGSjBVoNa8L/view?usp=sharing
       - webhook_url (optional): URL to be notified via a webhook when processing is complete.
   - Response:
     - Returns a JSON object containing a unique request_id that can be used to query the status.
   - Example using Postman:
     1. Set the request method to POST and URL to http://<HOST>/upload.
     2. In the form-data, add a file field with the CSV and an optional webhook_url field (for example, a Pipedream URL).
     3. Submit the request and receive a response in the form: { "request_id": "unique-request-id" }.

2. GET /status/{request_id}
   - Description: Retrieves the processing status, output CSV URL, and any error messages for a given request_id.
   - Request:
     - Path Parameter: request_id
   - Response:
     - Returns a JSON object containing:
       - request_id
       - status (e.g., pending, complete, failed)
       - output_csv (public S3 URL to the output CSV file)
       - Example CSV file: https://compressimageurls.s3.ap-south-1.amazonaws.com/csvfile/1d2a2ffe-cf50-43d1-ab6f-ed09a003582c_output.csv
       - error (if any)
   - Example using Curl:
     curl http://<HOST>/status/unique-request-id

---

Asynchronous Workers Documentation:
The system employs background worker functions to handle CSV data and image processing asynchronously. Key worker functions include:

1. process_images(request_id, rows):

   - Role: Orchestrates the entire image processing flow.
   - Functions:
     - Parses each row of the CSV to extract input image URLs and product details.
     - Compresses each image using the image_utils.compress_image(url) function.
     - Uploads each compressed image to AWS S3 and collects the public URLs.
     - Generates an output CSV, in memory, with the following columns: Serial Number, Product Name, Input Image Urls, and Output Image Urls.
     - Uploads the generated CSV to AWS S3 under the "csvfile/" folder and obtains a public URL.
     - Updates the processing_requests record in the database with a status of "complete" and stores the S3 URL of the output CSV.
     - If a webhook URL was provided, triggers the webhook using the trigger_webhook(webhook_url, payload) function.
   - Example:
     The worker processes a list of CSV rows (each containing product and image URL data) asynchronously. Even if one image fails, the process continues for the remaining images. After processing, an output CSV is generated and a webhook is triggered with a payload similar to:
     {
     "request_id": "unique-request-id",
     "status": "complete",
     "output_csv": "https://<AWS_BUCKET>.s3.amazonaws.com/csvfile/unique-request-id_output.csv",
     "message": "Image processing completed successfully."
     }

2. trigger_webhook(webhook_url, payload):
   - Role: Sends a POST request to the provided webhook URL with the processing result payload.
   - Functions:
     - Utilizes an asynchronous HTTP client (httpx.AsyncClient) to send the payload.
     - Logs any errors encountered during the HTTP request.
   - Example:
     Upon completion of image processing, if the webhook_url is set, this function notifies the external system (e.g., a Pipedream workflow) by sending a POST request with a JSON payload that includes the relevant processing details.

---

Usage Example:

1. A client uploads a CSV file via the POST /upload endpoint along with an optional webhook_url.
2. The system immediately responds with a unique request_id, for example: { "request_id": "abc-123" }.
3. The asynchronous worker function processes the CSV, compresses images, uploads them to S3, and generates an output CSV.
4. The client can monitor the status using the GET /status/abc-123 endpoint. Upon completion, a response may look like:
   {
   "request_id": "abc-123",
   "status": "complete",
   "output_csv": "https://compressimageurls.s3.amazonaws.com/csvfile/abc-123_output.csv",
   "error": null
   }
5. If a webhook URL was provided during upload, the system sends a POST request to that URL with a JSON payload containing the same information, thereby enabling integration with other services.

---
