from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from app.core.config import get_settings

settings = get_settings()

client = DocumentAnalysisClient(
    endpoint   = settings.azure_di_endpoint,
    credential = AzureKeyCredential(settings.azure_di_key),
)


def analyze_pdf(pdf_path: str) -> object:
    """
    Send a local PDF file to Azure Document Intelligence.
    Returns the full analysis result.
    Uses prebuilt-layout model — handles tables, columns, reading order.
    """
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document(
            "prebuilt-layout", f
        )
    return poller.result()


def extract_tables(result: object) -> list[list[dict]]:
    """
    Extract all tables from the DI result.
    Returns a list of tables — each table is a list of rows.
    Each row is a dict of column_index -> cell content.
    """
    tables = []
    for table in result.tables:
        rows = {}
        for cell in table.cells:
            row = rows.setdefault(cell.row_index, {})
            row[cell.column_index] = {
                "content"   : cell.content,
                "confidence": getattr(cell, "confidence", 1.0),
            }
        tables.append([rows[i] for i in sorted(rows.keys())])
    return tables


def extract_page_text(result: object, page_number: int) -> str:
    """
    Extract raw text from a specific page number (1-indexed).
    Used for article pages and trend text.
    """
    for page in result.pages:
        if page.page_number == page_number:
            lines = [line.content for line in page.lines]
            return "\n".join(lines)
    return ""


def get_low_confidence_pages(
    result          : object,
    threshold       : float = 0.80,
) -> list[int]:
    """
    Returns page numbers where any cell confidence is below threshold.
    These pages get flagged for manual review.
    """
    flagged = set()
    for table in result.tables:
        for cell in table.cells:
            confidence = getattr(cell, "confidence", 1.0)
            if confidence < threshold:
                flagged.add(table.bounding_regions[0].page_number)
    return sorted(flagged)