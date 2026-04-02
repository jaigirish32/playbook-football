#  Playbook Football

A full-stack NFL & CFB sports analytics web application that ingests data from the Playbook Sports PDF and presents comprehensive team statistics, ATS history, schedules, draft information, and AI-powered chat.

---

##  Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI + Uvicorn (Python 3.12) |
| **Database** | PostgreSQL (Docker local / Azure PostgreSQL) |
| **ORM** | SQLAlchemy 2 + Alembic |
| **Frontend** | React 19 + Vite + Tailwind CSS |
| **PDF Parsing** | Azure Document Intelligence (prebuilt-layout) |
| **AI Chat** | Azure OpenAI (GPT-4o-mini) |
| **Embeddings** | Azure OpenAI (text-embedding-3-small) |
| **Auth** | FastAPI-Users + JWT |

---

## Project Structure

```
playbook-football/
├── backend/
│   ├── app/
│   │   ├── core/          # Config, DB, security
│   │   ├── models/        # SQLAlchemy models
│   │   ├── repositories/  # DB operations
│   │   ├── routers/       # API endpoints
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Azure DI, OpenAI
│   ├── main.py            # FastAPI app
│   ├── ingest.py          # PDF ingestion CLI
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/         # TeamPage, HomePage, etc.
│       ├── components/    # Layout
│       ├── api/           # Axios API calls
│       └── store/         # Zustand state
└── docker-compose.yml
```

---

##  Setup

### 1. Prerequisites
- Python 3.12+
- Node.js 18+
- Docker Desktop
- Azure Document Intelligence account
- Azure OpenAI account

### 2. Database
```bash
docker-compose up -d
```

### 3. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Create .env file (see .env.example)
cp .env.example .env
# Fill in your Azure keys

# Run migrations
alembic upgrade head

# Start server
uvicorn main:app --reload --port 8000
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

##  Data Ingestion

The `ingest.py` CLI parses the Playbook Sports PDF into the database.

### NFL Ingestion
```bash
# Full NFL ingestion
python ingest.py --pdf PATH_TO_PDF

# Single team
python ingest.py --pdf PATH_TO_PDF --team ARI

# Schedule/gamelogs/draft picks
python ingest.py --pdf PATH_TO_PDF --nfl-games

# Playbook (coaches corner, narrative, etc.)
python ingest.py --pdf PATH_TO_PDF --nfl-playbook

# 10-year ATS history
python ingest.py --pdf PATH_TO_PDF --nfl-ats-history

# Draft analysis (grades, first round, steal)
python ingest.py --pdf PATH_TO_PDF --nfl-draft-analysis

# Fix coach names
python ingest.py --pdf PATH_TO_PDF --nfl-coaches
```

### CFB Ingestion
```bash
# All 135 CFB teams stats
python ingest.py --pdf PATH_TO_PDF --cfb-only

# CFB schedules
python ingest.py --pdf PATH_TO_PDF --cfb-games

# CFB stat logs
python ingest.py --pdf PATH_TO_PDF --cfb-gamelogs

# CFB coaches
python ingest.py --pdf PATH_TO_PDF --cfb-coaches

# CFB playbook/trends
python ingest.py --pdf PATH_TO_PDF --cfb-playbook

# CFB 10-year ATS history
python ingest.py --pdf PATH_TO_PDF --cfb-ats-history

# Single CFB team
python ingest.py --pdf PATH_TO_PDF --cfb-ats-history-team "Alabama"
```

---

##  Database Tables

| Table | Description |
|---|---|
| `teams` | 32 NFL + 135 CFB teams |
| `season_stats` | 4-year statistical review |
| `schedule_games` | 2025 schedule with lines |
| `game_logs` | 2024 stat logs |
| `coaches` | Coach info, records, RPR |
| `draft_picks` | 2025 NFL draft picks |
| `sos_stats` | NFL strength of schedule |
| `team_trends` | Good/Bad/Ugly/OU trends |
| `team_playbook` | Narrative, playbook, odds |
| `ats_history` | 10-year ATS history |

---

##  API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/teams?league=NFL` | All teams |
| `GET /api/teams/abbr/{abbr}` | Team by abbreviation |
| `GET /api/stats/season/{team_id}` | Season stats |
| `GET /api/stats/schedule/{team_id}` | Schedule |
| `GET /api/stats/gamelogs/{team_id}` | Stat logs |
| `GET /api/stats/draftpicks/{team_id}` | Draft picks |
| `GET /api/stats/playbook/{team_id}` | Playbook data |
| `GET /api/stats/ats-history/{team_id}` | ATS history |
| `GET /api/coaches/{team_id}` | Coach data |
| `POST /api/chat` | AI chat |

---

##  Features

### NFL Teams
- 4-year statistical review
- 2025 schedule with opening/closing lines
- 2024 stat logs with full box score
- 2025 draft picks + draft grades + first round + steal of draft
- Best & Worst team trends (Good/Bad/Ugly/O-U)
- Coaches Corner, Quarterly Report, Division Data
- Team narrative, stat, power play
- Win totals & playoff odds
- 10-year ATS history (2015-2024)

### CFB Teams
- 4-year stats with recruiting rankings
- Coach RPR, returning starters, recruit rank
- 2025 schedule & 2024 stat logs
- Team theme, narrative, stat, power play
- Marc Lawrence team trends
- 10-year ATS history (2015-2024)

### AI Chat
- Natural language queries about teams
- Powered by Azure OpenAI GPT-4o-mini
- Vector search using pgvector

---

## Environment Variables

```env
DATABASE_URL=postgresql://user:password@localhost:5432/playbook
AZURE_DI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DI_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
SECRET_KEY=your-secret-key
```

---

##  Default Admin

```
Email: admin@playbook.com
Password: admin123
