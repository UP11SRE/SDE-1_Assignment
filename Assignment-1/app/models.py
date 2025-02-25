# app/models.py
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class CSVRow(BaseModel):

    serial_number: str
    product_name: str
    input_image_urls: List[HttpUrl]  

class ProcessingStatus(BaseModel):

    request_id: str
    status: str
    processed_images: Optional[List[HttpUrl]] = []
    error: Optional[str] = None