import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import get_settings
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

settings = get_settings()
PDF_PATH = sys.argv[1]

def get_di_client():
    return DocumentAnalysisClient(
        endpoint=settings.azure_di_endpoint,
        credential=AzureKeyCredential(settings.azure_di_key),
    )

def get_team_name_from_page(result, page_number):
    for page in result.pages:
        if page.page_number == page_number:
            lines = [l.content.strip() for l in page.lines if l.content.strip()]
            # Team name is usually in first 5 lines — find the all-caps one
            for line in lines[:8]:
                upper = line.upper()
                # Skip conference names, head coach label, capacity info
                skip = any(w in upper for w in [
                    "CONFERENCE", "DIVISION", "HEAD COACH", "CAPACITY",
                    "STADIUM", "FIELD", "TURF", "GRASS", "WWW.", "SCHEDULE",
                    "STATISTICAL", "YEAR", "4 YEAR", "COACH",
                ])
                if not skip and line.isupper() and len(line) > 2:
                    return line
            return lines[0] if lines else "?"
    return "?"

# Process in batches of 10 pages
START_PAGE = 102
END_PAGE = 236
BATCH_SIZE = 10

client = get_di_client()
results_map = {}

print(f"Scanning CFB pages {START_PAGE}-{END_PAGE} in batches of {BATCH_SIZE}...")

for batch_start in range(START_PAGE, END_PAGE + 1, BATCH_SIZE):
    batch_end = min(batch_start + BATCH_SIZE - 1, END_PAGE)
    pages_str = f"{batch_start}-{batch_end}"
    print(f"  Batch: pages {pages_str}...")
    
    with open(PDF_PATH, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-layout", f, pages=pages_str)
    result = poller.result()
    
    for page_num in range(batch_start, batch_end + 1):
        name = get_team_name_from_page(result, page_num)
        results_map[page_num] = name

print()
print("CFB_TEAM_PAGES = {")
for page_num in sorted(results_map.keys()):
    name = results_map[page_num]
    print(f'    # p{page_num}: {name}')
print("}")
print(f"\nTotal: {len(results_map)} pages")