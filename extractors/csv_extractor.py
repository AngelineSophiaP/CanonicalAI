import csv
from typing import Generator
from models.source_models import ParsedCSVRecord

def extract_csv_stream(file_path: str) -> Generator[ParsedCSVRecord, None, None]:
    """Yields one validated row at a time to handle massive files."""
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                # Strip whitespace from keys and values
                clean_row = {k.strip(): v.strip() for k, v in row.items() if k and v}
                yield ParsedCSVRecord(**clean_row)
            except Exception as e:
                print(f"Skipping malformed row: {e}")