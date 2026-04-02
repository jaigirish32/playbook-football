"""
inspect_pdf.py
==============
Finds the exact pages for each data section in the PDF.
Run: python inspect_pdf.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

settings  = get_settings()
PDF_PATH  = r"C:\mywork\NFL\2025PBFootballPreviewGuide.pdf"


def get_client():
    return DocumentAnalysisClient(
        endpoint   = settings.azure_di_endpoint,
        credential = AzureKeyCredential(settings.azure_di_key),
    )


def find_section_pages(start: int, end: int):
    """
    Print first 3 lines of each page so we can
    identify what section is on each page.
    """
    print(f"\nScanning pages {start} to {end}...")
    print("=" * 60)

    client = get_client()

    with open(PDF_PATH, "rb") as f:
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            f,
            pages=f"{start}-{end}",
        )
    result = poller.result()

    for page in result.pages:
        lines = [l.content for l in page.lines[:4]]
        print(f"\nPage {page.page_number}:")
        for line in lines:
            print(f"  {line}")


def inspect_page_tables(page_num: int):
    """
    Print full table content for a specific page.
    """
    print(f"\nFull table inspection — page {page_num}")
    print("=" * 60)

    client = get_client()

    with open(PDF_PATH, "rb") as f:
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            f,
            pages=str(page_num),
        )
    result = poller.result()

    print(f"Tables found: {len(result.tables)}")

    # Print raw text
    for page in result.pages:
        print(f"\nRAW TEXT — page {page.page_number}:")
        for line in page.lines:
            print(f"  {line.content}")

    # Print tables
    for t_idx, table in enumerate(result.tables):
        print(f"\nTABLE {t_idx + 1}: {table.row_count} rows x {table.column_count} cols")
        grid = {}
        for cell in table.cells:
            grid[(cell.row_index, cell.column_index)] = cell.content
        for row in range(table.row_count):
            row_data = [grid.get((row, col), "") for col in range(table.column_count)]
            print(f"  Row {row:2d}: {row_data}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) == 3 and args[0] == "scan":
        find_section_pages(int(args[1]), int(args[2]))

    elif len(args) == 2 and args[0] == "page":
        inspect_page_tables(int(args[1]))

    else:
        print("Usage:")
        print("  Scan page range  : python inspect_pdf.py scan 10 20")
        print("  Inspect one page : python inspect_pdf.py page 10")