"""
ingest.py — NFL Tier 1 PDF ingestion script
============================================
Run once per season to populate the database from the PDF.

Usage:
  python ingest.py --teams-only          # seed teams + coaches only
  python ingest.py --pdf PATH_TO_PDF     # full ingestion from PDF
  python ingest.py --pdf PATH --page 28  # test single team page
"""

import re
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal, enable_pgvector, Base, engine
from app.core.config import get_settings
from app.models import (
    User, Team, Coach, CoachStat,
    SeasonStat, SOSStat, TeamTrend, AICache,
)

settings = get_settings()
PDF_PATH = None   # set from --pdf argument


# ── Helpers ───────────────────────────────────────────────────

def parse_record(s: str) -> tuple[int, int]:
    """
    Parse 'W-L' string into (wins, losses).
    Handles: '11-6', '69-71', '0-0', '–'
    """
    s = s.strip().replace("–", "0")
    parts = s.split("-")
    try:
        w = int(parts[0]) if len(parts) > 0 else 0
        l = int(parts[1]) if len(parts) > 1 else 0
        return w, l
    except (ValueError, IndexError):
        return 0, 0


def parse_record_3(s: str) -> tuple[int, int, int]:
    """
    Parse 'W-L-P' or 'W-L' into (wins, losses, pushes).
    Handles: '10-8', '4-3', '11-7-1'
    """
    s = s.strip().replace("–", "0")
    parts = s.split("-")
    try:
        w = int(parts[0]) if len(parts) > 0 else 0
        l = int(parts[1]) if len(parts) > 1 else 0
        p = int(parts[2]) if len(parts) > 2 else 0
        return w, l, p
    except (ValueError, IndexError):
        return 0, 0, 0


def safe_float(s: str) -> float | None:
    """Convert string to float safely."""
    try:
        return float(str(s).strip().replace("–", ""))
    except (ValueError, TypeError):
        return None


def safe_int(s: str) -> int | None:
    """Convert string to int safely."""
    try:
        return int(str(s).strip().replace("–", ""))
    except (ValueError, TypeError):
        return None


def get_di_client():
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential
    return DocumentAnalysisClient(
        endpoint   = settings.azure_di_endpoint,
        credential = AzureKeyCredential(settings.azure_di_key),
    )


def analyze_pages(pdf_path: str, pages: str) -> object:
    """Send specific pages to Azure DI and return result."""
    client = get_di_client()
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document(
            "prebuilt-layout", f, pages=pages
        )
    return poller.result()


def get_table_grid(table) -> dict:
    """Convert Azure DI table to {(row, col): content} dict."""
    grid = {}
    for cell in table.cells:
        grid[(cell.row_index, cell.column_index)] = cell.content.strip()
    return grid


def get_page_lines(result, page_number: int) -> list[str]:
    """Get all text lines from a specific page number."""
    for page in result.pages:
        if page.page_number == page_number:
            return [line.content.strip() for line in page.lines]
    return []


# ── NFL Teams master list ─────────────────────────────────────

NFL_TEAMS = [
    {"name": "Arizona Cardinals",    "abbreviation": "ARI", "conference": "NFC", "division": "NFC West",  "stadium": "State Farm Stadium",            "stadium_surface": "Grass", "stadium_city": "Glendale, AZ",       "stadium_capacity": 63400},
    {"name": "Atlanta Falcons",      "abbreviation": "ATL", "conference": "NFC", "division": "NFC South", "stadium": "Mercedes-Benz Stadium",          "stadium_surface": "Turf",  "stadium_city": "Atlanta, GA",         "stadium_capacity": 71000},
    {"name": "Baltimore Ravens",     "abbreviation": "BAL", "conference": "AFC", "division": "AFC North", "stadium": "M&T Bank Stadium",               "stadium_surface": "Turf",  "stadium_city": "Baltimore, MD",       "stadium_capacity": 71008},
    {"name": "Buffalo Bills",        "abbreviation": "BUF", "conference": "AFC", "division": "AFC East",  "stadium": "Highmark Stadium",               "stadium_surface": "Turf",  "stadium_city": "Orchard Park, NY",    "stadium_capacity": 71608},
    {"name": "Carolina Panthers",    "abbreviation": "CAR", "conference": "NFC", "division": "NFC South", "stadium": "Bank of America Stadium",        "stadium_surface": "Grass", "stadium_city": "Charlotte, NC",       "stadium_capacity": 74455},
    {"name": "Chicago Bears",        "abbreviation": "CHI", "conference": "NFC", "division": "NFC North", "stadium": "Soldier Field",                  "stadium_surface": "Grass", "stadium_city": "Chicago, IL",         "stadium_capacity": 61500},
    {"name": "Cincinnati Bengals",   "abbreviation": "CIN", "conference": "AFC", "division": "AFC North", "stadium": "Paycor Stadium",                 "stadium_surface": "Turf",  "stadium_city": "Cincinnati, OH",      "stadium_capacity": 65515},
    {"name": "Cleveland Browns",     "abbreviation": "CLE", "conference": "AFC", "division": "AFC North", "stadium": "Huntington Bank Field",          "stadium_surface": "Grass", "stadium_city": "Cleveland, OH",       "stadium_capacity": 67431},
    {"name": "Dallas Cowboys",       "abbreviation": "DAL", "conference": "NFC", "division": "NFC East",  "stadium": "AT&T Stadium",                   "stadium_surface": "Turf",  "stadium_city": "Arlington, TX",       "stadium_capacity": 80000},
    {"name": "Denver Broncos",       "abbreviation": "DEN", "conference": "AFC", "division": "AFC West",  "stadium": "Empower Field at Mile High",     "stadium_surface": "Grass", "stadium_city": "Denver, CO",          "stadium_capacity": 76125},
    {"name": "Detroit Lions",        "abbreviation": "DET", "conference": "NFC", "division": "NFC North", "stadium": "Ford Field",                     "stadium_surface": "Turf",  "stadium_city": "Detroit, MI",         "stadium_capacity": 65000},
    {"name": "Green Bay Packers",    "abbreviation": "GB",  "conference": "NFC", "division": "NFC North", "stadium": "Lambeau Field",                  "stadium_surface": "Grass", "stadium_city": "Green Bay, WI",       "stadium_capacity": 81441},
    {"name": "Houston Texans",       "abbreviation": "HOU", "conference": "AFC", "division": "AFC South", "stadium": "NRG Stadium",                    "stadium_surface": "Turf",  "stadium_city": "Houston, TX",         "stadium_capacity": 72220},
    {"name": "Indianapolis Colts",   "abbreviation": "IND", "conference": "AFC", "division": "AFC South", "stadium": "Lucas Oil Stadium",              "stadium_surface": "Turf",  "stadium_city": "Indianapolis, IN",    "stadium_capacity": 67000},
    {"name": "Jacksonville Jaguars", "abbreviation": "JAX", "conference": "AFC", "division": "AFC South", "stadium": "EverBank Stadium",               "stadium_surface": "Grass", "stadium_city": "Jacksonville, FL",    "stadium_capacity": 62000},
    {"name": "Kansas City Chiefs",   "abbreviation": "KC",  "conference": "AFC", "division": "AFC West",  "stadium": "GEHA Field at Arrowhead Stadium","stadium_surface": "Grass", "stadium_city": "Kansas City, MO",     "stadium_capacity": 76416},
    {"name": "Las Vegas Raiders",    "abbreviation": "LV",  "conference": "AFC", "division": "AFC West",  "stadium": "Allegiant Stadium",              "stadium_surface": "Turf",  "stadium_city": "Las Vegas, NV",       "stadium_capacity": 65000},
    {"name": "Los Angeles Chargers", "abbreviation": "LAC", "conference": "AFC", "division": "AFC West",  "stadium": "SoFi Stadium",                   "stadium_surface": "Turf",  "stadium_city": "Inglewood, CA",       "stadium_capacity": 70240},
    {"name": "Los Angeles Rams",     "abbreviation": "LAR", "conference": "NFC", "division": "NFC West",  "stadium": "SoFi Stadium",                   "stadium_surface": "Turf",  "stadium_city": "Inglewood, CA",       "stadium_capacity": 70240},
    {"name": "Miami Dolphins",       "abbreviation": "MIA", "conference": "AFC", "division": "AFC East",  "stadium": "Hard Rock Stadium",              "stadium_surface": "Grass", "stadium_city": "Miami Gardens, FL",   "stadium_capacity": 65326},
    {"name": "Minnesota Vikings",    "abbreviation": "MIN", "conference": "NFC", "division": "NFC North", "stadium": "U.S. Bank Stadium",              "stadium_surface": "Turf",  "stadium_city": "Minneapolis, MN",     "stadium_capacity": 66860},
    {"name": "New England Patriots", "abbreviation": "NE",  "conference": "AFC", "division": "AFC East",  "stadium": "Gillette Stadium",               "stadium_surface": "Turf",  "stadium_city": "Foxborough, MA",      "stadium_capacity": 65878},
    {"name": "New Orleans Saints",   "abbreviation": "NO",  "conference": "NFC", "division": "NFC South", "stadium": "Caesars Superdome",              "stadium_surface": "Turf",  "stadium_city": "New Orleans, LA",     "stadium_capacity": 73208},
    {"name": "New York Giants",      "abbreviation": "NYG", "conference": "NFC", "division": "NFC East",  "stadium": "MetLife Stadium",                "stadium_surface": "Turf",  "stadium_city": "East Rutherford, NJ", "stadium_capacity": 82500},
    {"name": "New York Jets",        "abbreviation": "NYJ", "conference": "AFC", "division": "AFC East",  "stadium": "MetLife Stadium",                "stadium_surface": "Turf",  "stadium_city": "East Rutherford, NJ", "stadium_capacity": 82500},
    {"name": "Philadelphia Eagles",  "abbreviation": "PHI", "conference": "NFC", "division": "NFC East",  "stadium": "Lincoln Financial Field",        "stadium_surface": "Grass", "stadium_city": "Philadelphia, PA",    "stadium_capacity": 69796},
    {"name": "Pittsburgh Steelers",  "abbreviation": "PIT", "conference": "AFC", "division": "AFC North", "stadium": "Acrisure Stadium",               "stadium_surface": "Grass", "stadium_city": "Pittsburgh, PA",      "stadium_capacity": 68400},
    {"name": "San Francisco 49ers",  "abbreviation": "SF",  "conference": "NFC", "division": "NFC West",  "stadium": "Levi's Stadium",                 "stadium_surface": "Grass", "stadium_city": "Santa Clara, CA",     "stadium_capacity": 68500},
    {"name": "Seattle Seahawks",     "abbreviation": "SEA", "conference": "NFC", "division": "NFC West",  "stadium": "Lumen Field",                    "stadium_surface": "Turf",  "stadium_city": "Seattle, WA",         "stadium_capacity": 69000},
    {"name": "Tampa Bay Buccaneers", "abbreviation": "TB",  "conference": "NFC", "division": "NFC South", "stadium": "Raymond James Stadium",          "stadium_surface": "Grass", "stadium_city": "Tampa, FL",           "stadium_capacity": 69218},
    {"name": "Tennessee Titans",     "abbreviation": "TEN", "conference": "AFC", "division": "AFC South", "stadium": "Nissan Stadium",                 "stadium_surface": "Turf",  "stadium_city": "Nashville, TN",       "stadium_capacity": 69143},
    {"name": "Washington Commanders","abbreviation": "WAS", "conference": "NFC", "division": "NFC East",  "stadium": "Northwest Stadium",              "stadium_surface": "Turf",  "stadium_city": "Landover, MD",        "stadium_capacity": 67617},
]

CFB_TEAM_PAGES = {
    "Air Force"           : 102,
    "Akron"               : 103,
    "Alabama"             : 104,
    "Appalachian State"   : 105,
    "Arizona"             : 106,
    "Arizona State"       : 107,
    "Arkansas"            : 108,
    "Arkansas State"      : 109,
    "Army"                : 110,
    "Auburn"              : 111,
    "Ball State"          : 112,
    "Baylor"              : 113,
    "Boise State"         : 114,
    "Boston College"      : 115,
    "Bowling Green"       : 116,
    "Buffalo"             : 117,
    "BYU"                 : 118,
    "California"          : 119,
    "Central Michigan"    : 120,
    "Charlotte"           : 121,
    "Cincinnati"          : 122,
    "Clemson"             : 123,
    "Coastal Carolina"    : 124,
    "Colorado"            : 125,
    "Colorado State"      : 126,
    "Duke"                : 127,
    "East Carolina"       : 128,
    "Eastern Michigan"    : 129,
    "Florida"             : 130,
    "Florida Atlantic"    : 131,
    "Florida International": 132,
    "Florida State"       : 133,
    "Fresno State"        : 134,
    "Georgia"             : 135,
    "Georgia Southern"    : 136,
    "Georgia State"       : 137,
    "Georgia Tech"        : 138,
    "Hawai'i"             : 139,
    "Houston"             : 140,
    "Illinois"            : 141,
    "Indiana"             : 142,
    "Iowa"                : 143,
    "Iowa State"          : 144,
    "Jacksonville State"  : 145,
    "James Madison"       : 146,
    "Kansas"              : 147,
    "Kansas State"        : 148,
    "Kennesaw State"      : 149,
    "Kent State"          : 150,
    "Kentucky"            : 151,
    "Liberty"             : 152,
    "Louisiana"           : 153,
    "Louisiana Tech"      : 154,
    "Louisville"          : 155,
    "LSU"                 : 156,
    "Marshall"            : 157,
    "Maryland"            : 158,
    "Memphis"             : 159,
    "Miami Florida"       : 160,
    "Miami Ohio"          : 161,
    "Michigan"            : 162,
    "Michigan State"      : 163,
    "Middle Tennessee State": 164,
    "Minnesota"           : 165,
    "Mississippi State"   : 166,
    "Missouri"            : 167,
    "Navy"                : 168,
    "NC State"            : 169,
    "Nebraska"            : 170,
    "Nevada"              : 171,
    "New Mexico"          : 172,
    "New Mexico State"    : 173,
    "North Carolina"      : 174,
    "North Texas"         : 175,
    "Northern Illinois"   : 176,
    "Northwestern"        : 177,
    "Notre Dame"          : 178,
    "Ohio State"          : 179,
    "Ohio University"     : 180,
    "Oklahoma"            : 181,
    "Oklahoma State"      : 182,
    "Old Dominion"        : 183,
    "Ole Miss"            : 184,
    "Oregon"              : 185,
    "Oregon State"        : 186,
    "Penn State"          : 187,
    "Pitt"                : 188,
    "Purdue"              : 189,
    "Rice"                : 190,
    "Rutgers"             : 191,
    "Sam Houston"         : 192,
    "San Diego State"     : 193,
    "San Jose State"      : 194,
    "SMU"                 : 195,
    "South Alabama"       : 196,
    "South Carolina"      : 197,
    "Southern Miss"       : 198,
    "Stanford"            : 199,
    "Syracuse"            : 200,
    "TCU"                 : 201,
    "Temple"              : 202,
    "Tennessee"           : 203,
    "Texas"               : 204,
    "Texas A&M"           : 205,
    "Texas State"         : 206,
    "Texas Tech"          : 207,
    "Toledo"              : 208,
    "Troy"                : 209,
    "Tulane"              : 210,
    "Tulsa"               : 211,
    "UAB"                 : 212,
    "UCF"                 : 213,
    "UCLA"                : 214,
    "UConn"               : 215,
    "UL Monroe"           : 216,
    "UMass"               : 217,
    "UNLV"                : 218,
    "USC"                 : 219,
    "USF"                 : 220,
    "Utah"                : 221,
    "Utah State"          : 222,
    "UTEP"                : 223,
    "UTSA"                : 224,
    "Vanderbilt"          : 225,
    "Virginia"            : 226,
    "Virginia Tech"       : 227,
    "Wake Forest"         : 228,
    "Washington"          : 229,
    "Washington State"    : 230,
    "West Virginia"       : 231,
    "Western Kentucky"    : 232,
    "Western Michigan"    : 233,
    "Wisconsin"           : 234,
    "Wyoming"             : 235,
    "Delaware"            : 236,
}

# Map PDF team names to abbreviations
# Used to match coaches data and SOS data to our teams table
PDF_NAME_TO_ABBR = {
    "arizona"        : "ARI",
    "atlanta"        : "ATL",
    "baltimore"      : "BAL",
    "buffalo"        : "BUF",
    "carolina"       : "CAR",
    "chicago"        : "CHI",
    "cincinnati"     : "CIN",
    "cleveland"      : "CLE",
    "dallas"         : "DAL",
    "denver"         : "DEN",
    "detroit"        : "DET",
    "green bay"      : "GB",
    "houston"        : "HOU",
    "indianapolis"   : "IND",
    "jacksonville"   : "JAX",
    "kansas city"    : "KC",
    "las vegas"      : "LV",
    "la chargers"    : "LAC",
    "la rams"        : "LAR",
    "miami"          : "MIA",
    "minnesota"      : "MIN",
    "new england"    : "NE",
    "new orleans"    : "NO",
    "ny giants"      : "NYG",
    "ny jets"        : "NYJ",
    "philadelphia"   : "PHI",
    "pittsburgh"     : "PIT",
    "san francisco"  : "SF",
    "seattle"        : "SEA",
    "tampa bay"      : "TB",
    "tennessee"      : "TEN",
    "washington"     : "WAS",
    # SOS page uses full caps
    "deroit"         : "DET",   # typo in PDF
}

# NFL team page mapping — PDF page number for each team
# Pattern: Arizona=28, Atlanta=30, Baltimore=32 ... every 2 pages
NFL_TEAM_PAGES = {
    "ARI": 28, "ATL": 30, "BAL": 32, "BUF": 34,
    "CAR": 36, "CHI": 38, "CIN": 40, "CLE": 42,
    "DAL": 44, "DEN": 46, "DET": 48, "GB":  50,
    "HOU": 52, "IND": 54, "JAX": 56, "KC":  58,
    "LV":  60, "LAC": 62, "LAR": 64, "MIA": 66,
    "MIN": 68, "NE":  70, "NO":  72, "NYG": 74,
    "NYJ": 76, "PHI": 78, "PIT": 80, "SF":  82,
    "SEA": 84, "TB":  86, "TEN": 88, "WAS": 90,
}

# ── CFB Team Pages ────────────────────────────────────────────
# One page per team, alphabetical, pages 102-236
CFB_TEAM_PAGES = {
    "Air Force"             : 102,
    "Akron"                 : 103,
    "Alabama"               : 104,
    "Appalachian State"     : 105,
    "Arizona"               : 106,
    "Arizona State"         : 107,
    "Arkansas"              : 108,
    "Arkansas State"        : 109,
    "Army"                  : 110,
    "Auburn"                : 111,
    "Ball State"            : 112,
    "Baylor"                : 113,
    "Boise State"           : 114,
    "Boston College"        : 115,
    "Bowling Green"         : 116,
    "Buffalo"               : 117,
    "BYU"                   : 118,
    "California"            : 119,
    "Central Michigan"      : 120,
    "Charlotte"             : 121,
    "Cincinnati"            : 122,
    "Clemson"               : 123,
    "Coastal Carolina"      : 124,
    "Colorado"              : 125,
    "Colorado State"        : 126,
    "Duke"                  : 127,
    "East Carolina"         : 128,
    "Eastern Michigan"      : 129,
    "Florida"               : 130,
    "Florida Atlantic"      : 131,
    "Florida International" : 132,
    "Florida State"         : 133,
    "Fresno State"          : 134,
    "Georgia"               : 135,
    "Georgia Southern"      : 136,
    "Georgia State"         : 137,
    "Georgia Tech"          : 138,
    "Hawai'i"               : 139,
    "Houston"               : 140,
    "Illinois"              : 141,
    "Indiana"               : 142,
    "Iowa"                  : 143,
    "Iowa State"            : 144,
    "Jacksonville State"    : 145,
    "James Madison"         : 146,
    "Kansas"                : 147,
    "Kansas State"          : 148,
    "Kennesaw State"        : 149,
    "Kent State"            : 150,
    "Kentucky"              : 151,
    "Liberty"               : 152,
    "Louisiana"             : 153,
    "Louisiana Tech"        : 154,
    "Louisville"            : 155,
    "LSU"                   : 156,
    "Marshall"              : 157,
    "Maryland"              : 158,
    "Memphis"               : 159,
    "Miami Florida"         : 160,
    "Miami Ohio"            : 161,
    "Michigan"              : 162,
    "Michigan State"        : 163,
    "Middle Tennessee State": 164,
    "Minnesota"             : 165,
    "Mississippi State"     : 166,
    "Missouri"              : 167,
    "Navy"                  : 168,
    "NC State"              : 169,
    "Nebraska"              : 170,
    "Nevada"                : 171,
    "New Mexico"            : 172,
    "New Mexico State"      : 173,
    "North Carolina"        : 174,
    "North Texas"           : 175,
    "Northern Illinois"     : 176,
    "Northwestern"          : 177,
    "Notre Dame"            : 178,
    "Ohio State"            : 179,
    "Ohio University"       : 180,
    "Oklahoma"              : 181,
    "Oklahoma State"        : 182,
    "Old Dominion"          : 183,
    "Ole Miss"              : 184,
    "Oregon"                : 185,
    "Oregon State"          : 186,
    "Penn State"            : 187,
    "Pitt"                  : 188,
    "Purdue"                : 189,
    "Rice"                  : 190,
    "Rutgers"               : 191,
    "Sam Houston"           : 192,
    "San Diego State"       : 193,
    "San Jose State"        : 194,
    "SMU"                   : 195,
    "South Alabama"         : 196,
    "South Carolina"        : 197,
    "Southern Miss"         : 198,
    "Stanford"              : 199,
    "Syracuse"              : 200,
    "TCU"                   : 201,
    "Temple"                : 202,
    "Tennessee"             : 203,
    "Texas"                 : 204,
    "Texas A&M"             : 205,
    "Texas State"           : 206,
    "Texas Tech"            : 207,
    "Toledo"                : 208,
    "Troy"                  : 209,
    "Tulane"                : 210,
    "Tulsa"                 : 211,
    "UAB"                   : 212,
    "UCF"                   : 213,
    "UCLA"                  : 214,
    "UConn"                 : 215,
    "UL Monroe"             : 216,
    "UMass"                 : 217,
    "UNLV"                  : 218,
    "USC"                   : 219,
    "USF"                   : 220,
    "Utah"                  : 221,
    "Utah State"            : 222,
    "UTEP"                  : 223,
    "UTSA"                  : 224,
    "Vanderbilt"            : 225,
    "Virginia"              : 226,
    "Virginia Tech"         : 227,
    "Wake Forest"           : 228,
    "Washington"            : 229,
    "Washington State"      : 230,
    "West Virginia"         : 231,
    "Western Kentucky"      : 232,
    "Western Michigan"      : 233,
    "Wisconsin"             : 234,
    "Wyoming"               : 235,
    "Delaware"              : 236,
}

# CFB team metadata — conference, division extracted from PDF
CFB_TEAMS_META = {
    "Air Force"             : {"conference": "Mountain West",        "division": "Mountain West"},
    "Akron"                 : {"conference": "Mid-American",         "division": "MAC East"},
    "Alabama"               : {"conference": "SEC",                  "division": "SEC West"},
    "Appalachian State"     : {"conference": "Sun Belt",             "division": "Sun Belt East"},
    "Arizona"               : {"conference": "Big 12",               "division": "Big 12"},
    "Arizona State"         : {"conference": "Big 12",               "division": "Big 12"},
    "Arkansas"              : {"conference": "SEC",                  "division": "SEC West"},
    "Arkansas State"        : {"conference": "Sun Belt",             "division": "Sun Belt West"},
    "Army"                  : {"conference": "AAC",                  "division": "AAC"},
    "Auburn"                : {"conference": "SEC",                  "division": "SEC West"},
    "Ball State"            : {"conference": "Mid-American",         "division": "MAC West"},
    "Baylor"                : {"conference": "Big 12",               "division": "Big 12"},
    "Boise State"           : {"conference": "Mountain West",        "division": "Mountain West"},
    "Boston College"        : {"conference": "ACC",                  "division": "ACC Atlantic"},
    "Bowling Green"         : {"conference": "Mid-American",         "division": "MAC East"},
    "Buffalo"               : {"conference": "Mid-American",         "division": "MAC East"},
    "BYU"                   : {"conference": "Big 12",               "division": "Big 12"},
    "California"            : {"conference": "ACC",                  "division": "ACC"},
    "Central Michigan"      : {"conference": "Mid-American",         "division": "MAC West"},
    "Charlotte"             : {"conference": "AAC",                  "division": "AAC"},
    "Cincinnati"            : {"conference": "Big 12",               "division": "Big 12"},
    "Clemson"               : {"conference": "ACC",                  "division": "ACC Atlantic"},
    "Coastal Carolina"      : {"conference": "Sun Belt",             "division": "Sun Belt East"},
    "Colorado"              : {"conference": "Big 12",               "division": "Big 12"},
    "Colorado State"        : {"conference": "Mountain West",        "division": "Mountain West"},
    "Duke"                  : {"conference": "ACC",                  "division": "ACC Coastal"},
    "East Carolina"         : {"conference": "AAC",                  "division": "AAC"},
    "Eastern Michigan"      : {"conference": "Mid-American",         "division": "MAC West"},
    "Florida"               : {"conference": "SEC",                  "division": "SEC East"},
    "Florida Atlantic"      : {"conference": "AAC",                  "division": "AAC"},
    "Florida International" : {"conference": "CUSA",                 "division": "CUSA"},
    "Florida State"         : {"conference": "ACC",                  "division": "ACC Atlantic"},
    "Fresno State"          : {"conference": "Mountain West",        "division": "Mountain West"},
    "Georgia"               : {"conference": "SEC",                  "division": "SEC East"},
    "Georgia Southern"      : {"conference": "Sun Belt",             "division": "Sun Belt East"},
    "Georgia State"         : {"conference": "Sun Belt",             "division": "Sun Belt East"},
    "Georgia Tech"          : {"conference": "ACC",                  "division": "ACC Coastal"},
    "Hawai'i"               : {"conference": "Mountain West",        "division": "Mountain West"},
    "Houston"               : {"conference": "Big 12",               "division": "Big 12"},
    "Illinois"              : {"conference": "Big Ten",              "division": "Big Ten"},
    "Indiana"               : {"conference": "Big Ten",              "division": "Big Ten"},
    "Iowa"                  : {"conference": "Big Ten",              "division": "Big Ten"},
    "Iowa State"            : {"conference": "Big 12",               "division": "Big 12"},
    "Jacksonville State"    : {"conference": "CUSA",                 "division": "CUSA"},
    "James Madison"         : {"conference": "Sun Belt",             "division": "Sun Belt East"},
    "Kansas"                : {"conference": "Big 12",               "division": "Big 12"},
    "Kansas State"          : {"conference": "Big 12",               "division": "Big 12"},
    "Kennesaw State"        : {"conference": "CUSA",                 "division": "CUSA"},
    "Kent State"            : {"conference": "Mid-American",         "division": "MAC East"},
    "Kentucky"              : {"conference": "SEC",                  "division": "SEC East"},
    "Liberty"               : {"conference": "CUSA",                 "division": "CUSA"},
    "Louisiana"             : {"conference": "Sun Belt",             "division": "Sun Belt West"},
    "Louisiana Tech"        : {"conference": "CUSA",                 "division": "CUSA"},
    "Louisville"            : {"conference": "ACC",                  "division": "ACC Atlantic"},
    "LSU"                   : {"conference": "SEC",                  "division": "SEC West"},
    "Marshall"              : {"conference": "Sun Belt",             "division": "Sun Belt East"},
    "Maryland"              : {"conference": "Big Ten",              "division": "Big Ten"},
    "Memphis"               : {"conference": "AAC",                  "division": "AAC"},
    "Miami Florida"         : {"conference": "ACC",                  "division": "ACC Coastal"},
    "Miami Ohio"            : {"conference": "Mid-American",         "division": "MAC East"},
    "Michigan"              : {"conference": "Big Ten",              "division": "Big Ten"},
    "Michigan State"        : {"conference": "Big Ten",              "division": "Big Ten"},
    "Middle Tennessee State": {"conference": "CUSA",                 "division": "CUSA"},
    "Minnesota"             : {"conference": "Big Ten",              "division": "Big Ten"},
    "Mississippi State"     : {"conference": "SEC",                  "division": "SEC West"},
    "Missouri"              : {"conference": "SEC",                  "division": "SEC East"},
    "Navy"                  : {"conference": "AAC",                  "division": "AAC"},
    "NC State"              : {"conference": "ACC",                  "division": "ACC Atlantic"},
    "Nebraska"              : {"conference": "Big Ten",              "division": "Big Ten"},
    "Nevada"                : {"conference": "Mountain West",        "division": "Mountain West"},
    "New Mexico"            : {"conference": "Mountain West",        "division": "Mountain West"},
    "New Mexico State"      : {"conference": "CUSA",                 "division": "CUSA"},
    "North Carolina"        : {"conference": "ACC",                  "division": "ACC Coastal"},
    "North Texas"           : {"conference": "AAC",                  "division": "AAC"},
    "Northern Illinois"     : {"conference": "Mid-American",         "division": "MAC West"},
    "Northwestern"          : {"conference": "Big Ten",              "division": "Big Ten"},
    "Notre Dame"            : {"conference": "Independent",          "division": "Independent"},
    "Ohio State"            : {"conference": "Big Ten",              "division": "Big Ten"},
    "Ohio University"       : {"conference": "Mid-American",         "division": "MAC East"},
    "Oklahoma"              : {"conference": "SEC",                  "division": "SEC West"},
    "Oklahoma State"        : {"conference": "Big 12",               "division": "Big 12"},
    "Old Dominion"          : {"conference": "Sun Belt",             "division": "Sun Belt East"},
    "Ole Miss"              : {"conference": "SEC",                  "division": "SEC West"},
    "Oregon"                : {"conference": "Big Ten",              "division": "Big Ten"},
    "Oregon State"          : {"conference": "Pac-12",               "division": "Pac-12"},
    "Penn State"            : {"conference": "Big Ten",              "division": "Big Ten"},
    "Pitt"                  : {"conference": "ACC",                  "division": "ACC Coastal"},
    "Purdue"                : {"conference": "Big Ten",              "division": "Big Ten"},
    "Rice"                  : {"conference": "AAC",                  "division": "AAC"},
    "Rutgers"               : {"conference": "Big Ten",              "division": "Big Ten"},
    "Sam Houston"           : {"conference": "CUSA",                 "division": "CUSA"},
    "San Diego State"       : {"conference": "Mountain West",        "division": "Mountain West"},
    "San Jose State"        : {"conference": "Mountain West",        "division": "Mountain West"},
    "SMU"                   : {"conference": "ACC",                  "division": "ACC"},
    "South Alabama"         : {"conference": "Sun Belt",             "division": "Sun Belt West"},
    "South Carolina"        : {"conference": "SEC",                  "division": "SEC East"},
    "Southern Miss"         : {"conference": "Sun Belt",             "division": "Sun Belt West"},
    "Stanford"              : {"conference": "ACC",                  "division": "ACC"},
    "Syracuse"              : {"conference": "ACC",                  "division": "ACC Atlantic"},
    "TCU"                   : {"conference": "Big 12",               "division": "Big 12"},
    "Temple"                : {"conference": "AAC",                  "division": "AAC"},
    "Tennessee"             : {"conference": "SEC",                  "division": "SEC East"},
    "Texas"                 : {"conference": "SEC",                  "division": "SEC West"},
    "Texas A&M"             : {"conference": "SEC",                  "division": "SEC West"},
    "Texas State"           : {"conference": "Sun Belt",             "division": "Sun Belt West"},
    "Texas Tech"            : {"conference": "Big 12",               "division": "Big 12"},
    "Toledo"                : {"conference": "Mid-American",         "division": "MAC West"},
    "Troy"                  : {"conference": "Sun Belt",             "division": "Sun Belt West"},
    "Tulane"                : {"conference": "AAC",                  "division": "AAC"},
    "Tulsa"                 : {"conference": "AAC",                  "division": "AAC"},
    "UAB"                   : {"conference": "AAC",                  "division": "AAC"},
    "UCF"                   : {"conference": "Big 12",               "division": "Big 12"},
    "UCLA"                  : {"conference": "Big Ten",              "division": "Big Ten"},
    "UConn"                 : {"conference": "Independent",          "division": "Independent"},
    "UL Monroe"             : {"conference": "Sun Belt",             "division": "Sun Belt West"},
    "UMass"                 : {"conference": "Mid-American",         "division": "MAC"},
    "UNLV"                  : {"conference": "Mountain West",        "division": "Mountain West"},
    "USC"                   : {"conference": "Big Ten",              "division": "Big Ten"},
    "USF"                   : {"conference": "AAC",                  "division": "AAC"},
    "Utah"                  : {"conference": "Big 12",               "division": "Big 12"},
    "Utah State"            : {"conference": "Mountain West",        "division": "Mountain West"},
    "UTEP"                  : {"conference": "CUSA",                 "division": "CUSA"},
    "UTSA"                  : {"conference": "AAC",                  "division": "AAC"},
    "Vanderbilt"            : {"conference": "SEC",                  "division": "SEC East"},
    "Virginia"              : {"conference": "ACC",                  "division": "ACC Coastal"},
    "Virginia Tech"         : {"conference": "ACC",                  "division": "ACC Coastal"},
    "Wake Forest"           : {"conference": "ACC",                  "division": "ACC Atlantic"},
    "Washington"            : {"conference": "Big Ten",              "division": "Big Ten"},
    "Washington State"      : {"conference": "Pac-12",               "division": "Pac-12"},
    "West Virginia"         : {"conference": "Big 12",               "division": "Big 12"},
    "Western Kentucky"      : {"conference": "CUSA",                 "division": "CUSA"},
    "Western Michigan"      : {"conference": "Mid-American",         "division": "MAC West"},
    "Wisconsin"             : {"conference": "Big Ten",              "division": "Big Ten"},
    "Wyoming"               : {"conference": "Mountain West",        "division": "Mountain West"},
    "Delaware"              : {"conference": "CUSA",                 "division": "CUSA"},
}

NFL_PLAYBOOK_PAGES = {
    'ARI': 29, 'ATL': 31, 'BAL': 33, 'BUF': 35, 'CAR': 37, 'CHI': 39,
    'CIN': 41, 'CLE': 43, 'DAL': 45, 'DEN': 47, 'DET': 49, 'GB':  51,
    'HOU': 53, 'IND': 55, 'JAX': 57, 'KC':  59, 'LV':  61, 'LAC': 63,
    'LAR': 65, 'MIA': 67, 'MIN': 69, 'NE':  71, 'NO':  73, 'NYG': 75,
    'NYJ': 77, 'PHI': 79, 'PIT': 81, 'SF':  83, 'SEA': 85, 'TB':  87,
    'TEN': 89, 'WAS': 91,
}

# ── Step 1: Seed teams ────────────────────────────────────────

def seed_teams(db) -> dict:
    from app.models.team import LeagueEnum
    from app.repositories.team_repo import upsert_team

    print("\n── Seeding NFL teams ─────────────────────────────")
    teams = {}
    for data in NFL_TEAMS:
        team = upsert_team(db, {**data, "league": LeagueEnum.NFL})
        teams[data["abbreviation"]] = team
        print(f"  ✓ {team.name}")
    print(f"  Total: {len(teams)} teams")
    return teams


# ── Step 2: Parse + seed coaches data from PDF page 10 ───────

def seed_coaches_from_pdf(db, teams: dict):
    """
    Parse the NFL Coaches Data chart from PDF page 10.
    TABLE 1: 26 rows x 16 cols
    Row 0 = header, Rows 1-25 = one coach per row.
    """
    from app.repositories.coach_repo import upsert_coach, upsert_coach_stats

    print("\n── Parsing coaches data (page 10) ───────────────")
    result = analyze_pages(PDF_PATH, "10")

    # Find TABLE 1 (26 rows x 16 cols)
    coaches_table = None
    for table in result.tables:
        if table.row_count >= 25 and table.column_count == 16:
            coaches_table = table
            break

    if not coaches_table:
        print("  ✗ Coaches table not found on page 10")
        return

    grid = get_table_grid(coaches_table)
    errors = []

    for row_idx in range(1, coaches_table.row_count):
        try:
            team_name  = grid.get((row_idx, 0), "").strip().lower()
            coach_name = grid.get((row_idx, 1), "").strip()
            years      = safe_int(grid.get((row_idx, 2), "0")) or 1

            if not team_name or not coach_name:
                continue

            abbr = PDF_NAME_TO_ABBR.get(team_name)
            if not abbr:
                print(f"  ✗ Unknown team: {team_name}")
                continue

            team = teams.get(abbr)
            if not team:
                continue

            # Parse all 13 ATS record columns (cols 3-15)
            def rec(col): return parse_record(grid.get((row_idx, col), "0-0"))

            home_w,  home_l  = rec(3)
            away_w,  away_l  = rec(4)
            fav_w,   fav_l   = rec(5)
            dog_w,   dog_l   = rec(6)
            rest_w,  rest_l  = rec(7)
            rev_w,   rev_l   = rec(8)
            vsrev_w, vsrev_l = rec(9)
            offw_w,  offw_l  = rec(10)
            offl_w,  offl_l  = rec(11)
            div_w,   div_l   = rec(12)
            ndiv_w,  ndiv_l  = rec(13)
            a35_w,   a35_l   = rec(14)
            s35_w,   s35_l   = rec(15)

            # Upsert coach — only update ATS splits, NOT name or years
            # Name and years come from parse_team_page (team first page)
            from app.models.coach import Coach
            coach_obj = db.query(Coach).filter(Coach.team_id == str(team.id)).first()
            if not coach_obj:
                coach = upsert_coach(db, str(team.id), {
                    "name"            : coach_name,
                    "years_with_team" : years,
                })
            else:
                coach = coach_obj

            # Upsert coach stats
            upsert_coach_stats(db, str(coach.id), {
                "home_ats_w"   : home_w,  "home_ats_l"   : home_l,
                "away_ats_w"   : away_w,  "away_ats_l"   : away_l,
                "fav_ats_w"    : fav_w,   "fav_ats_l"    : fav_l,
                "dog_ats_w"    : dog_w,   "dog_ats_l"    : dog_l,
                "rest_ats_w"   : rest_w,  "rest_ats_l"   : rest_l,
                "rev_ats_w"    : rev_w,   "rev_ats_l"    : rev_l,
                "vs_rev_ats_w" : vsrev_w, "vs_rev_ats_l" : vsrev_l,
                "off_win_ats_w": offw_w,  "off_win_ats_l": offw_l,
                "off_loss_ats_w": offl_w, "off_loss_ats_l": offl_l,
                "div_ats_w"    : div_w,   "div_ats_l"    : div_l,
                "ndiv_ats_w"   : ndiv_w,  "ndiv_ats_l"   : ndiv_l,
                "allow35_ats_w": a35_w,   "allow35_ats_l": a35_l,
                "score35_ats_w": s35_w,   "score35_ats_l": s35_l,
            })

            print(f"  ✓ {coach_name} ({abbr})")

        except Exception as e:
            errors.append(f"Row {row_idx}: {e}")

    if errors:
        print(f"  ✗ Errors: {len(errors)}")
        for e in errors:
            print(f"    {e}")


# ── Step 3: Parse + seed SOS data from PDF page 11 ───────────

def seed_sos_from_pdf(db, teams: dict):
    """
    Parse SOS data from PDF page 11.
    TABLE 1 + TABLE 2 = NFL Win Totals SOS (32 teams total).
    TABLE 3 = Conventional SOS (opp win %).
    Season year = 2025.
    """
    from app.repositories.stats_repo import upsert_sos_stat

    print("\n── Parsing SOS data (page 11) ────────────────────")
    result = analyze_pages(PDF_PATH, "11")

    # Collect win total SOS from TABLE 1 and TABLE 2
    win_total_rows = []
    for table in result.tables:
        if table.column_count == 6:
            grid = get_table_grid(table)
            # Skip header row
            for row_idx in range(1, table.row_count):
                team_name = grid.get((row_idx, 0), "").strip()
                if team_name and team_name.upper() != "TEAM":
                    win_total_rows.append({
                        "team"          : team_name,
                        "rank"          : safe_int(grid.get((row_idx, 1), "")),
                        "team_win_total": safe_float(grid.get((row_idx, 2), "")),
                        "foe_win_total" : safe_float(grid.get((row_idx, 3), "")),
                        "vs_div"        : safe_float(grid.get((row_idx, 4), "")),
                        "vs_nondiv"     : safe_float(grid.get((row_idx, 5), "")),
                    })

    # Collect conventional SOS (opp win %) from TABLE 3
    opp_win_pct = {}
    for table in result.tables:
        if table.column_count == 6:
            grid = get_table_grid(table)
            # Check if this is the conventional SOS table
            if grid.get((0, 2), "").strip().startswith("OPP"):
                for row_idx in range(1, table.row_count):
                    # Left side
                    t1 = grid.get((row_idx, 0), "").strip().lower()
                    p1 = safe_float(grid.get((row_idx, 2), ""))
                    if t1:
                        opp_win_pct[t1] = p1
                    # Right side
                    t2 = grid.get((row_idx, 3), "").strip().lower()
                    p2 = safe_float(grid.get((row_idx, 5), ""))
                    if t2:
                        opp_win_pct[t2] = p2

    errors = []
    seeded = 0

    for row in win_total_rows:
        try:
            team_name_lower = row["team"].strip().lower()
            abbr = PDF_NAME_TO_ABBR.get(team_name_lower)
            if not abbr:
                print(f"  ✗ Unknown team: {row['team']}")
                continue

            team = teams.get(abbr)
            if not team:
                continue

            opp_pct = opp_win_pct.get(team_name_lower)

            upsert_sos_stat(db, str(team.id), 2025, {
                "sos_rank"      : row["rank"],
                "team_win_total": row["team_win_total"],
                "foe_win_total" : row["foe_win_total"],
                "vs_div_wins"   : row["vs_div"],
                "vs_nondiv_wins": row["vs_nondiv"],
                "opp_win_pct"   : opp_pct,
            })

            print(f"  ✓ {row['team']} — rank {row['rank']}")
            seeded += 1

        except Exception as e:
            errors.append(f"{row['team']}: {e}")

    print(f"  Total seeded: {seeded}")
    if errors:
        for e in errors:
            print(f"  ✗ {e}")

# ── Step 3b: Seed CFB teams ───────────────────────────────────

def seed_cfb_teams(db) -> dict:
    from app.models.team import LeagueEnum
    from app.repositories.team_repo import upsert_team_by_name

    print("\n── Seeding CFB teams ─────────────────────────────")
    CFB_ABBR = {
        "Air Force"             : "AFA",
        "Akron"                 : "AKR",
        "Alabama"               : "ALA",
        "Appalachian State"     : "APP",
        "Arizona"               : "ARIZ",
        "Arizona State"         : "AZST",
        "Arkansas"              : "ARK",
        "Arkansas State"        : "ARST",
        "Army"                  : "ARMY",
        "Auburn"                : "AUB",
        "Ball State"            : "BALL",
        "Baylor"                : "BAY",
        "Boise State"           : "BOIS",
        "Boston College"        : "BC",
        "Bowling Green"         : "BGSU",
        "Buffalo"               : "BUFF",
        "BYU"                   : "BYU",
        "California"            : "CAL",
        "Central Michigan"      : "CMU",
        "Charlotte"             : "CHAR",
        "Cincinnati"            : "CIN",
        "Clemson"               : "CLEM",
        "Coastal Carolina"      : "CCU",
        "Colorado"              : "COLO",
        "Colorado State"        : "CSU",
        "Duke"                  : "DUKE",
        "East Carolina"         : "ECU",
        "Eastern Michigan"      : "EMU",
        "Florida"               : "FLA",
        "Florida Atlantic"      : "FAU",
        "Florida International" : "FIU",
        "Florida State"         : "FSU",
        "Fresno State"          : "FRES",
        "Georgia"               : "UGA",
        "Georgia Southern"      : "GASO",
        "Georgia State"         : "GAST",
        "Georgia Tech"          : "GT",
        "Hawai'i"               : "HAW",
        "Houston"               : "HOU",
        "Illinois"              : "ILL",
        "Indiana"               : "IND",
        "Iowa"                  : "IOWA",
        "Iowa State"            : "IAST",
        "Jacksonville State"    : "JVST",
        "James Madison"         : "JMU",
        "Kansas"                : "KAN",
        "Kansas State"          : "KAST",
        "Kennesaw State"        : "KENN",
        "Kent State"            : "KENT",
        "Kentucky"              : "UK",
        "Liberty"               : "LIB",
        "Louisiana"             : "ULL",
        "Louisiana Tech"        : "LAT",
        "Louisville"            : "LOU",
        "LSU"                   : "LSU",
        "Marshall"              : "MRSH",
        "Maryland"              : "MD",
        "Memphis"               : "MEM",
        "Miami Florida"         : "MIA",
        "Miami Ohio"            : "MIOH",
        "Michigan"              : "MICH",
        "Michigan State"        : "MSU",
        "Middle Tennessee State": "MTSU",
        "Minnesota"             : "MINN",
        "Mississippi State"     : "MSST",
        "Missouri"              : "MIZ",
        "Navy"                  : "NAVY",
        "NC State"              : "NCST",
        "Nebraska"              : "NEB",
        "Nevada"                : "NEV",
        "New Mexico"            : "UNM",
        "New Mexico State"      : "NMST",
        "North Carolina"        : "UNC",
        "North Texas"           : "UNT",
        "Northern Illinois"     : "NIU",
        "Northwestern"          : "NW",
        "Notre Dame"            : "ND",
        "Ohio State"            : "OSU",
        "Ohio University"       : "OHIO",
        "Oklahoma"              : "OU",
        "Oklahoma State"        : "OKST",
        "Old Dominion"          : "ODU",
        "Ole Miss"              : "MISS",
        "Oregon"                : "ORE",
        "Oregon State"          : "ORST",
        "Penn State"            : "PSU",
        "Pitt"                  : "PITT",
        "Purdue"                : "PUR",
        "Rice"                  : "RICE",
        "Rutgers"               : "RUT",
        "Sam Houston"           : "SHSU",
        "San Diego State"       : "SDSU",
        "San Jose State"        : "SJSU",
        "SMU"                   : "SMU",
        "South Alabama"         : "SOAL",
        "South Carolina"        : "SC",
        "Southern Miss"         : "USM",
        "Stanford"              : "STAN",
        "Syracuse"              : "SYR",
        "TCU"                   : "TCU",
        "Temple"                : "TEM",
        "Tennessee"             : "TENN",
        "Texas"                 : "TEX",
        "Texas A&M"             : "TAMU",
        "Texas State"           : "TXST",
        "Texas Tech"            : "TTU",
        "Toledo"                : "TOL",
        "Troy"                  : "TROY",
        "Tulane"                : "TUL",
        "Tulsa"                 : "TLSA",
        "UAB"                   : "UAB",
        "UCF"                   : "UCF",
        "UCLA"                  : "UCLA",
        "UConn"                 : "UCON",
        "UL Monroe"             : "ULM",
        "UMass"                 : "UMAS",
        "UNLV"                  : "UNLV",
        "USC"                   : "USC",
        "USF"                   : "USF",
        "Utah"                  : "UTAH",
        "Utah State"            : "UTST",
        "UTEP"                  : "UTEP",
        "UTSA"                  : "UTSA",
        "Vanderbilt"            : "VAN",
        "Virginia"              : "UVA",
        "Virginia Tech"         : "VT",
        "Wake Forest"           : "WAKE",
        "Washington"            : "WASH",
        "Washington State"      : "WAST",
        "West Virginia"         : "WVU",
        "Western Kentucky"      : "WKU",
        "Western Michigan"      : "WMU",
        "Wisconsin"             : "WISC",
        "Wyoming"               : "WYO",
        "Delaware"              : "DEL",
    }
    # Generate unique abbreviation from name
    def make_abbr(name):
        words = name.upper().replace("'", "").split()
        if len(words) == 1:
            return words[0][:8]
        abbr = "".join(w[0] for w in words)
        if len(abbr) < 3:
            abbr = words[0][:4] + "".join(w[0] for w in words[1:])
        return abbr[:8]

    teams = {}
    for name, meta in CFB_TEAMS_META.items():
        team = upsert_team_by_name(db, {
            "name"        : name,
            "abbreviation": CFB_ABBR.get(name, name[:8]),
            "league"      : LeagueEnum.CFB,
            "conference"  : meta["conference"],
            "division"    : meta["division"],
        })
        teams[name] = team

    print(f"  Total: {len(teams)} CFB teams")
    return teams




# girish
# ── Step 5: Parse 2025 Schedule Log ───────────────────────────

def parse_schedule_from_page(result, team, db, season_year=2025):
    import re
    from sqlalchemy import text

    # Schedule = TABLE 2: 23 rows x 10 cols
    sched_table = None
    for table in result.tables:
        if table.row_count >= 5 and table.column_count == 10:
            grid_check = get_table_grid(table)
            h1 = grid_check.get((1, 0), '').upper()
            if 'OPPONENT' in h1 or 'SCHEDULE' in grid_check.get((0, 1), '').upper():
                sched_table = table
                break

    if not sched_table:
        return 0

    grid    = get_table_grid(sched_table)
    game_num = 0
    saved   = 0

    for row_idx in range(2, sched_table.row_count):  # skip header rows 0 and 1
        try:
            opp_raw   = grid.get((row_idx, 0), '').strip()
            game_date = grid.get((row_idx, 1), '').strip()
            opp_record= grid.get((row_idx, 2), '').strip()
            adv_str  = grid.get((row_idx, 3), '').strip()   # ADV column
            line_str = grid.get((row_idx, 5), '').strip()    # LINE colum
            # col 4 = PF-PA (blank for future)
            # col 5 = LINE (blank for future)
            su        = grid.get((row_idx, 6), '').strip()
            ats       = grid.get((row_idx, 7), '').strip()
            ou        = grid.get((row_idx, 8), '').strip()
            scorecard = grid.get((row_idx, 9), '').strip()

            if not opp_raw or not game_date:
                continue
            if 'OPEN DATE' in opp_raw.upper():
                continue
            if not re.match(r'\d{1,2}/\d{1,2}', game_date):
                continue

            game_num += 1
            is_home = not opp_raw.lower().startswith('at ')
            opp = re.sub(r'^at\s+', '', opp_raw, flags=re.IGNORECASE).strip()
            opp = re.sub(r'[•\.\*]+\s*$', '', opp).strip()
            opp = re.sub(r'\s+[TM]$', '', opp).strip()  # remove Thursday/Monday suffix

            adv = None
            if adv_str and adv_str not in ('PK', 'pk', ''):
                try:
                    adv = float(adv_str)
                except:
                    pass
                
            # line_str is the ADV column e.g. "-4.5" or "+3.5" or "PK"
            spread = None
            if line_str and line_str not in ('PK', 'pk', ''):
                try:
                    spread = float(line_str)
                except:
                    pass

            db.execute(text("""
                INSERT INTO schedule_games
                    (id, team_id, season_year, game_num, opponent, game_date,
                    is_home, opp_record, adv, line, su_result, ats_result,
                    ou_result, ats_scorecard)
                VALUES
                    (gen_random_uuid(), :tid, :year, :gnum, :opp, :gdate,
                    :is_home, :rec, :adv, :line, :su, :ats, :ou, :sc)
                ON CONFLICT (team_id, season_year, game_num)
                DO UPDATE SET
                    opponent=EXCLUDED.opponent, opp_record=EXCLUDED.opp_record,
                    adv=EXCLUDED.adv, line=EXCLUDED.line, is_home=EXCLUDED.is_home,
                    su_result=EXCLUDED.su_result, ats_result=EXCLUDED.ats_result,
                    ou_result=EXCLUDED.ou_result, ats_scorecard=EXCLUDED.ats_scorecard,
                    updated_at=NOW()
            """), {
                'tid': str(team.id), 'year': season_year, 'gnum': game_num,
                'opp': opp, 'gdate': game_date, 'is_home': is_home,
                'rec': opp_record or None, 'adv': adv, 'line': spread,
                'su': su or None, 'ats': ats or None,
                'ou': ou or None, 'sc': scorecard or None,
            })
            saved += 1
        except Exception:
            pass

    db.commit()
    return saved


# ── Step 6: Parse 2024 Game Logs ──────────────────────────────

def parse_gamelogs_from_page(result, team, db, season_year=2024):
    import re
    from sqlalchemy import text

    # Find game log table: 19, 20, or 21 cols
    log_table = None
    for table in result.tables:
        if table.row_count >= 5 and table.column_count in [19, 20, 21]:
            log_table = table
            break

    if not log_table:
        return 0

    grid  = get_table_grid(log_table)
    ncols = log_table.column_count

    # Detect layout by checking if col1 row1 is a date
    col1_r1 = grid.get((1, 1), '').strip()
    col2_r1 = grid.get((1, 2), '').strip()

    if re.match(r'\d{1,2}/\d{1,2}', col1_r1):
        # Layout C: col0=opp, col1=date, offset=2
        layout = 'C'
    else:
        # Layout A/B/D: col0=at/✓, col1=opp, col2=date, offset=3
        layout = 'D' if ncols == 21 else 'A'

    game_num = 0
    saved    = 0

    for row_idx in range(1, log_table.row_count):
        try:
            if layout == 'C':
                # col0=opponent (may include "at" prefix)
                opp_raw   = grid.get((row_idx, 0), '').strip()
                game_date = grid.get((row_idx, 1), '').strip()
                is_home   = not re.match(r'^(at|/ at)\s', opp_raw, re.IGNORECASE)
                opp       = re.sub(r'^(✓|V|/|:selected:|\s)+', '', opp_raw).strip()
                opp       = re.sub(r'\n:selected:$', '', opp).strip()
                opp       = re.sub(r'^(at|/ at)\s+', '', opp, flags=re.IGNORECASE).strip()
                offset    = 2
            else:
                # Layout A/B/D: col0=at/✓, col1=opp (or empty), col2=date
                col0 = grid.get((row_idx, 0), '').strip()
                col1 = grid.get((row_idx, 1), '').strip()
                game_date = grid.get((row_idx, 2), '').strip()

                # Determine opponent and is_home
                col0_clean = re.sub(r'\n:selected:$', '', col0).strip()
                col0_clean = re.sub(r'^[✓V/\s]+', '', col0_clean).strip()

                if col1 and not re.match(r'\d{1,2}/\d{1,2}', col1):
                    # col1 has the opponent name
                    opp     = re.sub(r'\n:selected:$', '', col1).strip()
                    is_home = 'at' not in col0_clean.lower() and not re.match(r'^at\s', col0_clean, re.I)
                else:
                    # col0 has full "at Opponent" or just opponent
                    opp     = col0_clean
                    is_home = not re.match(r'^at\s', opp, re.IGNORECASE)
                    opp     = re.sub(r'^(at|/ at)\s+', '', opp, flags=re.IGNORECASE).strip()

                offset = 3

            if not opp or not re.match(r'\d{1,2}/\d{1,2}', game_date):
                continue
            if 'OPEN DATE' in opp.upper():
                continue
            # Clean trailing dots/symbols from opponent name
            opp = re.sub(r'[\.\·•\*]+\s*$', '', opp).strip()

            game_num += 1

            # For NYG layout D: there's an extra empty col at position offset+5
            # col order: OWL PF PA SU LINE [empty] ATS O/U ...
            if layout == 'D':
                opp_rec  = grid.get((row_idx, offset),   '').strip()
                pf_str   = grid.get((row_idx, offset+1), '').strip()
                pa_str   = grid.get((row_idx, offset+2), '').strip()
                su       = grid.get((row_idx, offset+3), '').strip()
                line_str = grid.get((row_idx, offset+4), '').strip()
                # offset+5 is empty col — skip
                ats      = grid.get((row_idx, offset+6), '').strip()
                ou_str   = grid.get((row_idx, offset+7), '').strip()
                oyp_str  = grid.get((row_idx, offset+8), '').strip()
                ofr_str  = grid.get((row_idx, offset+9), '').strip()
                ofp_str  = grid.get((row_idx, offset+10),'').strip()
                oyd_str  = grid.get((row_idx, offset+11),'').strip()
                dyd_str  = grid.get((row_idx, offset+12),'').strip()
                dfp_str  = grid.get((row_idx, offset+13),'').strip()
                dfr_str  = grid.get((row_idx, offset+14),'').strip()
                dyp_str  = grid.get((row_idx, offset+15),'').strip()
                res_str  = grid.get((row_idx, offset+16),'').strip()
                fa_str   = grid.get((row_idx, offset+17),'').strip()
            else:
                opp_rec  = grid.get((row_idx, offset),   '').strip()
                pf_str   = grid.get((row_idx, offset+1), '').strip()
                pa_str   = grid.get((row_idx, offset+2), '').strip()
                su       = grid.get((row_idx, offset+3), '').strip()
                line_str = grid.get((row_idx, offset+4), '').strip()
                ats      = grid.get((row_idx, offset+5), '').strip()
                ou_str   = grid.get((row_idx, offset+6), '').strip()
                oyp_str  = grid.get((row_idx, offset+7), '').strip()
                ofr_str  = grid.get((row_idx, offset+8), '').strip()
                ofp_str  = grid.get((row_idx, offset+9), '').strip()
                oyd_str  = grid.get((row_idx, offset+10),'').strip()
                dyd_str  = grid.get((row_idx, offset+11),'').strip()
                dfp_str  = grid.get((row_idx, offset+12),'').strip()
                dfr_str  = grid.get((row_idx, offset+13),'').strip()
                dyp_str  = grid.get((row_idx, offset+14),'').strip()
                # RES and F-A: separate or merged
                if ncols - offset >= 17:
                    res_str = grid.get((row_idx, offset+15),'').strip()
                    fa_str  = grid.get((row_idx, offset+16),'').strip()
                else:
                    res_fa  = grid.get((row_idx, offset+15),'').strip().split()
                    res_str = res_fa[0] if res_fa else None
                    fa_str  = res_fa[1] if len(res_fa) > 1 else None

            pf      = int(pf_str)   if pf_str.isdigit()   else None
            pa      = int(pa_str)   if pa_str.isdigit()   else None
            spread  = None if line_str in ('Pk','pk','') else safe_float(line_str)
            ou_line = safe_float(re.sub(r'[OUTou]','', ou_str)) if re.search(r'\d', ou_str) else None
            ou_res  = 'O' if ou_str.startswith('O') else ('U' if ou_str.startswith('U') else ('P' if ou_str.startswith('T') else None))
            oyp     = safe_float(oyp_str)
            ofr     = int(ofr_str)  if ofr_str.isdigit()  else None
            ofp     = int(ofp_str)  if ofp_str.isdigit()  else None
            oyd     = int(oyd_str)  if oyd_str.isdigit()  else None
            dyd     = int(dyd_str)  if dyd_str.isdigit()  else None
            dfp     = int(dfp_str)  if dfp_str.isdigit()  else None
            dfr     = int(dfr_str)  if dfr_str.isdigit()  else None
            dyp     = safe_float(dyp_str)

            db.execute(text("""
                INSERT INTO game_logs
                    (id, team_id, season_year, game_num, opponent, game_date,
                     is_home, opp_record, points_for, points_against, su_result,
                     line, ats_result, ou_line, ou_result,
                     off_ypr, off_rush, off_pass, off_total,
                     def_total, def_pass, def_rush, def_ypr,
                     result_score, first_downs)
                VALUES
                    (gen_random_uuid(), :tid, :year, :gnum, :opp, :gdate,
                     :is_home, :rec, :pf, :pa, :su,
                     :line, :ats, :ou_line, :ou_res,
                     :oyp, :ofr, :ofp, :oyd,
                     :dyd, :dfp, :dfr, :dyp,
                     :res, :fa)
                ON CONFLICT (team_id, season_year, game_num)
                DO UPDATE SET
                    opponent=EXCLUDED.opponent, points_for=EXCLUDED.points_for,
                    points_against=EXCLUDED.points_against, su_result=EXCLUDED.su_result,
                    line=EXCLUDED.line, ats_result=EXCLUDED.ats_result,
                    ou_result=EXCLUDED.ou_result, off_ypr=EXCLUDED.off_ypr,
                    off_rush=EXCLUDED.off_rush, off_pass=EXCLUDED.off_pass,
                    off_total=EXCLUDED.off_total, def_total=EXCLUDED.def_total,
                    def_pass=EXCLUDED.def_pass, def_rush=EXCLUDED.def_rush,
                    def_ypr=EXCLUDED.def_ypr, result_score=EXCLUDED.result_score,
                    updated_at=NOW()
            """), {
                'tid': str(team.id), 'year': season_year, 'gnum': game_num,
                'opp': opp, 'gdate': game_date, 'is_home': is_home,
                'rec': opp_rec, 'pf': pf, 'pa': pa, 'su': su or None,
                'line': spread, 'ats': ats or None,
                'ou_line': ou_line, 'ou_res': ou_res,
                'oyp': oyp, 'ofr': ofr, 'ofp': ofp, 'oyd': oyd,
                'dyd': dyd, 'dfp': dfp, 'dfr': dfr, 'dyp': dyp,
                'res': res_str or None, 'fa': fa_str or None,
            })
            saved += 1

        except Exception:
            pass

    db.commit()
    return saved


# ── Step 7: Parse 2025 Draft Picks ────────────────────────────

def parse_draft_picks_from_page(result, team, db, draft_year=2025):
    import re
    from sqlalchemy import text

    saved = 0
    found_rounds = set()

    # Method 1: Table detection (5 or 6 col draft table)
    for table in result.tables:
        if table.row_count >= 2 and table.column_count in [5, 6]:
            grid_check = get_table_grid(table)
            h0 = grid_check.get((0, 0), '').upper()
            h1 = grid_check.get((0, 1), '').upper()
            if 'ROUND' in h0 or 'ROUND' in h1 or 'PLAYER' in h0 or 'PLAYER' in h1:
                grid    = grid_check
                is_5col = table.column_count == 5

                for row_idx in range(1, table.row_count):
                    try:
                        if is_5col:
                            round_player = grid.get((row_idx, 0), '').strip()
                            m = re.match(r'^(\d+)\s+(.+)$', round_player)
                            if not m:
                                continue
                            round_str   = m.group(1)
                            player_name = m.group(2).strip()
                            position    = grid.get((row_idx, 1), '').strip()
                            height      = grid.get((row_idx, 2), '').strip()
                            weight_str  = grid.get((row_idx, 3), '').strip()
                            college     = grid.get((row_idx, 4), '').strip()
                        else:
                            round_str   = grid.get((row_idx, 0), '').strip()
                            player_name = grid.get((row_idx, 1), '').strip()
                            position    = grid.get((row_idx, 2), '').strip()
                            height      = grid.get((row_idx, 3), '').strip()
                            weight_str  = grid.get((row_idx, 4), '').strip()
                            college     = grid.get((row_idx, 5), '').strip()

                        if not round_str.isdigit() or not player_name:
                            continue

                        rnd = int(round_str)
                        found_rounds.add(rnd)

                        db.execute(text("""
                            INSERT INTO draft_picks
                                (id, team_id, draft_year, round_num, player_name,
                                 position, height, weight, college)
                            VALUES
                                (gen_random_uuid(), :tid, :year, :rnd, :name,
                                 :pos, :ht, :wt, :col)
                            ON CONFLICT DO NOTHING
                        """), {
                            'tid': str(team.id), 'year': draft_year,
                            'rnd': rnd, 'name': player_name,
                            'pos': position, 'ht': height,
                            'wt': int(weight_str) if weight_str.isdigit() else None,
                            'col': college,
                        })
                        saved += 1
                    except Exception:
                        pass
                break

    # Method 2: Single-line scanning
    lines = []
    for page in result.pages:
        lines = [l.content.strip() for l in page.lines]
        break

    POSITIONS = r'(DT|DE|CB|S|LB|OL|OG|OT|OC|C|QB|RB|WR|TE|Edge|EDGE|K|P|LS|NT|ILB|OLB|G)'

    for line in lines:
        line = line.strip()
        m = re.match(
            rf'^(\d+)\s+(.+?)\s+{POSITIONS}\s+(\d[\'\d"´\u2019\u201d]+)\s+(\d{{2,3}})\s+(.+)$',
            line
        )
        if m:
            rnd = int(m.group(1))
            if rnd in found_rounds:
                continue
            if not (1 <= rnd <= 7):
                continue
            found_rounds.add(rnd)
            try:
                db.execute(text("""
                    INSERT INTO draft_picks
                        (id, team_id, draft_year, round_num, player_name,
                         position, height, weight, college)
                    VALUES
                        (gen_random_uuid(), :tid, :year, :rnd, :name,
                         :pos, :ht, :wt, :col)
                    ON CONFLICT DO NOTHING
                """), {
                    'tid': str(team.id), 'year': draft_year,
                    'rnd': rnd, 'name': m.group(2).strip(),
                    'pos': m.group(3).strip(), 'ht': m.group(4).strip(),
                    'wt': int(m.group(5)) if m.group(5).isdigit() else None,
                    'col': m.group(6).strip(),
                })
                saved += 1
            except Exception:
                pass

    # Method 3: Multi-line combining (for teams where pick data is split across lines)
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        m_start = re.match(r'^(\d+)\s+([A-Z][a-zA-Z\s\'.]+)$', line)
        if m_start:
            rnd = int(m_start.group(1))
            if 1 <= rnd <= 7 and rnd not in found_rounds:
                # Combine with next 3 lines
                combined = line
                for j in range(1, 4):
                    if i + j < len(lines):
                        combined += ' ' + lines[i + j].strip()

                m = re.match(
                    rf'^(\d+)\s+(.+?)\s+{POSITIONS}\s+(\d[\'\d"´\u2019\u201d]+)\s+(\d{{2,3}})\s+(.+)$',
                    combined.strip()
                )
                if m:
                    found_rounds.add(rnd)
                    try:
                        db.execute(text("""
                            INSERT INTO draft_picks
                                (id, team_id, draft_year, round_num, player_name,
                                 position, height, weight, college)
                            VALUES
                                (gen_random_uuid(), :tid, :year, :rnd, :name,
                                 :pos, :ht, :wt, :col)
                            ON CONFLICT DO NOTHING
                        """), {
                            'tid': str(team.id), 'year': draft_year,
                            'rnd': rnd, 'name': m.group(2).strip(),
                            'pos': m.group(3).strip(), 'ht': m.group(4).strip(),
                            'wt': int(m.group(5)) if m.group(5).isdigit() else None,
                            'col': m.group(6).strip(),
                        })
                        saved += 1
                    except Exception:
                        pass
        i += 1

    db.commit()
    return saved

def seed_nfl_game_data_from_pdf(db, teams: dict, test_abbr: str = None):
    print("\n── Parsing NFL Schedule/GameLogs/Drafts ─────────────")

    team_list = [(abbr, page) for abbr, page in NFL_TEAM_PAGES.items()
                 if not test_abbr or abbr == test_abbr.upper()]

    success = 0
    for abbr, page in team_list:
        team = teams.get(abbr)
        if not team:
            continue
        try:
            print(f"  Parsing {abbr} (page {page})...")
            result = analyze_pages(PDF_PATH, str(page))
            s = parse_schedule_from_page(result, team, db)
            g = parse_gamelogs_from_page(result, team, db)
            d = parse_draft_picks_from_page(result, team, db)
            print(f"  ✓ {abbr}: {s} schedule, {g} game logs, {d} draft picks")
            success += 1
        except Exception as e:
            print(f"  ✗ {abbr} failed: {e}")

    print(f"\n  Done: {success} teams")







# ── Step 4b: Parse CFB team stats ─────────────────────────────

def parse_cfb_team_page(result, name: str, teams: dict, db) -> bool:
    from app.repositories.stats_repo import upsert_season_stat
    import re

    team = teams.get(name)
    if not team:
        print(f"  X CFB team not found: {name}")
        return False

    lines = []
    for page in result.pages:
        lines = [l.content.strip() for l in page.lines]
        break

    # Find where schedule/game history starts and cut off there
    cutoff = len(lines)
    for idx, line in enumerate(lines):
        if 'SCHEDULE LOG' in line.upper():
            cutoff = idx
            break
        if re.match(r'^\d{4}\s*[-–]\s*[A-Z]', line) and idx > 20:
            cutoff = idx
            break
    lines = lines[:cutoff]

    parsed = 0
    i = 0
    while i < len(lines):
        line = lines[i]

        m = re.match(r'^\*?(\d{4})\b', line)
        if m:
            year_str = m.group(1)
            if year_str == "2924":
                year_str = "2024"

            if year_str in ["2021", "2022", "2023", "2024"]:
                year = int(year_str)

                # Combine this line with next lines to get complete data
                combined = line
                for j in range(1, 25):
                    if i + j < len(lines):
                        next_line = lines[i + j]
                        if re.match(r'^\*?20\d{2}\b', next_line):
                            break
                        combined += " " + next_line

                # Normalize placeholders
                combined = combined.replace('\u2013', '0-0').replace('\u2014', '0-0')
                combined = combined.replace('_', '0-0')
                combined = re.sub(r'\s+-\s+-\s+', ' 0-0 0-0 ', combined)
                combined = re.sub(r'\s+-\s+', ' 0-0 ', combined)

                # Extract all W-L records
                records = re.findall(r'\d+-\d+(?:-\d+)?', combined)

                # Extract numbers — skip year (>=2000) and 2 starters
                nums_text = re.sub(r'\d+-\d+(?:-\d+)?', ' ', combined)
                all_nums = re.findall(r'\b(\d+(?:\.\d+)?)\b', nums_text)

                ret_off = None
                ret_def = None
                nums = []
                od_count = 0
                
                for n in all_nums:
                    fval = float(n)
                    if fval >= 2000:
                        continue
                    
                    if od_count < 2:
                        # First two numbers after year are O and D
                        if od_count == 0:
                            ret_off = int(fval)
                        else:
                            ret_def = int(fval)
                        od_count += 1
                        continue
                    if fval < 1000:
                        nums.append(fval)

                nums = []
                skip_count = 2
                for n in all_nums:
                    fval = float(n)
                    if fval >= 2000:
                        continue
                    if skip_count > 0:
                        skip_count -= 1
                        continue
                    if fval < 1000:
                        nums.append(fval)

                if len(records) >= 2:
                    try:
                        su_w,  su_l,  _     = parse_record_3(records[0])
                        ats_w, ats_l, ats_p = parse_record_3(records[1])

                        # Default all splits to 0
                        div_su_w = div_su_l = div_ats_w = div_ats_l = 0
                        hf_w = hf_l = hd_w = hd_l = 0
                        rd_w = rd_l = rf_w = rf_l = 0

                        if len(records) >= 8:
                            div_su_w,  div_su_l,  _ = parse_record_3(records[2])
                            div_ats_w, div_ats_l, _ = parse_record_3(records[3])
                            hf_w, hf_l, _ = parse_record_3(records[4])
                            hd_w, hd_l, _ = parse_record_3(records[5])
                            rd_w, rd_l, _ = parse_record_3(records[6])
                            rf_w, rf_l, _ = parse_record_3(records[7])
                        elif len(records) >= 6:
                            hf_w, hf_l, _ = parse_record_3(records[2])
                            hd_w, hd_l, _ = parse_record_3(records[3])
                            rd_w, rd_l, _ = parse_record_3(records[4])
                            rf_w, rf_l, _ = parse_record_3(records[5])

                        pf      = nums[0] if len(nums) > 0 else None
                        pa      = nums[1] if len(nums) > 1 else None
                        off_ypr = nums[2] if len(nums) > 2 else None
                        off_rsh = nums[3] if len(nums) > 3 else None
                        off_pss = nums[4] if len(nums) > 4 else None
                        off_tot = nums[5] if len(nums) > 5 else None
                        def_tot = nums[6] if len(nums) > 6 else None
                        def_pss = nums[7] if len(nums) > 7 else None
                        def_rsh = nums[8] if len(nums) > 8 else None
                        def_ypr = nums[9] if len(nums) > 9 else None

                        upsert_season_stat(db, str(team.id), year, {
                            "su_wins"           : su_w,
                            "su_losses"         : su_l,
                            "ats_wins"          : ats_w,
                            "ats_losses"        : ats_l,
                            "ats_pushes"        : ats_p,
                            "div_su_wins"       : div_su_w,
                            "div_su_losses"     : div_su_l,
                            "div_ats_wins"      : div_ats_w,
                            "div_ats_losses"    : div_ats_l,
                            "home_fav_ats_w"    : hf_w,
                            "home_fav_ats_l"    : hf_l,
                            "home_dog_ats_w"    : hd_w,
                            "home_dog_ats_l"    : hd_l,
                            "road_dog_ats_w"    : rd_w,
                            "road_dog_ats_l"    : rd_l,
                            "road_fav_ats_w"    : rf_w,
                            "road_fav_ats_l"    : rf_l,
                            "points_for_avg"    : pf,
                            "points_against_avg": pa,
                            "off_ypr"           : off_ypr,
                            "off_rush_avg"      : off_rsh,
                            "off_pass_avg"      : off_pss,
                            "off_total_avg"     : off_tot,
                            "def_total_avg"     : def_tot,
                            "def_pass_avg"      : def_pss,
                            "def_rush_avg"      : def_rsh,
                            "def_ypr"           : def_ypr,
                            "ret_off_starters" : ret_off,
                            "ret_def_starters" : ret_def,
                            "recruit_rank"     : int(nums[10]) if len(nums) > 10 else None,
                            "recruit_5star"    : int(nums[11]) if len(nums) > 11 else None,
                            "recruit_4star"    : int(nums[12]) if len(nums) > 12 else None,
                            "recruit_3star"    : int(nums[13]) if len(nums) > 13 else None,
                            "recruit_total"    : int(nums[14]) if len(nums) > 14 else None,
                        })
                        parsed += 1

                    except Exception as e:
                        print(f"  X Error parsing CFB year {year_str} for {name}: {e}")

        i += 1

    if parsed == 0:
        print(f"  X CFB no years parsed for {name}")
        return False

    return True


def seed_cfb_stats_from_pdf(db, teams: dict, test_name: str = None, resume: bool = False):
    print("\n── Parsing CFB team stats from PDF ──────────────")

    team_names = [test_name] if test_name else list(CFB_TEAM_PAGES.keys())
    success = 0
    skipped = 0
    errors  = []

    for name in team_names:
        page_num = CFB_TEAM_PAGES.get(name)
        if not page_num:
            print(f"  X No page mapping for {name}")
            continue

        # Resume mode — skip teams that already have 4 years
        if resume and not test_name:
            team = teams.get(name)
            if team:
                from sqlalchemy import text
                count = db.execute(
                    text("SELECT COUNT(*) FROM season_stats WHERE team_id = :tid"),
                    {"tid": str(team.id)}
                ).scalar()
                # Delaware only has 2 years, Kennesaw State has 3
                min_years = 2 if name in ["Delaware"] else 3 if name in ["Kennesaw State", "Jacksonville State", "Sam Houston", "James Madison"] else 4
                if count >= min_years:
                    skipped += 1
                    continue

        try:
            print(f"  Parsing {name} (page {page_num})...")
            result = analyze_pages(PDF_PATH, str(page_num))
            ok = parse_cfb_team_page(result, name, teams, db)
            if ok:
                print(f"  ✓ {name} done")
                success += 1
            else:
                errors.append(name)
        except Exception as e:
            print(f"  X {name} failed: {e}")
            errors.append(name)

    print(f"\n  Parsed: {success} CFB teams")
    if skipped:
        print(f"  Skipped: {skipped} teams (already complete)")
    if errors:
        print(f"  Failed: {errors}")
# ── Step 4: Parse team page stats ────────────────────────────

def parse_team_page(result, abbr: str, teams: dict, db) -> bool:
    from app.repositories.stats_repo import upsert_season_stat, upsert_trend
    import re

    team = teams.get(abbr)
    print(f"  DEBUG team lookup: abbr={abbr}, found={team is not None}")
    if not team:
        print(f"  ✗ Team not found: {abbr}")
        return False

    # ── Parse coach info from page lines ──────────────────────
    import re as _re
    from app.repositories.coach_repo import upsert_coach

    print(f"  DEBUG result type: {type(result)}, attrs: {[a for a in dir(result) if not a.startswith('_')][:10]}")

    coach_lines = []
    for page in result.pages:
        print(f"  DEBUG: pages={len(result.pages)}, lines={len(result.pages[0].lines) if result.pages else 0}")
        coach_lines = [l.content.strip() for l in page.lines]
        break

    coach_name    = None
    years         = None
    su_w_c = su_l_c = None
    ats_w_c = ats_l_c = ats_p_c = None


    coach_first = None
    coach_last  = None

    for line in coach_lines[:20]:
        if line:
            print(f"  COACH LINE: {repr(line)}")
        if not line:
            continue

        # Record line — check first
        rec_m = _re.search(r'(\d+)-(\d+)\s+SU\s*[/•·]\s*(\d+)-(\d+)(?:-(\d+))?\s+ATS', line, _re.IGNORECASE)
        if rec_m and su_w_c is None:
            su_w_c  = int(rec_m.group(1))
            su_l_c  = int(rec_m.group(2))
            ats_w_c = int(rec_m.group(3))
            ats_l_c = int(rec_m.group(4))
            ats_p_c = int(rec_m.group(5)) if rec_m.group(5) else 0
            continue

        # Year line
        yr_m = _re.search(r'^(\w+)\s+year$', line, _re.IGNORECASE)
        if yr_m and years is None:
            word = yr_m.group(1).lower()
            year_words = {'first':1,'second':2,'third':3,'fourth':4,'fifth':5,
                         'sixth':6,'seventh':7,'eighth':8,'ninth':9,'tenth':10,
                         'eleventh':11,'twelfth':12,'thirteenth':13,'fourteenth':14,
                         'fifteenth':15,'sixteenth':16,'seventeenth':17,'eighteenth':18,
                         'nineteenth':19,'twentieth':20}
            if word in year_words:
                years = year_words[word]
            else:
                ord_m = _re.match(r'(\d+)', word)
                if ord_m:
                    years = int(ord_m.group(1))
            continue

        # Skip known non-name lines
        skip = ['head coach', 'record with', 'capacity', 'www.', 'scoring',
                'year', 'offensive', 'defensive', 'arizona', 'atlanta', 'baltimore',
                'buffalo', 'carolina', 'chicago', 'cincinnati', 'cleveland', 'dallas',
                'denver', 'detroit', 'green bay', 'houston', 'indianapolis',
                'jacksonville', 'kansas city', 'las vegas', 'los angeles', 'miami',
                'minnesota', 'new england', 'new orleans', 'new york', 'philadelphia',
                'pittsburgh', 'san francisco', 'seattle', 'tampa bay', 'tennessee',
                'washington', 'cardinals', 'falcons', 'ravens', 'bills', 'panthers',
                'bears', 'bengals', 'browns', 'cowboys', 'broncos', 'lions', 'packers',
                'texans', 'colts', 'jaguars', 'chiefs', 'raiders', 'chargers', 'rams',
                'dolphins', 'vikings', 'patriots', 'saints', 'giants', 'jets', 'eagles',
                'steelers', '49ers', 'seahawks', 'buccaneers', 'titans', 'commanders']
        if any(s in line.lower() for s in skip):
            continue

        # Single ALL CAPS word — could be first or last name
        if _re.match(r'^[A-Z]+$', line) and 2 < len(line) < 20:
            print(f"  NAME CANDIDATE: {repr(line)} first={coach_first} last={coach_last}")
            if coach_first is None:
                coach_first = line
            elif coach_last is None:
                coach_last = line
            continue

    if coach_first and coach_last:
        coach_name = coach_first + ' ' + coach_last
    elif coach_first:
        coach_name = coach_first

    if coach_name:
        from app.repositories.coach_repo import upsert_coach as _upsert_coach
        _upsert_coach(db, str(team.id), {
            'name'             : coach_name,
            'years_with_team'  : years or 1,
            'record_su_wins'   : su_w_c or 0,
            'record_su_losses' : su_l_c or 0,
            'record_ats_wins'  : ats_w_c,
            'record_ats_losses': ats_l_c,
            'record_ats_pushes': ats_p_c,
        })
        print(f"  ✓ Coach updated: {coach_name} ({years} yrs) SU:{su_w_c}-{su_l_c} ATS:{ats_w_c}-{ats_l_c}")

    # Find the 4-year stat table

    # Find the 4-year stat table
    stat_table = None
    for table in result.tables:
        if table.row_count == 6 and table.column_count in [12, 13, 14, 15, 16, 17, 18]:
            stat_table = table
            break

    if not stat_table:
        print(f"  ✗ Stat table not found for {abbr}")
        return False

    grid     = get_table_grid(stat_table)
    num_cols = stat_table.column_count

    for row_idx in range(2, 6):
        try:
            year_str = grid.get((row_idx, 0), "").strip()
            if year_str not in ["2021", "2022", "2023", "2024"]:
                continue
            year = int(year_str)

            # ── Defaults ──────────────────────────────────────
            su_w = su_l = ats_w = ats_l = ats_p = 0
            div_su_w = div_su_l = div_ats_w = div_ats_l = 0
            hf_w = hf_l = hd_w = hd_l = rd_w = rd_l = rf_w = rf_l = 0
            pf = pa = off_ypr = off_rsh = off_pss = off_tot = None
            def_tot = def_pss = def_rsh = def_ypr = None

            # ── Parse by column count ─────────────────────────

            if num_cols == 18:
                # ARI — all columns separate
                su_w,  su_l,  _     = parse_record_3(grid.get((row_idx, 1), "0-0"))
                ats_w, ats_l, ats_p = parse_record_3(grid.get((row_idx, 2), "0-0"))
                div_su_w,  div_su_l,  _ = parse_record_3(grid.get((row_idx, 3), "0-0"))
                div_ats_w, div_ats_l, _ = parse_record_3(grid.get((row_idx, 4), "0-0"))
                hf_w, hf_l, _ = parse_record_3(grid.get((row_idx, 5), "0-0"))
                hd_w, hd_l, _ = parse_record_3(grid.get((row_idx, 6), "0-0"))
                rd_w, rd_l, _ = parse_record_3(grid.get((row_idx, 7), "0-0"))
                rf_w, rf_l, _ = parse_record_3(grid.get((row_idx, 8), "0-0"))
                pf_pa = grid.get((row_idx, 9), "").strip().split()
                pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                off_ypr = safe_float(grid.get((row_idx, 10), ""))
                off_rsh = safe_float(grid.get((row_idx, 11), ""))
                off_pss = safe_float(grid.get((row_idx, 12), ""))
                off_tot = safe_float(grid.get((row_idx, 13), ""))
                def_tot = safe_float(grid.get((row_idx, 14), ""))
                def_pss = safe_float(grid.get((row_idx, 15), ""))
                def_rsh = safe_float(grid.get((row_idx, 16), ""))
                def_ypr = safe_float(grid.get((row_idx, 17), ""))

            elif num_cols == 17:
                # CLE or CAR — detect by col 7
                su_w,  su_l,  _     = parse_record_3(grid.get((row_idx, 1), "0-0"))
                ats_w, ats_l, ats_p = parse_record_3(grid.get((row_idx, 2), "0-0"))
                div_su_w,  div_su_l,  _ = parse_record_3(grid.get((row_idx, 3), "0-0"))
                div_ats_w, div_ats_l, _ = parse_record_3(grid.get((row_idx, 4), "0-0"))
                hf_w, hf_l, _ = parse_record_3(grid.get((row_idx, 5), "0-0"))
                hd_w, hd_l, _ = parse_record_3(grid.get((row_idx, 6), "0-0"))

                col7 = grid.get((row_idx, 7), "").strip()
                col7_parts = col7.split()

                if len(col7_parts) >= 2:
                    # CAR: col7=RD+RF merged, col8=PF PA, col9=off_ypr, col16=def_ypr
                    rd_w, rd_l, _ = parse_record_3(col7_parts[0])
                    rf_w, rf_l, _ = parse_record_3(col7_parts[1] if len(col7_parts) > 1 else "0-0")
                    pf_pa = grid.get((row_idx, 8), "").strip().split()
                    pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                    pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                    off_ypr = safe_float(grid.get((row_idx, 9),  ""))
                    off_rsh = safe_float(grid.get((row_idx, 10), ""))
                    off_pss = safe_float(grid.get((row_idx, 11), ""))
                    off_tot = safe_float(grid.get((row_idx, 12), ""))
                    def_tot = safe_float(grid.get((row_idx, 13), ""))
                    def_pss = safe_float(grid.get((row_idx, 14), ""))
                    def_rsh = safe_float(grid.get((row_idx, 15), ""))
                    def_ypr = safe_float(grid.get((row_idx, 16), ""))
                else:
                    # CLE: col7=RD, col8=RF, col9=PF PA, col10=Ypr+Rsh merged, col16=def_ypr
                    rd_w, rd_l, _ = parse_record_3(col7)
                    rf_w, rf_l, _ = parse_record_3(grid.get((row_idx, 8), "0-0"))
                    pf_pa = grid.get((row_idx, 9), "").strip().split()
                    pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                    pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                    yr_rsh = grid.get((row_idx, 10), "").strip().split()
                    off_ypr = safe_float(yr_rsh[0]) if len(yr_rsh) > 0 else None
                    off_rsh = safe_float(yr_rsh[1]) if len(yr_rsh) > 1 else None
                    off_pss = safe_float(grid.get((row_idx, 11), ""))
                    off_tot = safe_float(grid.get((row_idx, 12), ""))
                    def_tot = safe_float(grid.get((row_idx, 13), ""))
                    def_pss = safe_float(grid.get((row_idx, 14), ""))
                    rsh_ypr = grid.get((row_idx, 15), "").strip().split()
                    def_rsh = safe_float(rsh_ypr[0]) if rsh_ypr else None
                    def_ypr_16 = safe_float(grid.get((row_idx, 16), ""))
                    def_ypr = def_ypr_16 if def_ypr_16 else (safe_float(rsh_ypr[1]) if len(rsh_ypr) > 1 else None)

            elif num_cols == 16:
                # KC — SU+ATS merged, DIV merged, HF/HD/RD/RF separate
                p = grid.get((row_idx, 1), "0-0 0-0").strip().split()
                su_w,  su_l,  _     = parse_record_3(p[0] if len(p) > 0 else "0-0")
                ats_w, ats_l, ats_p = parse_record_3(p[1] if len(p) > 1 else "0-0")
                d = grid.get((row_idx, 2), "0-0 0-0").strip().split()
                div_su_w,  div_su_l,  _ = parse_record_3(d[0] if len(d) > 0 else "0-0")
                div_ats_w, div_ats_l, _ = parse_record_3(d[1] if len(d) > 1 else "0-0")
                hf_w, hf_l, _ = parse_record_3(grid.get((row_idx, 3), "0-0"))
                hd_w, hd_l, _ = parse_record_3(grid.get((row_idx, 4), "0-0"))
                rd_w, rd_l, _ = parse_record_3(grid.get((row_idx, 5), "0-0"))
                rf_w, rf_l, _ = parse_record_3(grid.get((row_idx, 6), "0-0"))
                pf_pa = grid.get((row_idx, 7), "").strip().split()
                pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                off_ypr = safe_float(grid.get((row_idx, 8),  ""))
                off_rsh = safe_float(grid.get((row_idx, 9),  ""))
                off_pss = safe_float(grid.get((row_idx, 10), ""))
                off_tot = safe_float(grid.get((row_idx, 11), ""))
                def_tot = safe_float(grid.get((row_idx, 12), ""))
                def_pss = safe_float(grid.get((row_idx, 13), ""))
                def_rsh = safe_float(grid.get((row_idx, 14), ""))
                def_ypr = safe_float(grid.get((row_idx, 15), ""))

            elif num_cols == 15:
                col1 = grid.get((row_idx, 1), "").strip()
                if " " in col1:
                    # NYG layout — SU+ATS merged, DIV merged, HF+HD merged, RD+RF merged
                    p = col1.split()
                    su_w,  su_l,  _     = parse_record_3(p[0] if len(p) > 0 else "0-0")
                    ats_w, ats_l, ats_p = parse_record_3(p[1] if len(p) > 1 else "0-0")
                    d = grid.get((row_idx, 2), "0-0 0-0").strip().split()
                    div_su_w,  div_su_l,  _ = parse_record_3(d[0] if len(d) > 0 else "0-0")
                    div_ats_w, div_ats_l, _ = parse_record_3(d[1] if len(d) > 1 else "0-0")
                    hf_hd = grid.get((row_idx, 3), "0-0 0-0").strip().split()
                    hf_w, hf_l, _ = parse_record_3(hf_hd[0] if len(hf_hd) > 0 else "0-0")
                    hd_w, hd_l, _ = parse_record_3(hf_hd[1] if len(hf_hd) > 1 else "0-0")
                    rd_rf = grid.get((row_idx, 4), "0-0 0-0").strip().split()
                    rd_w, rd_l, _ = parse_record_3(rd_rf[0] if len(rd_rf) > 0 else "0-0")
                    rf_w, rf_l, _ = parse_record_3(rd_rf[1] if len(rd_rf) > 1 else "0-0")
                    pf_pa = grid.get((row_idx, 6), "").strip().split()
                    pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                    pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                    off_ypr = safe_float(grid.get((row_idx, 7),  ""))
                    off_rsh = safe_float(grid.get((row_idx, 8),  ""))
                    off_pss = safe_float(grid.get((row_idx, 9),  ""))
                    off_tot = safe_float(grid.get((row_idx, 10), ""))
                    def_tot = safe_float(grid.get((row_idx, 11), ""))
                    def_pss = safe_float(grid.get((row_idx, 12), ""))
                    def_rsh = safe_float(grid.get((row_idx, 13), ""))
                    def_ypr = safe_float(grid.get((row_idx, 14), ""))
                else:
                    # NO/SEA layout — SU/ATS/DIV separate, HF separate
                    su_w,  su_l,  _     = parse_record_3(grid.get((row_idx, 1), "0-0"))
                    ats_w, ats_l, ats_p = parse_record_3(grid.get((row_idx, 2), "0-0"))
                    div_su_w,  div_su_l,  _ = parse_record_3(grid.get((row_idx, 3), "0-0"))
                    div_ats_w, div_ats_l, _ = parse_record_3(grid.get((row_idx, 4), "0-0"))

                    col5 = grid.get((row_idx, 5), "").strip()
                    col5_parts = col5.split()

                    if len(col5_parts) >= 4:
                        # SEA layout — col5=HF HD RD RF all merged, col6=PF PA
                        hf_w, hf_l, _ = parse_record_3(col5_parts[0])
                        hd_w, hd_l, _ = parse_record_3(col5_parts[1] if len(col5_parts) > 1 else "0-0")
                        rd_w, rd_l, _ = parse_record_3(col5_parts[2] if len(col5_parts) > 2 else "0-0")
                        rf_w, rf_l, _ = parse_record_3(col5_parts[3] if len(col5_parts) > 3 else "0-0")
                        pf_pa = grid.get((row_idx, 6), "").strip().split()
                        pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                        pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                        off_ypr = safe_float(grid.get((row_idx, 7),  ""))
                        off_rsh = safe_float(grid.get((row_idx, 8),  ""))
                        off_pss = safe_float(grid.get((row_idx, 9),  ""))
                        off_tot = safe_float(grid.get((row_idx, 10), ""))
                        def_tot = safe_float(grid.get((row_idx, 11), ""))
                        def_pss = safe_float(grid.get((row_idx, 12), ""))
                        def_rsh = safe_float(grid.get((row_idx, 13), ""))
                        def_ypr = safe_float(grid.get((row_idx, 14), ""))
                    else:
                        # NO layout — col5=HF, col6=HD+RD+RF merged, col7=PF PA
                        hf_w, hf_l, _ = parse_record_3(col5)
                        hd_rd_rf = grid.get((row_idx, 6), "0-0 0-0 0-0").strip().split()
                        hd_w, hd_l, _ = parse_record_3(hd_rd_rf[0] if len(hd_rd_rf) > 0 else "0-0")
                        rd_w, rd_l, _ = parse_record_3(hd_rd_rf[1] if len(hd_rd_rf) > 1 else "0-0")
                        rf_w, rf_l, _ = parse_record_3(hd_rd_rf[2] if len(hd_rd_rf) > 2 else "0-0")
                        pf_pa = grid.get((row_idx, 7), "").strip().split()
                        pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                        pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                        yr = grid.get((row_idx, 8), "").strip().split()
                        off_ypr = safe_float(yr[0]) if len(yr) > 0 else None
                        off_rsh = safe_float(yr[1]) if len(yr) > 1 else None
                        off_pss = safe_float(grid.get((row_idx, 9),  ""))
                        off_tot = safe_float(grid.get((row_idx, 10), ""))
                        def_tot = safe_float(grid.get((row_idx, 11), ""))
                        def_pss = safe_float(grid.get((row_idx, 12), ""))
                        def_rsh = safe_float(grid.get((row_idx, 13), ""))
                        def_ypr = safe_float(grid.get((row_idx, 14), ""))

            elif num_cols == 14:
                # DET/MIN or MIA — detect by col5 being PF PA (two integers)
                p = grid.get((row_idx, 1), "0-0 0-0").strip().split()
                su_w,  su_l,  _     = parse_record_3(p[0] if len(p) > 0 else "0-0")
                ats_w, ats_l, ats_p = parse_record_3(p[1] if len(p) > 1 else "0-0")
                d = grid.get((row_idx, 2), "0-0 0-0").strip().split()
                div_su_w,  div_su_l,  _ = parse_record_3(d[0] if len(d) > 0 else "0-0")
                div_ats_w, div_ats_l, _ = parse_record_3(d[1] if len(d) > 1 else "0-0")

                col5 = grid.get((row_idx, 5), "").strip()
                col5_parts = col5.split()
                col5_is_pf_pa = (len(col5_parts) == 2 and
                                 all(re.match(r'^\d+$', x) for x in col5_parts))

                if col5_is_pf_pa:
                    # DET/MIN layout: col5=PF PA, col6=off_ypr, col13=def_ypr
                    col3 = grid.get((row_idx, 3), "").strip()
                    col4 = grid.get((row_idx, 4), "").strip().split()
                    if not col3:
                        # DET: col3=empty, col4=all 4 splits
                        hf_w, hf_l, _ = parse_record_3(col4[0] if len(col4) > 0 else "0-0")
                        hd_w, hd_l, _ = parse_record_3(col4[1] if len(col4) > 1 else "0-0")
                        rd_w, rd_l, _ = parse_record_3(col4[2] if len(col4) > 2 else "0-0")
                        rf_w, rf_l, _ = parse_record_3(col4[3] if len(col4) > 3 else "0-0")
                    else:
                        # MIN: col3=HF, col4=HD+RD+RF
                        hf_w, hf_l, _ = parse_record_3(col3)
                        hd_w, hd_l, _ = parse_record_3(col4[0] if len(col4) > 0 else "0-0")
                        rd_w, rd_l, _ = parse_record_3(col4[1] if len(col4) > 1 else "0-0")
                        rf_w, rf_l, _ = parse_record_3(col4[2] if len(col4) > 2 else "0-0")
                    pf = safe_float(col5_parts[0])
                    pa = safe_float(col5_parts[1])
                    off_ypr = safe_float(grid.get((row_idx, 6),  ""))
                    off_rsh = safe_float(grid.get((row_idx, 7),  ""))
                    off_pss = safe_float(grid.get((row_idx, 8),  ""))
                    off_tot = safe_float(grid.get((row_idx, 9),  ""))
                    def_tot = safe_float(grid.get((row_idx, 10), ""))
                    def_pss = safe_float(grid.get((row_idx, 11), ""))
                    def_rsh = safe_float(grid.get((row_idx, 12), ""))
                    def_ypr = safe_float(grid.get((row_idx, 13), ""))
                else:
                    # MIA: col3=HF, col6=HD+RD+RF, col7=PF PA, col8=Ypr+Rsh, col13=Rsh+Ypr
                    hf_w, hf_l, _ = parse_record_3(grid.get((row_idx, 3), "0-0"))
                    hd_rd_rf = grid.get((row_idx, 6), "0-0 0-0 0-0").strip().split()
                    hd_w, hd_l, _ = parse_record_3(hd_rd_rf[0] if len(hd_rd_rf) > 0 else "0-0")
                    rd_w, rd_l, _ = parse_record_3(hd_rd_rf[1] if len(hd_rd_rf) > 1 else "0-0")
                    rf_w, rf_l, _ = parse_record_3(hd_rd_rf[2] if len(hd_rd_rf) > 2 else "0-0")
                    pf_pa = grid.get((row_idx, 7), "").strip().split()
                    pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                    pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                    yr_rsh = grid.get((row_idx, 8), "").strip().split()
                    off_ypr = safe_float(yr_rsh[0]) if len(yr_rsh) > 0 else None
                    off_rsh = safe_float(yr_rsh[1]) if len(yr_rsh) > 1 else None
                    off_pss = safe_float(grid.get((row_idx, 9),  ""))
                    off_tot = safe_float(grid.get((row_idx, 10), ""))
                    def_tot = safe_float(grid.get((row_idx, 11), ""))
                    def_pss = safe_float(grid.get((row_idx, 12), ""))
                    rsh_ypr = grid.get((row_idx, 13), "").strip().split()
                    def_rsh = safe_float(rsh_ypr[0]) if rsh_ypr else None
                    def_ypr = safe_float(rsh_ypr[1]) if len(rsh_ypr) > 1 else None

            elif num_cols == 13:
                # WAS or LAC — detect by col3
                p = grid.get((row_idx, 1), "0-0 0-0").strip().split()
                su_w,  su_l,  _     = parse_record_3(p[0] if len(p) > 0 else "0-0")
                ats_w, ats_l, ats_p = parse_record_3(p[1] if len(p) > 1 else "0-0")
                d = grid.get((row_idx, 2), "0-0 0-0").strip().split()
                div_su_w,  div_su_l,  _ = parse_record_3(d[0] if len(d) > 0 else "0-0")
                div_ats_w, div_ats_l, _ = parse_record_3(d[1] if len(d) > 1 else "0-0")

                col3 = grid.get((row_idx, 3), "").strip()
                col3_parts = col3.split()

                if len(col3_parts) >= 4:
                    # WAS: col3=all 4 splits merged, col4=PF PA, col5=off_ypr, col12=def_ypr
                    hf_w, hf_l, _ = parse_record_3(col3_parts[0])
                    hd_w, hd_l, _ = parse_record_3(col3_parts[1] if len(col3_parts) > 1 else "0-0")
                    rd_w, rd_l, _ = parse_record_3(col3_parts[2] if len(col3_parts) > 2 else "0-0")
                    rf_w, rf_l, _ = parse_record_3(col3_parts[3] if len(col3_parts) > 3 else "0-0")
                    pf_pa = grid.get((row_idx, 4), "").strip().split()
                    pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                    pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                    off_ypr = safe_float(grid.get((row_idx, 5),  ""))
                    off_rsh = safe_float(grid.get((row_idx, 6),  ""))
                    off_pss = safe_float(grid.get((row_idx, 7),  ""))
                    off_tot = safe_float(grid.get((row_idx, 8),  ""))
                    def_tot = safe_float(grid.get((row_idx, 9),  ""))
                    def_pss = safe_float(grid.get((row_idx, 10), ""))
                    def_rsh = safe_float(grid.get((row_idx, 11), ""))
                    def_ypr = safe_float(grid.get((row_idx, 12), ""))
                else:
                    # LAC: col3=empty, col4=all splits, col5=PF PA, col6=Ypr+Rsh merged
                    s = grid.get((row_idx, 4), "0-0 0-0 0-0 0-0").strip().split()
                    hf_w, hf_l, _ = parse_record_3(s[0] if len(s) > 0 else "0-0")
                    hd_w, hd_l, _ = parse_record_3(s[1] if len(s) > 1 else "0-0")
                    rd_w, rd_l, _ = parse_record_3(s[2] if len(s) > 2 else "0-0")
                    rf_w, rf_l, _ = parse_record_3(s[3] if len(s) > 3 else "0-0")
                    pf_pa = grid.get((row_idx, 5), "").strip().split()
                    pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                    pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                    yr = grid.get((row_idx, 6), "").strip().split()
                    off_ypr = safe_float(yr[0]) if len(yr) > 0 else None
                    off_rsh = safe_float(yr[1]) if len(yr) > 1 else None
                    off_pss = safe_float(grid.get((row_idx, 7),  ""))
                    off_tot = safe_float(grid.get((row_idx, 8),  ""))
                    def_tot = safe_float(grid.get((row_idx, 9),  ""))
                    def_pss = safe_float(grid.get((row_idx, 10), ""))
                    def_rsh = safe_float(grid.get((row_idx, 11), ""))
                    def_ypr = safe_float(grid.get((row_idx, 12), ""))

            elif num_cols == 12:
                # LAR — SU+ATS merged, DIV merged, all 4 splits merged
                p = grid.get((row_idx, 1), "0-0 0-0").strip().split()
                su_w,  su_l,  _     = parse_record_3(p[0] if len(p) > 0 else "0-0")
                ats_w, ats_l, ats_p = parse_record_3(p[1] if len(p) > 1 else "0-0")
                d = grid.get((row_idx, 2), "0-0 0-0").strip().split()
                div_su_w,  div_su_l,  _ = parse_record_3(d[0] if len(d) > 0 else "0-0")
                div_ats_w, div_ats_l, _ = parse_record_3(d[1] if len(d) > 1 else "0-0")
                s = grid.get((row_idx, 3), "0-0 0-0 0-0 0-0").strip().split()
                hf_w, hf_l, _ = parse_record_3(s[0] if len(s) > 0 else "0-0")
                hd_w, hd_l, _ = parse_record_3(s[1] if len(s) > 1 else "0-0")
                rd_w, rd_l, _ = parse_record_3(s[2] if len(s) > 2 else "0-0")
                rf_w, rf_l, _ = parse_record_3(s[3] if len(s) > 3 else "0-0")
                pf_pa = grid.get((row_idx, 4), "").strip().split()
                pf = safe_float(pf_pa[0]) if len(pf_pa) > 0 else None
                pa = safe_float(pf_pa[1]) if len(pf_pa) > 1 else None
                yr = grid.get((row_idx, 5), "").strip().split()
                off_ypr = safe_float(yr[0]) if len(yr) > 0 else None
                off_rsh = safe_float(yr[1]) if len(yr) > 1 else None
                off_pss = safe_float(grid.get((row_idx, 6), ""))
                off_tot = safe_float(grid.get((row_idx, 7), ""))
                def_tot = safe_float(grid.get((row_idx, 8), ""))
                def_pss = safe_float(grid.get((row_idx, 9), ""))
                def_rsh = safe_float(grid.get((row_idx, 10), ""))
                def_ypr = safe_float(grid.get((row_idx, 11), ""))

            else:
                print(f"  ✗ Unknown layout ({num_cols} cols) for {abbr} row {row_idx}")
                continue

            # ── Write to DB ───────────────────────────────────
            upsert_season_stat(db, str(team.id), year, {
                "su_wins"           : su_w,
                "su_losses"         : su_l,
                "ats_wins"          : ats_w,
                "ats_losses"        : ats_l,
                "ats_pushes"        : ats_p,
                "div_su_wins"       : div_su_w,
                "div_su_losses"     : div_su_l,
                "div_ats_wins"      : div_ats_w,
                "div_ats_losses"    : div_ats_l,
                "home_fav_ats_w"    : hf_w,
                "home_fav_ats_l"    : hf_l,
                "home_dog_ats_w"    : hd_w,
                "home_dog_ats_l"    : hd_l,
                "road_dog_ats_w"    : rd_w,
                "road_dog_ats_l"    : rd_l,
                "road_fav_ats_w"    : rf_w,
                "road_fav_ats_l"    : rf_l,
                "points_for_avg"    : pf,
                "points_against_avg": pa,
                "off_ypr"           : off_ypr,
                "off_rush_avg"      : off_rsh,
                "off_pass_avg"      : off_pss,
                "off_total_avg"     : off_tot,
                "def_total_avg"     : def_tot,
                "def_pass_avg"      : def_pss,
                "def_rush_avg"      : def_rsh,
                "def_ypr"           : def_ypr,
            })

        except Exception as e:
            print(f"  ✗ Error parsing year row {row_idx} for {abbr}: {e}")

    # ── Parse trends ──────────────────────────────────────────
    lines = []
    for page in result.pages:
        lines = [l.content.strip() for l in page.lines]
        break

    good_lines, bad_lines, ugly_lines, ou_lines = [], [], [], []
    current = None

    for line in lines:
        upper = line.upper()
        if "THE GOOD" in upper:
            current = "good"
            continue
        elif "THE BAD" in upper:
            current = "bad"
            continue
        elif "THE UGLY" in upper:
            current = "ugly"
            continue
        elif "OVER / UNDER" in upper or "OVER/UNDER" in upper:
            current = "ou"
            continue
        elif "2025 DRAFT PICKS" in upper:
            current = None
            continue

        if current == "good"   and line: good_lines.append(line)
        elif current == "bad"  and line: bad_lines.append(line)
        elif current == "ugly" and line: ugly_lines.append(line)
        elif current == "ou"   and line: ou_lines.append(line)

    if any([good_lines, bad_lines, ugly_lines, ou_lines]):
        upsert_trend(db, str(team.id), 2024, {
            "good_trends": "\n".join(good_lines),
            "bad_trends" : "\n".join(bad_lines),
            "ugly_trends": "\n".join(ugly_lines),
            "ou_trends"  : "\n".join(ou_lines),
        })

    return True




def seed_team_stats_from_pdf(db, teams: dict, test_abbr: str = None):
    """
    Parse all NFL team pages from the PDF.
    If test_abbr is provided, only parse that one team.
    """
    print("\n── Parsing team stats from PDF ──────────────────")

    team_abbrs = [test_abbr] if test_abbr else list(NFL_TEAM_PAGES.keys())
    success = 0
    errors  = []

    for abbr in team_abbrs:
        page_num = NFL_TEAM_PAGES.get(abbr)
        if not page_num:
            continue

        try:
            print(f"  Parsing {abbr} (page {page_num})...")
            result = analyze_pages(PDF_PATH, str(page_num))
            ok = parse_team_page(result, abbr, teams, db)
            if ok:
                print(f"  ✓ {abbr} done")
                success += 1
            else:
                errors.append(abbr)
        except Exception as e:
            print(f"  ✗ {abbr} failed: {e}")
            errors.append(abbr)

    print(f"\n  Parsed: {success} teams")
    if errors:
        print(f"  Failed: {errors}")

def parse_team_playbook(result, abbr: str, teams: dict, db) -> bool:
    import re
    from sqlalchemy import text

    team = teams.get(abbr)
    if not team:
        print(f"  ✗ Playbook team not found: {abbr}")
        return False

    lines = []
    for page in result.pages:
        lines = [l.content.strip() for l in page.lines]
        break

    # ── Extract sections ──────────────────────────────────────
    team_theme         = None
    win_total          = None
    win_total_odds     = None
    opp_win_total      = None
    playoff_yes_odds   = None
    playoff_no_odds    = None
    narrative_lines    = []
    stat_lines         = []
    power_play_lines   = []
    coaches_lines      = []
    q1_lines           = []
    q2_lines           = []
    q3_lines           = []
    q4_lines           = []
    division_lines     = []
    drop_cap = ''
    current = None
    in_narrative = False
    narrative_done = False

    for i, line in enumerate(lines):
        upper = line.upper()

        # ── Team Theme ────────────────────────────────────────
        if 'TEAM THEME:' in upper:
            m = re.search(r'TEAM THEME:\s*(.+)', line, re.IGNORECASE)
            if m:
                team_theme = m.group(1).strip()
            continue

        # ── Win Total ─────────────────────────────────────────
        if 'SEASON WIN TOTAL:' in upper:
            m = re.search(r'WIN TOTAL:\s*([\d.]+)\s*\(([^)]+)\)', line, re.IGNORECASE)
            if m:
                try:
                    win_total = float(m.group(1))
                    win_total_odds = m.group(2).strip()
                except:
                    pass
            continue

        # ── Opponents Win Total ───────────────────────────────
        if "OPPONENTS' COLLECTIVE" in upper or "OPPONENTS COLLECTIVE" in upper:
            m = re.search(r'([\d.]+)\s*$', line)
            if m:
                try:
                    opp_win_total = float(m.group(1))
                except:
                    pass
            continue

        # ── Playoff Odds ──────────────────────────────────────
        if 'ODDS TO MAKE' in upper and 'PLAYOFFS' in upper:
            yes_m = re.search(r'YES\s*([+-]\d+)', line, re.IGNORECASE)
            no_m  = re.search(r'NO\s*([+-]\d+)',  line, re.IGNORECASE)
            if yes_m: playoff_yes_odds = yes_m.group(1)
            if no_m:  playoff_no_odds  = no_m.group(1)
            continue

        # ── Section headers ───────────────────────────────────
        if 'COACHES CORNER' in upper:
            current = 'coaches'
            in_narrative = False
            continue
        elif '1ST QTR' in upper or 'GAMES 1-4' in upper:
            current = 'q1'
            continue
        elif '2ND QTR' in upper or 'GAMES 5-8' in upper:
            current = 'q2'
            continue
        elif '3RD QTR' in upper or 'GAMES 9-12' in upper:
            current = 'q3'
            continue
        elif '4TH QTR' in upper or 'GAMES 13-17' in upper:
            current = 'q4'
            continue
        elif 'DIVISION DATA' in upper:
            current = 'division'
            continue
        elif 'QUARTERLY REPORT' in upper:
            current = None
            continue
        elif 'STAT YOU WILL LIKE' in upper:
            current = 'stat'
            in_narrative = False
            continue
        elif 'POINTSPREAD POWER PLAY' in upper:
            current = 'power'
            in_narrative = False
            continue
        elif '10 YEAR ATS HISTORY' in upper:
            current = None
            in_narrative = False
            continue
        elif 'CAREER HISTORY' in upper:
            continue
        elif '2025' in line and 'PLAYBOOK' in upper:
            # Start of narrative section on right side
            in_narrative = True
            current = None
            continue

        # Skip empty lines for trend sections
        if not line:
            if in_narrative and narrative_lines:
                narrative_lines.append('')
            continue

        # ── Assign to sections ────────────────────────────────
        if current == 'coaches' and line:
            coaches_lines.append(line)
        elif current == 'q1' and line:
            q1_lines.append(line)
        elif current == 'q2' and line:
            q2_lines.append(line)
        elif current == 'q3' and line:
            q3_lines.append(line)
        elif current == 'q4' and line:
            q4_lines.append(line)
        elif current == 'division' and line:
            division_lines.append(line)
        elif current == 'stat' and line:
            stat_lines.append(line)
        elif current == 'power' and line:
            power_play_lines.append(line)
        elif in_narrative and not narrative_done and line:
            print(f"  NARRATIVE LINE: {line[:50]}")  # DEBUG
            if len(line) == 1:
                drop_cap = line
                continue
            if drop_cap:
                line = drop_cap + line
                drop_cap = ''
            narrative_lines.append(line)

    # ── Upsert to DB ──────────────────────────────────────────
    db.execute(text("""
        INSERT INTO team_playbook
            (id, team_id, season_year, team_theme, win_total, win_total_odds,
             opp_win_total, playoff_yes_odds, playoff_no_odds, narrative,
             stat_you_will_like, power_play, coaches_corner,
             q1_trends, q2_trends, q3_trends, q4_trends, division_data)
        VALUES
            (gen_random_uuid(), :tid, :year, :theme, :wt, :wto,
             :owt, :pyo, :pno, :narr,
             :stat, :pp, :cc,
             :q1, :q2, :q3, :q4, :div)
        ON CONFLICT (team_id, season_year)
        DO UPDATE SET
            team_theme=EXCLUDED.team_theme,
            win_total=EXCLUDED.win_total,
            win_total_odds=EXCLUDED.win_total_odds,
            opp_win_total=EXCLUDED.opp_win_total,
            playoff_yes_odds=EXCLUDED.playoff_yes_odds,
            playoff_no_odds=EXCLUDED.playoff_no_odds,
            narrative=EXCLUDED.narrative,
            stat_you_will_like=EXCLUDED.stat_you_will_like,
            power_play=EXCLUDED.power_play,
            coaches_corner=EXCLUDED.coaches_corner,
            q1_trends=EXCLUDED.q1_trends,
            q2_trends=EXCLUDED.q2_trends,
            q3_trends=EXCLUDED.q3_trends,
            q4_trends=EXCLUDED.q4_trends,
            division_data=EXCLUDED.division_data,
            updated_at=NOW()
    """), {
        'tid' : str(team.id),
        'year': 2025,
        'theme': team_theme,
        'wt'  : win_total,
        'wto' : win_total_odds,
        'owt' : opp_win_total,
        'pyo' : playoff_yes_odds,
        'pno' : playoff_no_odds,
        'narr': '\n'.join(narrative_lines).strip() or None,
        'stat': '\n'.join(stat_lines).strip() or None,
        'pp'  : '\n'.join(power_play_lines).strip() or None,
        'cc'  : '\n'.join(coaches_lines).strip() or None,
        'q1'  : '\n'.join(q1_lines).strip() or None,
        'q2'  : '\n'.join(q2_lines).strip() or None,
        'q3'  : '\n'.join(q3_lines).strip() or None,
        'q4'  : '\n'.join(q4_lines).strip() or None,
        'div' : '\n'.join(division_lines).strip() or None,
    })
    db.commit()
    print(f"  ✓ Playbook parsed for {abbr}")
    return True


def parse_cfb_gamelogs(result, name: str, teams: dict, db, season_year=2024) -> int:
    import re
    from sqlalchemy import text

    team = teams.get(name)
    if not team:
        print(f"  ✗ CFB team not found: {name}")
        return 0

    # Find the stat logs table — identified by having OYP/OFR columns
    stat_table = None
    for table in result.tables:
        for cell in table.cells:
            if cell.row_index == 0 and 'OYP' in cell.content.upper():
                stat_table = table
                break
        if stat_table:
            break

    if not stat_table:
        print(f"  ✗ Stat logs table not found for {name}")
        return 0

    # Build grid
    grid = {}
    for cell in stat_table.cells:
        grid[(cell.row_index, cell.column_index)] = cell.content.strip()

    def g(row, col, default=None):
        v = grid.get((row, col), '')
        v = re.sub(r':selected:|:unselected:', '', v).strip()
        return v if v else default

    def safe_float(v):
        if not v: return None
        try: return float(v)
        except: return None

    def safe_int(v):
        if not v: return None
        try: return int(float(v))
        except: return None

    # Column mapping from Table 2:
    # 0=check, 1=OPPONENT, 2=DATE, 3=OWL, 4=PF, 5=PA, 6=SU,
    # 7=LINE, 8=ATS, 9=O/U, 10=OYP, 11=OFR, 12=OFP, 13=OYD,
    # 14=DYD, 15=DFP, 16=DFR, 17=DYP, 18=RES, 19=F-A

    game_num = 0
    saved    = 0

    for row_idx in range(1, stat_table.row_count):
        opp_raw   = g(row_idx, 1)
        game_date = g(row_idx, 2)

        if not opp_raw or not game_date:
            continue
        if opp_raw.upper() in ('OPPONENT', 'DATE', 'OWL'):
            continue

        # Home/away from col 0 (check mark or 'at')
        col0      = g(row_idx, 0, '')
        is_home   = 'at' not in col0.lower() and not opp_raw.lower().startswith('at ')
        opp       = re.sub(r'^at\s+', '', opp_raw, flags=re.IGNORECASE).strip()
        opp       = re.sub(r'[\s•·\*\.]+$', '', opp).strip()

        opp_record = g(row_idx, 3)
        pf         = safe_int(g(row_idx, 4))
        pa         = safe_int(g(row_idx, 5))
        su_result  = g(row_idx, 6)
        line_val   = safe_float(g(row_idx, 7))
        ats_result = g(row_idx, 8)
        ou_raw     = g(row_idx, 9)

        ou_result  = None
        ou_line    = None
        if ou_raw:
            ou_m = re.match(r'([OUou])(\d+\.?\d*)', ou_raw)
            if ou_m:
                ou_result = ou_m.group(1).upper()
                ou_line   = safe_float(ou_m.group(2))

        off_ypr   = safe_float(g(row_idx, 10))
        off_rush  = safe_int(g(row_idx, 11))
        off_pass  = safe_int(g(row_idx, 12))
        off_total = safe_int(g(row_idx, 13))
        def_total = safe_int(g(row_idx, 14))
        def_pass  = safe_int(g(row_idx, 15))
        def_rush  = safe_int(g(row_idx, 16))
        def_ypr   = safe_float(g(row_idx, 17))
        res_score = g(row_idx, 18)
        first_dwn = g(row_idx, 19)

        if su_result not in ('W', 'L', 'T'):
            su_result = None
        if ats_result not in ('W', 'L', 'P'):
            ats_result = None

        game_num += 1

        db.execute(text("""
            INSERT INTO game_logs
                (id, team_id, season_year, game_num, opponent, game_date,
                 is_home, opp_record, points_for, points_against,
                 su_result, line, ats_result, ou_result, ou_line,
                 off_ypr, off_rush, off_pass, off_total,
                 def_total, def_pass, def_rush, def_ypr,
                 result_score, first_downs)
            VALUES
                (gen_random_uuid(), :tid, :year, :gnum, :opp, :gdate,
                 :is_home, :rec, :pf, :pa,
                 :su, :line, :ats, :ou, :oul,
                 :oyp, :ofr, :ofp, :oyd,
                 :dyd, :dfp, :dfr, :dyp,
                 :res, :fa)
            ON CONFLICT (team_id, season_year, game_num)
            DO UPDATE SET
                opponent=EXCLUDED.opponent,
                opp_record=EXCLUDED.opp_record,
                points_for=EXCLUDED.points_for,
                points_against=EXCLUDED.points_against,
                su_result=EXCLUDED.su_result,
                line=EXCLUDED.line,
                ats_result=EXCLUDED.ats_result,
                ou_result=EXCLUDED.ou_result,
                ou_line=EXCLUDED.ou_line,
                off_ypr=EXCLUDED.off_ypr,
                off_rush=EXCLUDED.off_rush,
                off_pass=EXCLUDED.off_pass,
                off_total=EXCLUDED.off_total,
                def_total=EXCLUDED.def_total,
                def_pass=EXCLUDED.def_pass,
                def_rush=EXCLUDED.def_rush,
                def_ypr=EXCLUDED.def_ypr,
                result_score=EXCLUDED.result_score,
                first_downs=EXCLUDED.first_downs,
                updated_at=NOW()
        """), {
            'tid': str(team.id), 'year': season_year, 'gnum': game_num,
            'opp': opp,         'gdate': game_date,   'is_home': is_home,
            'rec': opp_record,  'pf': pf,             'pa': pa,
            'su': su_result,    'line': line_val,      'ats': ats_result,
            'ou': ou_result,    'oul': ou_line,
            'oyp': off_ypr,     'ofr': off_rush,       'ofp': off_pass,
            'oyd': off_total,   'dyd': def_total,
            'dfp': def_pass,    'dfr': def_rush,       'dyp': def_ypr,
            'res': res_score,   'fa': first_dwn,
        })
        saved += 1

    db.commit()
    return saved



def parse_cfb_schedule(result, name: str, teams: dict, db, season_year=2025) -> int:
    import re
    from sqlalchemy import text

    team = teams.get(name)
    if not team:
        print(f"  ✗ CFB team not found: {name}")
        return 0

    lines = []
    for page in result.pages:
        lines = [l.content.strip() for l in page.lines]
        break

    # Find schedule section
    start_idx = None
    end_idx   = None
    for i, line in enumerate(lines):
        if 'SCHEDULE LOG' in line.upper() and start_idx is None:
            start_idx = i + 1
        if start_idx and ('FINAL 2024' in line.upper() or 'STAT LOGS' in line.upper()):
            end_idx = i
            break

    if not start_idx:
        print(f"  ✗ Schedule not found for {name}")
        return 0

    sched_lines = lines[start_idx:end_idx] if end_idx else lines[start_idx:start_idx+50]

    # Filter out header lines
    skip = {'OPPONENT', 'DATE', 'OWL', 'PTF - PTA', 'SU', 'LINE', 'ATS', 'O/U',
            'ATS SCORECARD', 'PTF', 'PTA'}
    filtered = []
    for line in sched_lines:
        if not line:
            continue
        if line.upper() in skip:
            continue
        if 'SCHEDULE' in line.upper() or 'PLAYBOOK' in line.upper():
            continue
        if 'TEAM THEME' in line.upper():
            continue
        filtered.append(line)

    # Parse in groups — opponent, date, OWL, (optional scorecard)
    game_num = 0
    saved    = 0
    i        = 0

    while i < len(filtered):
        line = filtered[i]

        # Is this line a date?
        date_match = re.match(r'^(\d{1,2}/\d{1,2})$', line.strip())
        # Is this line an OWL record?
        owl_match  = re.match(r'^(\d{1,2}-\d{1,2})$', line.strip())
        # Is this an ATS scorecard?
        scorecard_match = re.search(r'\d+-\d+\s+L\d+|^\^\d+', line.strip())

        if date_match or owl_match or scorecard_match:
            i += 1
            continue

        # This must be an opponent line
        opp_raw = line.strip()

        # Look ahead for date and OWL
        game_date  = None
        opp_record = None
        ats_sc     = None
        j          = i + 1

        while j < len(filtered) and j < i + 4:
            next_line = filtered[j].strip()
            if re.match(r'^\d{1,2}/\d{1,2}$', next_line) and not game_date:
                game_date = next_line
            elif re.match(r'^\d{1,2}-\d{1,2}$', next_line) and not opp_record:
                opp_record = next_line
            elif re.search(r'\d+-\d+\s+L\d+|^\^', next_line) and not ats_sc:
                ats_sc = next_line
            else:
                break
            j += 1

        if not game_date:
            i += 1
            continue

        # Parse home/away
        is_home = not opp_raw.lower().startswith('at ')
        opp = re.sub(r'^at\s+', '', opp_raw, flags=re.IGNORECASE).strip()
        opp = re.sub(r'[\s•·\*\.]+$', '', opp).strip()

        if not opp:
            i += 1
            continue

        game_num += 1

        db.execute(text("""
            INSERT INTO schedule_games
                (id, team_id, season_year, game_num, opponent, game_date,
                 is_home, opp_record, ats_scorecard)
            VALUES
                (gen_random_uuid(), :tid, :year, :gnum, :opp, :gdate,
                 :is_home, :rec, :sc)
            ON CONFLICT (team_id, season_year, game_num)
            DO UPDATE SET
                opponent=EXCLUDED.opponent,
                opp_record=EXCLUDED.opp_record,
                is_home=EXCLUDED.is_home,
                ats_scorecard=EXCLUDED.ats_scorecard,
                updated_at=NOW()
        """), {
            'tid'    : str(team.id),
            'year'   : season_year,
            'gnum'   : game_num,
            'opp'    : opp,
            'gdate'  : game_date,
            'is_home': is_home,
            'rec'    : opp_record,
            'sc'     : ats_sc,
        })
        saved += 1
        i = j  # skip ahead past the lines we consumed

    db.commit()
    return saved


def parse_cfb_coach(result, name: str, teams: dict, db) -> bool:
    import re
    from sqlalchemy import text

    team = teams.get(name)
    if not team:
        return False

    lines = []
    for page in result.pages:
        lines = [l.content.strip() for l in page.lines]
        break

    # Search all lines for specific patterns
    coach_name    = None
    years         = None
    su_w = su_l   = None
    ats_w = ats_l = ats_p = None
    rpr           = None
    rpr_off       = None
    rpr_def       = None
    ret_off       = None
    ret_def       = None
    recruit_rank_2025 = None

    year_words = {
        'first':1,'second':2,'third':3,'fourth':4,'fifth':5,
        'sixth':6,'seventh':7,'eighth':8,'ninth':9,'tenth':10,
        'eleventh':11,'twelfth':12,'thirteenth':13,'fourteenth':14,
        'fifteenth':15,'sixteenth':16,'seventeenth':17,'eighteenth':18,
        'nineteenth':19,'twentieth':20,'twenty-first':21,'twenty-second':22,
    }

    # Known non-coach uppercase lines to skip
    skip_names = {name.upper(), 'CRIMSON TIDE', 'BULLDOGS', 'BUCKEYES',
                  'FALCONS', 'VOLUNTEERS', 'GATORS', 'HURRICANES', 'TIGERS',
                  'AGGIES', 'LONGHORNS', 'SOONERS', 'WOLVERINES', 'NITTANY LIONS',
                  'SEMINOLES', 'HURRICANES', 'CRIMSON', 'TIDE', '4 YEAR STATISTICAL REVIEW',
                  'RET STARTERS', 'SOUTHEASTERN CONFERENCE', 'BIG TEN', 'ACC', 'BIG 12',
                  'PAC-12', 'BIG EAST', 'MOUNTAIN WEST', 'SUN BELT', 'MAC', 'CUSA',
                  'AMERICAN ATHLETIC', 'INDEPENDENT'}

    for line in lines[:25]:
        if line:
            print(f"  LINE: {repr(line)}")
        if not line:
            continue

        # Skip known non-coach lines
        if line.upper() in skip_names:
            continue

        # RPR line — check first to avoid misidentifying as coach name
        rpr_m = re.match(r'^RPR:\s*(\d+)$', line, re.IGNORECASE)
        if rpr_m:
            rpr = int(rpr_m.group(1))
            continue

        # RPR breakdown
        rpr_d = re.search(r'Off:\s*(\d+)\s*[•·\.\,]\s*Def:\s*(\d+)', line, re.IGNORECASE)
        if rpr_d:
            rpr_off = int(rpr_d.group(1))
            rpr_def = int(rpr_d.group(2))
            continue

        # Record line — "9-4 SU . 6-6 ATS"
        rec_m = re.search(r'(\d+)-(\d+)\s+SU\s*[•·\.\,]\s*(\d+)-(\d+)(?:-(\d+))?\s+ATS', line, re.IGNORECASE)
        if rec_m:
            su_w  = int(rec_m.group(1))
            su_l  = int(rec_m.group(2))
            ats_w = int(rec_m.group(3))
            ats_l = int(rec_m.group(4))
            ats_p = int(rec_m.group(5)) if rec_m.group(5) else 0
            continue

        # Year line — must be exactly "Word Year" with no digits
        year_m = re.match(r'^(\w[\w\-]*)\s+[Yy]ear$', line.strip())
        if year_m and not any(c.isdigit() for c in line):
            word = year_m.group(1).lower()
            if word in year_words:
                years = year_words[word]
            else:
                ord_m = re.match(r'(\d+)', word)
                if ord_m:
                    years = int(ord_m.group(1))
            continue

        # Recruit rank — parse 2025 value
        recruit_m = re.search(r'recruit rank:\s*(\d+)', line, re.IGNORECASE)
        if recruit_m:
            recruit_rank_2025 = int(recruit_m.group(1))
            continue

        # Stadium line — skip
        if 'stadium' in line.lower() or 'capacity' in line.lower():
            continue

        # Website — skip
        if 'www.' in line.lower():
            continue

        # OFF/DEF returning starters — parse
        off_def_m = re.match(r'^(\d+)\s+OFF\s*/\s*(\d+)\s+DEF$', line, re.IGNORECASE)
        if off_def_m:
            ret_off = int(off_def_m.group(1))
            ret_def = int(off_def_m.group(2))
            continue
        if '7' in line and 'OFF' in line:
            print(f"  TESTING OFF/DEF: {repr(line)}, match={re.match(r'^(\\d+)\\s+OFF\\s*/\\s*(\\d+)\\s+DEF$', line, re.IGNORECASE)}")

         # DEBUG
        if 'OFF' in line.upper() and 'DEF' in line.upper():
            print(f"  OFF/DEF line: {repr(line)}")

        # Pure number — skip
        if re.match(r'^\d+$', line):
            continue

        # Coach name — all caps, 2+ words, no digits, not in skip list
        if (re.match(r'^[A-Z][A-Z\s\'\-\.]+$', line) and
            len(line.split()) >= 2 and
            not any(c.isdigit() for c in line) and
            line.upper() not in skip_names and
            coach_name is None):
            coach_name = line.strip()

    if not coach_name:
        print(f"  ✗ Coach not found for {name}")
        return False

    db.execute(text("""
        INSERT INTO coaches
            (id, team_id, name, years_with_team,
             record_su_wins, record_su_losses,
             record_ats_wins, record_ats_losses, record_ats_pushes,
             rpr, rpr_off, rpr_def,
             ret_off_starters, ret_def_starters,
             recruit_rank_2025)
        VALUES
            (gen_random_uuid(), :tid, :name, :yrs,
             :suw, :sul, :atsw, :atsl, :atsp,
             :rpr, :rpro, :rprd,
             :retoff, :retdef,
             :rrk)
        ON CONFLICT (team_id)
        DO UPDATE SET
            name=EXCLUDED.name,
            years_with_team=EXCLUDED.years_with_team,
            record_su_wins=EXCLUDED.record_su_wins,
            record_su_losses=EXCLUDED.record_su_losses,
            record_ats_wins=EXCLUDED.record_ats_wins,
            record_ats_losses=EXCLUDED.record_ats_losses,
            record_ats_pushes=EXCLUDED.record_ats_pushes,
            rpr=EXCLUDED.rpr,
            rpr_off=EXCLUDED.rpr_off,
            rpr_def=EXCLUDED.rpr_def,
            ret_off_starters=EXCLUDED.ret_off_starters,
            ret_def_starters=EXCLUDED.ret_def_starters,
            recruit_rank_2025=EXCLUDED.recruit_rank_2025,
            updated_at=NOW()
    """), {
        'tid'   : str(team.id),
        'name'  : coach_name,
        'yrs'   : years or 1,
        'suw'   : su_w or 0,
        'sul'   : su_l or 0,
        'atsw'  : ats_w,
        'atsl'  : ats_l,
        'atsp'  : ats_p,
        'rpr'   : rpr,
        'rpro'  : rpr_off,
        'rprd'  : rpr_def,
        'retoff': ret_off,
        'retdef': ret_def,
        'rrk'   : recruit_rank_2025,
    })
    db.commit()
    print(f"  ✓ Coach: {coach_name} ({years} yrs) SU:{su_w}-{su_l} RPR:{rpr} RRK:{recruit_rank_2025}")
    return True

def parse_cfb_playbook(result, name: str, teams: dict, db) -> bool:
    import re
    from sqlalchemy import text

    team = teams.get(name)
    if not team:
        print(f"  ✗ CFB team not found: {name}")
        return False

    # ── Separate left and right column lines using x position ──
    RIGHT_X_THRESHOLD = 4.0

    right_lines = []
    for page in result.pages:
        for line in page.lines:
            if not line.content.strip():
                continue
            x = min(pt.x for pt in line.polygon)
            if x >= RIGHT_X_THRESHOLD:
                right_lines.append(line.content.strip())
        break

    team_theme       = None
    narrative_lines  = []
    stat_lines       = []
    power_play_lines = []
    good_lines       = []
    bad_lines        = []
    ugly_lines       = []
    drop_cap         = ''
    current          = None

    for line in right_lines:
        upper = line.upper().strip()

        if not line.strip():
            continue

        # Stop at 10 year ATS history
        if '10 YEAR ATS' in upper:
            break

        # Team Theme
        if 'TEAM THEME:' in upper:
            m = re.search(r'TEAM THEME:\s*(.+)', line, re.IGNORECASE)
            if m:
                team_theme = m.group(1).strip()
            current = 'narrative'
            continue

        # Section headers
        if 'MARC LAWRENCE' in upper or 'TEAM TRENDS' in upper:
            current = None
            continue
        if upper == 'THE GOOD':
            current = 'good'
            continue
        if upper == 'THE BAD':
            current = 'bad'
            continue
        if upper == 'THE UGLY':
            current = 'ugly'
            continue
        if 'STAT YOU WILL LIKE' in upper:
            current = 'stat'
            continue
        if 'POINTSPREAD POWER PLAY' in upper:
            current = 'power'
            continue

        # Skip coach/header info lines
        skip_patterns = [
            r'^\d+-\d+\s+SU',           # SU record
            r'recruit rank',             # recruit rank
            r'^\d+\s+OFF\s*/',          # returning starters
            r'^RPR:',                    # RPR
            r'^\(Off:',                  # RPR breakdown
            r'^www\.',                   # website
            r'^\d+\s+year$',            # year
            r'^second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth', # year words
        ]
        if any(re.search(p, line, re.IGNORECASE) for p in skip_patterns):
            continue

        # Skip stats table headers
        skip_upper_exact = {
            'OFFENSIVE YD AVG', 'DEFENSIVE YD AVG', 'RECRUITING HISTORY',
            'YPR', 'RSH PSS', 'TOT', 'RK 5* 4*', '3* TOT',
            'WIN-LOSS SU ATS', 'CONF W-L SU ATS', 'AGAINST THE SPR',
        }
        if upper in skip_upper_exact:
            continue

        # Drop cap — single uppercase letter starts narrative
        if len(line.strip()) == 1 and line.strip().isupper() and current == 'narrative':
            drop_cap = line.strip()
            continue

        # ── Assign to sections ────────────────────────────────
        if current == 'narrative':
            if drop_cap:
                line     = drop_cap + line.strip()
                drop_cap = ''
            # Only add lines that look like prose (have lowercase)
            # or reasonable narrative content
            if any(c.islower() for c in line) and len(line.strip()) > 5:
                narrative_lines.append(line.strip())

        elif current == 'stat':
            if line.strip() and 'STAT YOU WILL LIKE' not in upper:
                stat_lines.append(line.strip())

        elif current == 'power':
            if line.strip() and 'POINTSPREAD POWER PLAY' not in upper:
                # Stop at NOTES
                if 'NOTES' in upper:
                    current = None
                    continue
                power_play_lines.append(line.strip())

        elif current == 'good':
            if line.strip() and 'THE GOOD' not in upper:
                good_lines.append(line.strip())

        elif current == 'bad':
            if line.strip() and 'THE BAD' not in upper:
                bad_lines.append(line.strip())

        elif current == 'ugly':
            if line.strip() and 'THE UGLY' not in upper:
                if re.match(r'^\d{4}\s*[–-]', line):
                    break
                if upper in ('LINE ATS', 'SCORE SU LINE ATS', 'OPPONENT'):
                    break
                ugly_lines.append(line.strip())

    # ── Upsert team_playbook ──────────────────────────────────
    if team_theme or narrative_lines or stat_lines:
        db.execute(text("""
            INSERT INTO team_playbook
                (id, team_id, season_year, team_theme, narrative,
                 stat_you_will_like, power_play)
            VALUES
                (gen_random_uuid(), :tid, 2025, :theme, :narr, :stat, :pp)
            ON CONFLICT (team_id, season_year)
            DO UPDATE SET
                team_theme=EXCLUDED.team_theme,
                narrative=EXCLUDED.narrative,
                stat_you_will_like=EXCLUDED.stat_you_will_like,
                power_play=EXCLUDED.power_play,
                updated_at=NOW()
        """), {
            'tid'  : str(team.id),
            'theme': team_theme,
            'narr' : '\n'.join(narrative_lines).strip() or None,
            'stat' : '\n'.join(stat_lines).strip() or None,
            'pp'   : '\n'.join(power_play_lines).strip() or None,
        })

    # ── Upsert team_trends ────────────────────────────────────
    if good_lines or bad_lines or ugly_lines:
        from app.repositories.stats_repo import upsert_trend
        upsert_trend(db, str(team.id), 2024, {
            'good_trends': '\n'.join(good_lines).strip() or None,
            'bad_trends' : '\n'.join(bad_lines).strip() or None,
            'ugly_trends': '\n'.join(ugly_lines).strip() or None,
            'ou_trends'  : None,
        })

    db.commit()
    print(f"  ✓ CFB Playbook: {name} theme={team_theme} narr={len(narrative_lines)} good={len(good_lines)} bad={len(bad_lines)} ugly={len(ugly_lines)}")
    return True


def parse_ats_history(result, abbr: str, teams: dict, db) -> int:
    """
    Parse 10-year ATS history from NFL team second page using Azure DI tables.
    Handles all varying column structures across all 32 NFL teams.
    
    Key observations from analysis:
    - Each year = one Azure DI table (10 tables total)
    - Year/coach in rows 0-1 (sometimes split across cells)
    - Last year (2024) often has no year header, data starts at row 0
    - Column structures vary: 5-9 cols, ATS/O/U combined or separate
    - Score sometimes split across 2 cells
    - Opponent sometimes split: 'at' prefix in separate cell
    - LINE sometimes split: sign in one cell, number in next
    
    Strategy: For each row, find the SCORE cell (NN-NN pattern),
    then derive everything relative to it.
    """
    import re
    from sqlalchemy import text

    team = teams.get(abbr)
    if not team:
        print(f"  ✗ Team not found: {abbr}")
        return 0

    # ── Find ATS history tables ───────────────────────────────
    ats_tables = []
    years_found = []

    for table in result.tables:
        if table.row_count < 5:
            continue
        grid = get_table_grid(table)

        # Find year from all cells
        yr = None
        coach = ''
        all_text = re.sub(r'[\*†\n]', ' ', ' '.join([
            grid.get((r, c), '')
            for r in range(min(3, table.row_count))
            for c in range(table.column_count)
        ]))
        
        yr_m = re.search(r'(20\d\d)', all_text)
        if yr_m:
            yr = int(yr_m.group(1))
            # Try to get coach — text after dash following year, before header words
            after_yr = all_text[yr_m.end():]
            dash_m = re.search(r'[-–]\s*([A-Z][A-Z\s]+?)(?=OPPONENT|SCORE|SU|LINE|ATS|\d{2,}|$)', after_yr)
            if dash_m:
                raw = dash_m.group(1).strip()
                coach = ' '.join(w for w in raw.split() 
                                 if w not in ('OPPONENT','SCORE','SU','LINE','ATS','O/U') 
                                 and w.isalpha()).strip()
        # If no year found, check if table has valid game headers (it's a missing year)
        if not yr:
            header_text = all_text.upper()
            if 'OPPONENT' in header_text and 'SCORE' in header_text and 'LINE' in header_text:
                yr = (years_found[-1] + 1) if years_found else None

        # Find data start row (first row with score pattern)
        data_start = 2
        for r in range(table.row_count):
            row_text = ' '.join([grid.get((r, c), '') for c in range(table.column_count)])
            if re.search(r'\d+\s*[-–]\s*\d+', row_text) and re.search(r'[WLT]\s', row_text):
                data_start = r
                break

        # If no year found and data at row 0 — last year table (2024)
        if not yr and data_start == 0:
            yr = (years_found[-1] + 1) if years_found else 2024

        if yr:
            ats_tables.append((table, grid, yr, coach, data_start))
            years_found.append(yr)

    if not ats_tables:
        print(f"  ✗ No ATS history tables found for {abbr}")
        return 0

    # ── Parse each table ─────────────────────────────────────
    saved = 0
    SCORE_PAT = re.compile(r'^(\d+)\s*[-–]\s*(\d+)')
    ATS_OU_PAT = re.compile(r'^([WLTwlt])\s+([OUou0Pp])(\d+\.?\d*)?')
    OU_ONLY_PAT = re.compile(r'^([OUou0])(\d+\.?\d*)')

    def clean(s):
        return re.sub(r"['\*†]", '', s or '').strip()

    def parse_row(cells, col_count):
        """
        Parse a single game row using score-relative positioning.
        Strategy: find score cell, derive all other values from it.
        """
        cells = [clean(c) for c in cells]

        # Step 1: Find score cell (or combine adjacent cells to form score)
        score_col = None
        pf = pa = None

        for c in range(col_count):
            m = SCORE_PAT.match(cells[c].replace(' ', ''))
            if m:
                score_col = c
                pf = int(m.group(1))
                pa = int(m.group(2))
                break

        # Try combining adjacent cells for split score like "13 -" + "20"
        if score_col is None:
            for c in range(col_count - 1):
                combined = cells[c] + cells[c+1]
                m = SCORE_PAT.match(combined.replace(' ', ''))
                if m:
                    cells[c] = combined
                    cells.pop(c+1)
                    score_col = c
                    pf = int(m.group(1))
                    pa = int(m.group(2))
                    break

        if score_col is None or pf is None:
            return None

        # Step 2: Opponent = everything before score (non-empty cells)
        opp_parts = [cells[c] for c in range(score_col) if cells[c]]
        opp_raw   = ' '.join(opp_parts).strip()

        # Step 3: After score = SU, LINE parts, ATS, O/U
        # Collect non-empty cells after score
        after = [cells[c] for c in range(score_col + 1, len(cells)) if cells[c]]

        if not after:
            return None

        # Clean game type markers from score cell (like "13-25 B" or "17-15M")
        score_clean = cells[score_col]
        score_clean = re.sub(r'\s*[BMSTNbmstn]+$', '', score_clean).strip()

        # Step 4: Parse SU — first cell after score that is W/L/T
        su = None
        su_idx = 0
        for i, val in enumerate(after):
            # SU might have game type prefix like "B W" or "M W"
            val_clean = re.sub(r'^[BMSTNbmstn]+\s*', '', val).strip()
            if val_clean[:1].upper() in ('W', 'L', 'T'):
                su = val_clean[:1].upper()
                su_idx = i
                break

        after_su = after[su_idx + 1:]

        # Step 5: Parse LINE — collect sign + number
        line_float = None
        line_idx   = 0
        for i, val in enumerate(after_su):
            # Line can be: "-7", "+3", "Pk", "pk", sign only "-", number only "7.5"
            val_clean = val.replace(' ', '')
            if val_clean.lower() in ('pk', 'pick', 'p'):
                line_float = 0.0
                line_idx   = i
                break
            m = re.match(r'^([+\-])(\d+\.?\d*)$', val_clean)
            if m:
                try:
                    line_float = float(m.group(1) + m.group(2))
                    line_idx   = i
                    break
                except:
                    pass
            # Sign only (like "-" or "+")
            if val_clean in ('+', '-') and i + 1 < len(after_su):
                next_val = after_su[i+1].replace(' ', '')
                if re.match(r'^\d+\.?\d*$', next_val):
                    try:
                        line_float = float(val_clean + next_val)
                        # Consume both cells
                        after_su = after_su[:i] + [val_clean + next_val] + after_su[i+2:]
                        line_idx = i
                        break
                    except:
                        pass
            # Number with spaces around decimal like "+ 6 .5" or "+ 4 .5"
            if val_clean in ('+', '-'):
                continue
            # Pure number (line without sign, treat as negative for favorites)
            if re.match(r'^\d+\.?\d*$', val_clean) and i == 0:
                try:
                    line_float = -float(val_clean)
                    line_idx   = i
                    break
                except:
                    pass

        after_line = after_su[line_idx + 1:]

        # Step 6: Parse ATS and O/U from remaining cells
        ats    = None
        ou     = None
        ou_line = None

        for val in after_line:
            val_clean = clean(val)
            if not val_clean:
                continue

            # Check for combined ATS O/U: "W O44", "L U45", "T P47"
            m = ATS_OU_PAT.match(val_clean)
            if m:
                if ats is None:
                    ats = m.group(1).upper()
                if ou is None:
                    ou_char = m.group(2).upper()
                    if ou_char == '0':
                        ou_char = 'O'
                    ou = ou_char
                    try:
                        ou_line = float(m.group(3)) if m.group(3) else None
                    except:
                        ou_line = None
                continue

            # ATS only: W, L, T, P
            if val_clean.upper() in ('W', 'L', 'T', 'P') and ats is None:
                ats = val_clean.upper()
                continue

            # O/U only: O44, U45, P47
            m2 = OU_ONLY_PAT.match(val_clean)
            if m2 and ou is None:
                ou_char = m2.group(1).upper()
                if ou_char == '0':
                    ou_char = 'O'
                ou = ou_char
                try:
                    ou_line = float(m2.group(2)) if m2.group(2) else None
                except:
                    ou_line = None

        # Step 7: Parse opponent
        if not opp_raw:
            return None

        is_home    = not bool(re.match(r'^at\s+', opp_raw, re.IGNORECASE))
        is_neutral = bool(re.match(r'^n\s+', opp_raw)) and opp_raw[0] == 'n'
        is_playoff = bool(re.match(r'^(?:pl|ply)', opp_raw, re.IGNORECASE))

        opp = re.sub(r'^(?:at\s+|pl\s+|ply\s+)', '', opp_raw, flags=re.IGNORECASE).strip()
        opp = re.sub(r'^(?:@)', '', opp).strip()
        # Only strip lowercase 'n ' (neutral marker), keep 'N ' as city prefix
        if opp and opp[0] == 'n' and len(opp) > 2 and opp[1] == ' ':
            opp = opp[2:].strip()
        opp = re.sub(r'\s+[Bb]wl$', '', opp, flags=re.IGNORECASE).strip()  # strip trailing Bwl only

        if not opp or len(opp) < 2:
            return None

        return {
            'opp'       : opp,
            'is_home'   : is_home,
            'is_neutral': is_neutral,
            'is_playoff': is_playoff,
            'pf'        : pf,
            'pa'        : pa,
            'su'        : su,
            'line'      : line_float,
            'ats'       : ats,
            'ou'        : ou,
            'ou_line'   : ou_line,
        }

    for table, grid, season_year, coach, data_start in ats_tables:
        game_num = 0

        for row_idx in range(data_start, table.row_count):
            cells = [grid.get((row_idx, c), '').strip() for c in range(table.column_count)]
            full  = ' '.join(cells).strip()

            if not full or len(full) < 5:
                continue
            # Skip header rows
            if any(h in full.upper() for h in ['OPPONENT', 'SCORE SU', 'ATS O/U', 'AT TWICKENHAM',
                                                 'AT WEMBLEY', 'AT TOTTENHAM', 'LONDON', 'MUNICH']):
                continue
            # Skip footnote lines
            if full.startswith('*') or re.match(r'^\*', full):
                continue

            game = parse_row(cells, table.column_count)
            if not game:
                continue

            game_num += 1

            db.execute(text("""
                INSERT INTO ats_history
                    (id, team_id, season_year, coach_name, game_num,
                     opponent, is_home, is_neutral, is_playoff,
                     points_for, points_against, su_result,
                     line, ats_result, ou_result, ou_line, game_type)
                VALUES
                    (gen_random_uuid(), :tid, :yr, :coach, :gnum,
                     :opp, :home, :neutral, :playoff,
                     :pf, :pa, :su, :line, :ats, :ou, :oul, NULL)
                ON CONFLICT (team_id, season_year, game_num)
                DO UPDATE SET
                    opponent=EXCLUDED.opponent,
                    is_home=EXCLUDED.is_home,
                    points_for=EXCLUDED.points_for,
                    points_against=EXCLUDED.points_against,
                    su_result=EXCLUDED.su_result,
                    line=EXCLUDED.line,
                    ats_result=EXCLUDED.ats_result,
                    ou_result=EXCLUDED.ou_result,
                    ou_line=EXCLUDED.ou_line,
                    updated_at=NOW()
            """), {
                'tid'    : str(team.id),
                'yr'     : season_year,
                'coach'  : coach,
                'gnum'   : game_num,
                'opp'    : game['opp'],
                'home'   : game['is_home'],
                'neutral': game['is_neutral'],
                'playoff': game['is_playoff'],
                'pf'     : game['pf'],
                'pa'     : game['pa'],
                'su'     : game['su'],
                'line'   : game['line'],
                'ats'    : game['ats'],
                'ou'     : game['ou'],
                'oul'    : game['ou_line'],
            })
            saved += 1

        db.commit()
        print(f"    {season_year}: {game_num} games ({coach})")

    print(f"  ✓ ATS history: {abbr} — {saved} total games")
    return saved



def parse_cfb_ats_history(result, name: str, teams: dict, db) -> int:
    """
    Parse 10-year ATS history from CFB team page using Azure DI tables.
    
    Differences from NFL (parse_ats_history):
    - No O/U column (CFB doesn't track O/U in this section)
    - Line shown as "---" when no line available (FCS opponents etc)
    - Bowl game opponents have "Bwl" suffix
    - More playoff/bowl games per season
    - Same Azure DI table structure (one table per year)
    """
    import re
    from sqlalchemy import text

    team = teams.get(name)
    if not team:
        print(f"  ✗ CFB team not found: {name}")
        return 0

    # ── Find ATS history tables ───────────────────────────────
    ats_tables = []
    years_found = []

    for table in result.tables:
        if table.row_count < 5:
            continue
        grid = get_table_grid(table)

        # Scan rows 0-2 for year pattern
        yr    = None
        coach = ''
        all_text = re.sub(r'[\*†\n]', ' ', ' '.join([
            grid.get((r, c), '')
            for r in range(min(3, table.row_count))
            for c in range(table.column_count)
        ]))

        # Find year
        yr_m = re.search(r'(20\d\d)', all_text)
        if yr_m:
            yr = int(yr_m.group(1))
            if yr > 2024: 
                continue   # ← skip invalid years
            # Find coach after dash following year
            after_yr = all_text[yr_m.end():]
            dash_m = re.search(r'[-–]\s*([A-Z][A-Z\s]+?)(?=OPPONENT|SCORE|SU|LINE|ATS|\d{2,}|$)', after_yr)
            if dash_m:
                raw = dash_m.group(1).strip()
                coach = ' '.join(w for w in raw.split()
                                 if w not in ('OPPONENT','SCORE','SU','LINE','ATS','O/U')
                                 and w.isalpha()).strip()

        # Find data start row
        data_start = 2
        for r in range(table.row_count):
            row_text = ' '.join([grid.get((r, c), '') for c in range(table.column_count)])
            if re.search(r'\d+\s*[-–]\s*\d+', row_text) and re.search(r'[WLT]\s', row_text):
                data_start = r
                break

        # If no year found but has valid headers — assign next year
        if not yr:
            header_text = all_text.upper()
            if 'RET STARTERS' in header_text or 'WIN-LOSS' in header_text or 'RECRUITING' in header_text:
                continue
            if 'YPR' in header_text and 'RSH' in header_text and 'PSS' in header_text:
                continue
            if 'OPPONENT' in header_text and 'SCORE' in header_text and 'LINE' in header_text:
                yr = (years_found[-1] + 1) if years_found else None
            elif data_start == 0:
                yr = (years_found[-1] + 1) if years_found else None

        if yr:
            ats_tables.append((table, grid, yr, coach, data_start))
            years_found.append(yr)

    if not ats_tables:
        print(f"  ✗ No ATS history tables found for {name}")
        return 0

    # ── Core row parser (score-relative, no O/U) ─────────────
    SCORE_PAT = re.compile(r'^(\d+)\s*[-–]\s*(\d+)')

    def clean(s):
        s = re.sub(r':selected:|:unselected:', '', s or '')
        return re.sub(r"['\*†]", '', s).strip()

    def parse_row(cells, col_count):
        cells = [clean(c) for c in cells]

        # Find score cell
        score_col = None
        pf = pa = None

        for c in range(col_count):
            m = SCORE_PAT.match(cells[c].replace(' ', ''))
            if m:
                score_col = c
                pf = int(m.group(1))
                pa = int(m.group(2))
                break

        # Try combining adjacent cells for split score
        if score_col is None:
            for c in range(col_count - 1):
                combined = cells[c] + cells[c+1]
                m = SCORE_PAT.match(combined.replace(' ', ''))
                if m:
                    cells[c] = combined
                    cells.pop(c+1)
                    score_col = c
                    pf = int(m.group(1))
                    pa = int(m.group(2))
                    break

        if score_col is None or pf is None:
            return None

        # Opponent = everything before score
        opp_parts = [cells[c] for c in range(score_col) if cells[c]]
        opp_raw   = ' '.join(opp_parts).strip()
        if 'ashingto' in opp_raw:
            print(f"  DEBUG opp: {repr(opp_raw)} cells={cells}")

        # After score
        after = [cells[c] for c in range(score_col + 1, len(cells)) if cells[c]]

        if not after:
            return None

        # Parse SU
        su = None
        su_idx = 0
        line_sign = ''
        for i, val in enumerate(after):
            val_clean = re.sub(r'^[BMSTNbmstn]+\s*', '', val).strip()
            if val_clean[:1].upper() in ('W', 'L', 'T'):
                su = val_clean[:1].upper()
                su_idx = i
                # Check if line sign is attached: "L +" or "W -"
                sign_m = re.search(r'[WLT]\s*([+\-])\s*$', val_clean)
                if sign_m:
                    line_sign = sign_m.group(1)  # ← capture sign
                break

        after_su = after[su_idx + 1:]

        # Parse LINE — handle "---" as null
        line_float = None
        line_idx   = 0
        for i, val in enumerate(after_su):
            val_clean = val.replace(' ', '')

            if line_sign and re.match(r'^\d+\.?\d*$', val_clean):
                try:
                    line_float = float(line_sign + val_clean)
                    line_idx = i
                    break
                except:
                    pass

            # No line available
            if re.match(r'^-{2,}$', val_clean):
                line_float = None
                line_idx   = i
                break

            if val_clean.lower() in ('pk', 'pick'):
                line_float = 0.0
                line_idx   = i
                break

            m = re.match(r'^([+\-])(\d+\.?\d*)$', val_clean)
            if m:
                try:
                    line_float = float(m.group(1) + m.group(2))
                    line_idx   = i
                    break
                except:
                    pass

            # Sign only
            if val_clean in ('+', '-') and i + 1 < len(after_su):
                next_val = after_su[i+1].replace(' ', '')
                if re.match(r'^\d+\.?\d*$', next_val):
                    try:
                        line_float = float(val_clean + next_val)
                        after_su = after_su[:i] + [val_clean + next_val] + after_su[i+2:]
                        line_idx = i
                        break
                    except:
                        pass

        after_line = after_su[line_idx + 1:]

        # Parse ATS (no O/U for CFB)
        ats = None
        for val in after_line:
            val_clean = clean(val)
            if not val_clean:
                continue
            if val_clean.upper()[:1] in ('W', 'L', 'T', 'P'):
                ats = val_clean.upper()[:1]
                break

        # Parse opponent
        if not opp_raw:
            return None

        is_home    = not bool(re.match(r'^at\s+', opp_raw, re.IGNORECASE))
        is_neutral = bool(re.match(r'^n\s+', opp_raw)) and opp_raw[0] == 'n'
        is_playoff = bool(re.match(r'^(?:ply|pl)\s', opp_raw, re.IGNORECASE))

        opp = re.sub(r'^(?:at\s+|ply\s+|pl\s+)', '', opp_raw, flags=re.IGNORECASE).strip()
        opp = re.sub(r'^@', '', opp).strip()
        # Strip lowercase 'n ' neutral marker, keep uppercase 'N ' as city
        if opp and opp[0] == 'n' and len(opp) > 2 and opp[1] == ' ':
            opp = opp[2:].strip()
        # Only strip trailing 'Bwl' — do NOT strip single letters like n/m/t
        # as they appear in team names (Oregon, Washington, Texas A&M etc)
        opp = re.sub(r'\s+Bwl$', '', opp, flags=re.IGNORECASE).strip()
        # Remove "Bwl" suffix from bowl games
        opp = re.sub(r'\s+Bwl$', '', opp, flags=re.IGNORECASE).strip()

        if 'Texas' in ' '.join(cells) or 'Oregon' in ' '.join(cells) or 'Washington' in ' '.join(cells):
            print(f"  DEBUG cells={cells} opp_raw={repr(opp_raw)} opp={repr(opp)}")

        if not opp or len(opp) < 2:
            return None

        return {
            'opp'       : opp,
            'is_home'   : is_home,
            'is_neutral': is_neutral,
            'is_playoff': is_playoff,
            'pf'        : pf,
            'pa'        : pa,
            'su'        : su,
            'line'      : line_float,
            'ats'       : ats,
        }

    # ── Parse each table ─────────────────────────────────────
    saved = 0

    for table, grid, season_year, coach, data_start in ats_tables:
        game_num = 0

        for row_idx in range(data_start, table.row_count):
            cells = [grid.get((row_idx, c), '').strip() for c in range(table.column_count)]
            full  = ' '.join(cells).strip()

            if not full or len(full) < 5:
                continue
            if any(h in full.upper() for h in ['OPPONENT', 'SCORE SU', 'ATS O/U',
                                                'AT TWICKENHAM', 'AT WEMBLEY',
                                                'AT TOTTENHAM', 'LONDON', 'MUNICH',
                                                'PLAYBOOK', 'HISTORY RESULTS']):
                continue
            if full.startswith('*') or re.match(r'^\*', full):
                continue

            game = parse_row(cells, table.column_count)
            if not game:
                continue

            game_num += 1

            db.execute(text("""
                INSERT INTO ats_history
                    (id, team_id, season_year, coach_name, game_num,
                     opponent, is_home, is_neutral, is_playoff,
                     points_for, points_against, su_result,
                     line, ats_result, ou_result, ou_line, game_type)
                VALUES
                    (gen_random_uuid(), :tid, :yr, :coach, :gnum,
                     :opp, :home, :neutral, :playoff,
                     :pf, :pa, :su, :line, :ats, NULL, NULL, NULL)
                ON CONFLICT (team_id, season_year, game_num)
                DO UPDATE SET
                    opponent=EXCLUDED.opponent,
                    is_home=EXCLUDED.is_home,
                    points_for=EXCLUDED.points_for,
                    points_against=EXCLUDED.points_against,
                    su_result=EXCLUDED.su_result,
                    line=EXCLUDED.line,
                    ats_result=EXCLUDED.ats_result,
                    updated_at=NOW()
            """), {
                'tid'    : str(team.id),
                'yr'     : season_year,
                'coach'  : coach,
                'gnum'   : game_num,
                'opp'    : game['opp'],
                'home'   : game['is_home'],
                'neutral': game['is_neutral'],
                'playoff': game['is_playoff'],
                'pf'     : game['pf'],
                'pa'     : game['pa'],
                'su'     : game['su'],
                'line'   : game['line'],
                'ats'    : game['ats'],
            })
            saved += 1

        db.commit()
        print(f"    {season_year}: {game_num} games ({coach})")

    print(f"  ✓ CFB ATS history: {name} — {saved} total games")
    return saved

def parse_nfl_draft_analysis(result, abbr: str, teams: dict, db) -> bool:
    """
    Parse Draft Grades, First Round, and Steal Of The Draft
    from NFL team first page (right column).
    Uses Azure DI polygon x-position to isolate right column.
    Sections appear to the right of the stat logs column.
    """
    import re
    from sqlalchemy import text

    team = teams.get(abbr)
    if not team:
        print(f"  ✗ Team not found: {abbr}")
        return False

    # ── Get right column lines using polygon x-position ──────
    # Right column (draft info) starts at x > 4.5 inches
    RIGHT_X = 4.5

    right_lines = []
    for page in result.pages:
        for line in page.lines:
            x = min(pt.x for pt in line.polygon)
            if x >= RIGHT_X:
                right_lines.append(line.content.strip())
        break

    if not right_lines:
        print(f"  ✗ No right column lines found for {abbr}")
        return False

    # ── Parse sections ────────────────────────────────────────
    draft_grades_lines  = []
    first_round_lines   = []
    steal_lines         = []
    current             = None

    for line in right_lines:
        upper = line.upper().strip()

        if not line.strip():
            continue

        # Section headers
        if upper == 'DRAFT GRADES' or 'DRAFT GRADES' == upper:
            current = 'grades'
            continue
        if upper == 'FIRST ROUND':
            current = 'first_round'
            continue
        if 'STEAL OF THE DRAFT' in upper:
            current = 'steal'
            continue

        # Stop at known non-draft sections
        if any(h in upper for h in ['ROUND / PLAYER', 'PLAYBOOK SPORTS', 'CARDINALS', 'BILLS',
                                      'RAVENS', 'BEARS', 'BENGALS', 'BROWNS', 'COWBOYS',
                                      'BRONCOS', 'LIONS', 'PACKERS', 'TEXANS', 'COLTS',
                                      'JAGUARS', 'CHIEFS', 'RAIDERS', 'CHARGERS', 'RAMS',
                                      'DOLPHINS', 'VIKINGS', 'PATRIOTS', 'SAINTS', 'GIANTS',
                                      'JETS', 'EAGLES', 'STEELERS', '49ERS', 'SEAHAWKS',
                                      'BUCCANEERS', 'TITANS', 'COMMANDERS', 'FALCONS',
                                      'PANTHERS']):
            continue

        # Skip draft pick table rows (e.g. "1 Walter Nolen DT 6'4 304 Ole Miss")
        if re.match(r'^\d+\s+[A-Z][a-z]', line):
            continue

        # Assign to sections
        if current == 'grades':
            # Grades lines have patterns like "PLAYBOOK: A..." or "ESPN: B..."
            if any(g in upper for g in ['PLAYBOOK:', 'ESPN:', 'OURLADS:', 'PFF:', 'SI:', 'COMPOSITE:']):
                draft_grades_lines.append(line.strip())

        elif current == 'first_round':
            # Prose lines have lowercase letters
            if any(c.islower() for c in line) and len(line.strip()) > 5:
                first_round_lines.append(line.strip())
            # Also capture ALL CAPS player name lines like "DT WALTER NOLEN of Ole Miss"
            elif re.search(r'[A-Z]{2,}\s+[A-Z]{2,}', line) and any(c.islower() for c in line):
                first_round_lines.append(line.strip())

        elif current == 'steal':
            if any(c.islower() for c in line) and len(line.strip()) > 5:
                steal_lines.append(line.strip())

    draft_grades  = ' '.join(draft_grades_lines).strip() or None
    first_round   = ' '.join(first_round_lines).strip() or None
    steal_of_draft = ' '.join(steal_lines).strip() or None

    if not draft_grades and not first_round and not steal_of_draft:
        print(f"  ✗ No draft analysis found for {abbr}")
        return False

    # ── Update team_playbook ──────────────────────────────────
    db.execute(text("""
        UPDATE team_playbook
        SET
            draft_grades   = :grades,
            first_round    = :first_round,
            steal_of_draft = :steal,
            updated_at     = NOW()
        WHERE team_id = :tid AND season_year = 2025
    """), {
        'tid'        : str(team.id),
        'grades'     : draft_grades,
        'first_round': first_round,
        'steal'      : steal_of_draft,
    })
    db.commit()

    print(f"  ✓ Draft analysis: {abbr} grades={bool(draft_grades)} first_round={bool(first_round)} steal={bool(steal_of_draft)}")
    return True

def parse_cfb_stadiums(result, name: str, teams: dict, db) -> bool:
    """
    Parse stadium, nickname, full conference, and website from CFB team page.
    Line format:
      Line 0: Team name (ALABAMA)
      Line 6: Nickname (CRIMSON TIDE)
      Line 9: Stadium (Bryant-Denny Stadium (Grass) • Capacity: 100,077 • Tuscaloosa, AL)
      Line 11: Conference ... 4 YEAR STATISTICAL REVIEW ... www.rolltide.com
    """
    import re
    from sqlalchemy import text

    team = teams.get(name)
    if not team:
        print(f"  ✗ CFB team not found: {name}")
        return False

    # Get raw lines from page (not stripped — to find website at end)
    raw_lines = []
    lines = []
    for page in result.pages:
        raw_lines = [l.content for l in page.lines]
        lines = [l.strip() for l in raw_lines]
        break

    stadium = None
    surface = None
    capacity = None
    city = None
    nickname = None
    full_conference = None
    website = None

    skip_patterns = [
        r'^\d+', r'^RPR', r'OFF\s*/\s*DEF', r'SU\s*[•·]', r'Recruit Rank',
        r'Year$', r'^\*', r'Coach', r'Record With', r'^4 YEAR'
    ]
    team_name_upper = name.upper()
    found_team_name = False

    for i, line in enumerate(lines[:25]):
        if not line:
            continue

        # Skip team name
        if line.upper() == team_name_upper or line.upper().startswith(team_name_upper):
            found_team_name = True
            continue

        # Stadium with surface
        m = re.search(
            r'(.+?)\s*\(([^)]+)\)\s*[•·\.]\s*Capacity:\s*([\d,]+)\s*[•·\.]\s*(.+)',
            line, re.IGNORECASE
        )
        if m:
            stadium  = m.group(1).strip()
            surface  = m.group(2).strip()
            capacity = int(m.group(3).replace(',', ''))
            city     = m.group(4).strip()
            continue

        # Stadium without surface
        m2 = re.search(
            r'(.+?)\s*[•·\.]\s*Capacity:\s*([\d,]+)\s*[•·\.]\s*(.+)',
            line, re.IGNORECASE
        )
        if m2 and not stadium:
            stadium  = m2.group(1).strip()
            capacity = int(m2.group(2).replace(',', ''))
            city     = m2.group(3).strip()
            continue

        # Nickname — ALL CAPS, after team name, BEFORE stadium line
        if (found_team_name and
            nickname is None and
            stadium is None and  # ← only before stadium found
            re.match(r'^[A-Z][A-Z\s]+$', line) and
            2 < len(line) < 40 and
            not re.search(r'\d', line) and
            not any(re.search(p, line, re.IGNORECASE) for p in skip_patterns)):
            nickname = line.strip()

        # Conference + website line (e.g. "Southeastern Conference   4 YEAR...   www.rolltide.com")
        if re.search(r'Conference|Independent|Association', line, re.IGNORECASE):
            # Extract full conference name (first part before 4 YEAR)
            conf_m = re.match(r'^([A-Za-z0-9\s\-]+(?:Conference|Independent|Association))', line, re.IGNORECASE)
            if conf_m:
                full_conference = conf_m.group(1).strip()
            # Extract website from raw line (at the end)
            raw = raw_lines[i] if i < len(raw_lines) else line
            web_m = re.search(r'(www\.[a-z0-9\.\-]+)', raw, re.IGNORECASE)
            if web_m:
                website = web_m.group(1).strip()
            continue

        # Website — standalone www. line
        if re.match(r'^www\.', line, re.IGNORECASE):
            website = line.strip()
            continue
        # Nickname — ALL CAPS, after team name AND after seeing year/SU record
        if (found_team_name and
            nickname is None and
            re.match(r'^[A-Z][A-Z\s]+$', line) and
            2 < len(line) < 40 and
            not re.search(r'\d', line) and
            not any(re.search(p, line, re.IGNORECASE) for p in skip_patterns) and
            # Must come after SU record or year line (indicates coach section passed)
            any(re.search(r'SU|Year|Record', lines[j], re.IGNORECASE)
                for j in range(i) if j < len(lines) and lines[j])):
            nickname = line.strip()

    if not stadium and not nickname:
        print(f"  ✗ No data found for {name}")
        return False

    db.execute(text("""
        UPDATE teams SET
            stadium          = :stadium,
            stadium_surface  = :surface,
            stadium_capacity = :capacity,
            stadium_city     = :city,
            nickname         = :nickname,
            conference       = COALESCE(:full_conf, conference),
            website          = :website
        WHERE id = :tid
    """), {
        'tid'      : str(team.id),
        'stadium'  : stadium,
        'surface'  : surface,
        'capacity' : capacity,
        'city'     : city,
        'nickname' : nickname,
        'full_conf': full_conference,
        'website'  : website,
    })
    db.commit()
    print(f"  ✓ {name}: nickname={nickname} conf={full_conference} web={website} stadium={stadium}")
    return True


# ── Step 5: Generate embeddings ───────────────────────────────

def generate_embeddings(db):
    if not settings.azure_openai_key or settings.azure_openai_key == "your-key-here":
        print("\n── Skipping embeddings — Azure OpenAI not configured")
        return
    print("\n── Generating embeddings ─────────────────────────")
    from app.services.ingestion_service import generate_embeddings_for_all_teams
    count = generate_embeddings_for_all_teams(db)
    print(f"  ✓ Embeddings generated: {count}")



# ── Main ──────────────────────────────────────────────────────

def main():
    global PDF_PATH

    parser = argparse.ArgumentParser(
        description="Populate Playbook Football database from PDF"
    )
    parser.add_argument("--pdf",           type=str,            help="Path to the PDF file")
    parser.add_argument("--teams-only",    action="store_true", help="Only seed teams, skip PDF")
    parser.add_argument("--team",          type=str,            help="Test single NFL team e.g. ARI")
    parser.add_argument("--cfb-team",      type=str,            help="Test single CFB team e.g. Alabama")
    parser.add_argument("--cfb-only",      action="store_true", help="Run CFB ingestion only (all teams)")
    parser.add_argument("--cfb-resume",    action="store_true", help="Resume CFB ingestion, skip teams with 4 years")
    parser.add_argument("--nfl-games",     action="store_true", help="Parse NFL schedule/gamelogs/draft picks")
    parser.add_argument("--playbook-team", type=str,            help="Parse playbook for single NFL team e.g. ARI")
    parser.add_argument("--nfl-playbook",  action="store_true", help="Parse NFL second pages for all 32 teams")
    parser.add_argument("--nfl-coaches",   action="store_true", help="Fix NFL coach names from team pages for all 32 teams")
    parser.add_argument("--cfb-games", action="store_true", help="Parse CFB schedule for all teams")
    parser.add_argument("--cfb-game-team", type=str, help="Parse CFB schedule for single team")
    parser.add_argument("--cfb-gamelogs",      action="store_true", help="Parse CFB stat logs for all teams")
    parser.add_argument("--cfb-gamelog-team",  type=str,            help="Parse CFB stat logs for single team")
    parser.add_argument("--cfb-coaches",    action="store_true", help="Parse CFB coaches for all teams")
    parser.add_argument("--cfb-coach-team", type=str,            help="Parse CFB coach for single team")
    parser.add_argument("--cfb-playbook",      action="store_true", help="Parse CFB playbook for all teams")
    parser.add_argument("--cfb-playbook-team", type=str,            help="Parse CFB playbook for single team")
    parser.add_argument("--nfl-ats-history",      action="store_true", help="Parse NFL 10-year ATS history all teams")
    parser.add_argument("--cfb-ats-history",      action="store_true", help="Parse CFB 10-year ATS history all teams")
    parser.add_argument("--cfb-ats-history-team",  type=str,            help="Parse CFB 10-year ATS history single team")
    parser.add_argument("--nfl-draft-analysis", action="store_true", help="Parse NFL draft grades, first round, steal of draft")
    parser.add_argument("--nfl-draft-analysis-team", type=str, help="Parse draft analysis for single NFL team e.g. ARI")
    parser.add_argument("--cfb-stadiums", action="store_true", help="Parse CFB stadium info for all teams")
    args = parser.parse_args()

    enable_pgvector()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Always seed NFL teams first
        nfl_teams = seed_teams(db)

        if args.teams_only:
            print("\n✓ NFL Teams seeded. Use --pdf to import stats.")
            return

        if not args.pdf:
            print("\nNo --pdf provided. Teams seeded only.")
            print("Run: python ingest.py --pdf PATH_TO_PDF")
            return

        PDF_PATH = args.pdf

        if not Path(PDF_PATH).exists():
            print(f"\n✗ PDF not found: {PDF_PATH}")
            sys.exit(1)

        # ── Single CFB team ────────────────────────────────────
        if args.cfb_team:
            cfb_teams = seed_cfb_teams(db)
            seed_cfb_stats_from_pdf(db, cfb_teams, test_name=args.cfb_team)
            generate_embeddings(db)
            print("\n✓ CFB ingestion complete")
            return

        # ── All CFB teams ──────────────────────────────────────
        elif args.cfb_only:
            cfb_teams = seed_cfb_teams(db)
            seed_cfb_stats_from_pdf(db, cfb_teams, test_name=None, resume=args.cfb_resume)
            generate_embeddings(db)
            print("\n✓ CFB ingestion complete")
            return

        # ── NFL games (schedule/gamelogs/draft picks) ──────────
        elif args.nfl_games:
            seed_nfl_game_data_from_pdf(db, nfl_teams, test_abbr=args.team)
            print("\n✓ NFL game data complete")
            return

        # ── Single NFL team playbook ───────────────────────────
        elif args.playbook_team:
            abbr = args.playbook_team.upper()
            page = NFL_PLAYBOOK_PAGES.get(abbr)
            if not page:
                print(f"✗ Unknown team: {abbr}")
            else:
                print(f"\n── Parsing Playbook for {abbr} (page {page}) ────────────")
                teams = {t.abbreviation: t for t in db.query(Team).filter(Team.league == 'NFL').all()}
                result = analyze_pages(args.pdf, page)
                parse_team_playbook(result, abbr, teams, db)
            return

        # ── All NFL team playbooks ─────────────────────────────
        elif args.nfl_playbook:
            print("\n── Parsing NFL Playbook pages ─────────────────────────")
            teams = {t.abbreviation: t for t in db.query(Team).filter(Team.league == 'NFL').all()}
            for abbr, page in NFL_PLAYBOOK_PAGES.items():
                print(f"  Parsing {abbr} (page {page})...")
                try:
                    result = analyze_pages(args.pdf, page)
                    parse_team_playbook(result, abbr, teams, db)
                except Exception as e:
                    print(f"  ✗ {abbr} failed: {e}")
            print("✓ NFL Playbook ingestion complete")
            return

        elif args.nfl_coaches:
            print("\n── Fixing NFL Coach Names from team pages ─────────────")
            for abbr, page in NFL_TEAM_PAGES.items():
                print(f"  Parsing {abbr} (page {page})...")
                try:
                    result = analyze_pages(args.pdf, str(page))
                    parse_team_page(result, abbr, nfl_teams, db)
                except Exception as e:
                    print(f"  ✗ {abbr} failed: {e}")
            print("✓ NFL coach names updated")
            return

        elif args.cfb_gamelog_team:
            cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
            page = CFB_TEAM_PAGES.get(args.cfb_gamelog_team)
            if not page:
                print(f"✗ Unknown CFB team: {args.cfb_gamelog_team}")
            else:
                result = analyze_pages(args.pdf, page)
                saved = parse_cfb_gamelogs(result, args.cfb_gamelog_team, cfb_teams, db)
                print(f"✓ Saved {saved} game logs for {args.cfb_gamelog_team}")
            return

        elif args.cfb_gamelogs:
            print("\n── Parsing CFB Game Logs ─────────────────────────────")
            cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
            for name, page in CFB_TEAM_PAGES.items():
                print(f"  Parsing {name} (page {page})...")
                try:
                    result = analyze_pages(args.pdf, page)
                    saved = parse_cfb_gamelogs(result, name, cfb_teams, db)
                    print(f"  ✓ {saved} games")
                except Exception as e:
                    print(f"  ✗ {name} failed: {e}")
            print("✓ CFB game logs complete")
            return
        
        elif args.nfl_draft_analysis_team:
            abbr = args.nfl_draft_analysis_team.upper()
            page = NFL_TEAM_PAGES.get(abbr)
            if not page:
                print(f"✗ Unknown team: {abbr}")
            else:
                teams = {t.abbreviation: t for t in db.query(Team).filter(Team.league == 'NFL').all()}
                result = analyze_pages(args.pdf, str(page))
                parse_nfl_draft_analysis(result, abbr, teams, db)
            return

        elif args.nfl_draft_analysis:
            print("\n── Parsing NFL Draft Analysis ────────────────────────")
            teams = {t.abbreviation: t for t in db.query(Team).filter(Team.league == 'NFL').all()}
            for abbr, page in NFL_TEAM_PAGES.items():
                print(f"  Parsing {abbr} (page {page})...")
                try:
                    result = analyze_pages(args.pdf, str(page))
                    parse_nfl_draft_analysis(result, abbr, teams, db)
                except Exception as e:
                    print(f"  ✗ {abbr} failed: {e}")
            print("✓ NFL draft analysis complete")
            return

        elif args.cfb_stadiums:
            print("\n── Parsing CFB Stadium Info ──────────────────────────")
            cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
            for name, page in CFB_TEAM_PAGES.items():
                try:
                    result = analyze_pages(args.pdf, str(page))
                    parse_cfb_stadiums(result, name, cfb_teams, db)
                except Exception as e:
                    db.rollback()
                    print(f"  ✗ {name} failed: {e}")
            print("✓ CFB stadium info complete")
            return

        elif args.cfb_ats_history_team:
            name = args.cfb_ats_history_team
            page = CFB_TEAM_PAGES.get(name)
            if not page:
                print(f"✗ Unknown CFB team: {name}")
            else:
                cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
                result = analyze_pages(args.pdf, page)
                saved = parse_cfb_ats_history(result, name, cfb_teams, db)
                print(f"✓ {saved} games saved for {name}")
            return

        elif args.cfb_ats_history:
            print("\n── Parsing CFB ATS History ───────────────────────────")
            cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
            for name, page in CFB_TEAM_PAGES.items():
                print(f"  Parsing {name} (page {page})...")
                try:
                    result = analyze_pages(args.pdf, page)
                    parse_cfb_ats_history(result, name, cfb_teams, db)
                except Exception as e:
                    print(f"  ✗ {name} failed: {e}")
            print("✓ CFB ATS history complete")
            return

        # ── Single NFL team stats ──────────────────────────────
        elif args.team:
            seed_coaches_from_pdf(db, nfl_teams)  # ATS splits only
            seed_sos_from_pdf(db, nfl_teams)
            seed_team_stats_from_pdf(db, nfl_teams, test_abbr=args.team.upper())  # overwrites coach name
            generate_embeddings(db)
            print("\n✓ Ingestion complete")
            return

        elif args.cfb_game_team:
            cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
            page = CFB_TEAM_PAGES.get(args.cfb_game_team)
            if not page:
                print(f"✗ Unknown CFB team: {args.cfb_game_team}")
            else:
                result = analyze_pages(args.pdf, page)
                saved = parse_cfb_schedule(result, args.cfb_game_team, cfb_teams, db)
                print(f"✓ Saved {saved} schedule games for {args.cfb_game_team}")
            return

        elif args.cfb_games:
            print("\n── Parsing CFB Schedule ──────────────────────────────")
            cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
            for name, page in CFB_TEAM_PAGES.items():
                print(f"  Parsing {name} (page {page})...")
                try:
                    result = analyze_pages(args.pdf, page)
                    saved = parse_cfb_schedule(result, name, cfb_teams, db)
                    print(f"  ✓ {saved} games")
                except Exception as e:
                    print(f"  ✗ {name} failed: {e}")
            print("✓ CFB schedule complete")
            return

        elif args.cfb_coach_team:
            cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
            page = CFB_TEAM_PAGES.get(args.cfb_coach_team)
            if not page:
                print(f"✗ Unknown CFB team: {args.cfb_coach_team}")
            else:
                result = analyze_pages(args.pdf, page)
                parse_cfb_coach(result, args.cfb_coach_team, cfb_teams, db)
            return

        elif args.cfb_coaches:
            print("\n── Parsing CFB Coaches ───────────────────────────────")
            cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
            for name, page in CFB_TEAM_PAGES.items():
                print(f"  Parsing {name} (page {page})...")
                try:
                    result = analyze_pages(args.pdf, page)
                    parse_cfb_coach(result, name, cfb_teams, db)
                except Exception as e:
                    print(f"  ✗ {name} failed: {e}")
            print("✓ CFB coaches complete")
            return

        elif args.cfb_playbook_team:
            cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
            page = CFB_TEAM_PAGES.get(args.cfb_playbook_team)
            if not page:
                print(f"✗ Unknown CFB team: {args.cfb_playbook_team}")
            else:
                result = analyze_pages(args.pdf, page)
                parse_cfb_playbook(result, args.cfb_playbook_team, cfb_teams, db)
            return

        elif args.cfb_playbook:
            print("\n── Parsing CFB Playbook ──────────────────────────────")
            cfb_teams = {t.name: t for t in db.query(Team).filter(Team.league == 'CFB').all()}
            for name, page in CFB_TEAM_PAGES.items():
                print(f"  Parsing {name} (page {page})...")
                try:
                    result = analyze_pages(args.pdf, page)
                    parse_cfb_playbook(result, name, cfb_teams, db)
                except Exception as e:
                    print(f"  ✗ {name} failed: {e}")
            print("✓ CFB Playbook complete")
            return
        
        elif args.nfl_ats_history_team:
            abbr = args.nfl_ats_history_team.upper()
            page = NFL_PLAYBOOK_PAGES.get(abbr)
            if not page:
                print(f"✗ Unknown team: {abbr}")
            else:
                teams = {t.abbreviation: t for t in db.query(Team).filter(Team.league == 'NFL').all()}
                result = analyze_pages(args.pdf, page)
                saved = parse_ats_history(result, abbr, teams, db)
                print(f"✓ {saved} games saved for {abbr}")
            return

        elif args.nfl_ats_history:
            print("\n── Parsing NFL ATS History ───────────────────────────")
            teams = {t.abbreviation: t for t in db.query(Team).filter(Team.league == 'NFL').all()}
            for abbr, page in NFL_PLAYBOOK_PAGES.items():
                print(f"  Parsing {abbr} (page {page})...")
                try:
                    result = analyze_pages(args.pdf, page)
                    parse_ats_history(result, abbr, teams, db)
                except Exception as e:
                    print(f"  ✗ {abbr} failed: {e}")
            print("✓ NFL ATS history complete")
            return

        # ── Full ingestion — NFL + CFB ─────────────────────────
        else:
            seed_coaches_from_pdf(db, nfl_teams)
            seed_sos_from_pdf(db, nfl_teams)
            seed_team_stats_from_pdf(db, nfl_teams)

            cfb_teams = seed_cfb_teams(db)
            seed_cfb_stats_from_pdf(db, cfb_teams)

            generate_embeddings(db)
            print("\n✓ Ingestion complete")

    except Exception as e:
        print(f"\nX Ingestion failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()