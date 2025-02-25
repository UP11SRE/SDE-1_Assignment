# app/image_utils.py
import requests
from PIL import Image
from io import BytesIO
import os

def compress_image(image_url: str, quality: int = 50) -> BytesIO:

    response = requests.get(image_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download image: {image_url}")

    image = Image.open(BytesIO(response.content))
    compressed_io = BytesIO()
    image.save(compressed_io, format=image.format, quality=quality)
    compressed_io.seek(0)
    return compressed_io

def upload_compressed_image(file_obj: BytesIO, destination_path: str) -> str:
   
    # Ensure the destination directory exists
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    with open(destination_path, "wb") as f:
        f.write(file_obj.read())
    return destination_path