# app/csv_handler.py
import csv
from io import StringIO
from app.models import CSVRow
from typing import List

def parse_csv(file_content: bytes) -> List[CSVRow]:

    text_content = file_content.decode("utf-8")
    f = StringIO(text_content)
    reader = csv.reader(f)
    results = []
    # Assuming the first row is a header; adjust if not
    headers = next(reader)
    for row in reader:
        if len(row) < 3:
            continue  # Skip rows that do not have enough columns
        serial_number = row[0].strip()
        product_name = row[1].strip()
        # Split image URLs by comma and remove any extra spaces
        image_urls = [url.strip() for url in row[2].split(",") if url.strip()]
        try:
            csv_row = CSVRow(
                serial_number=serial_number,
                product_name=product_name,
                input_image_urls=image_urls
            )
            results.append(csv_row)
        except Exception as e:
            # Optionally, log error for this row
            continue
    return results