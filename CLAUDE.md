# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
# Start database
docker compose up -d

# Install dependencies (from backend/)
pip install -r requirements.txt

# Run dev server (port 8007)
cd backend
.venv/bin/uvicorn main:app --reload --port 8007
```

### Frontend

```bash
# Install and run dev server (port 5179)
cd frontend
npm install
npm run dev

# Production build (outputs to frontend/dist/)
npm run build
```

### Database

```bash
docker compose down        # stop (data persists in pgdata volume)
docker compose down -v     # stop and delete volume
```

There are no automated tests. The DB schema is created automatically by SQLAlchemy on first backend startup via `init_db()` in `database.py`.

## Architecture

Single-user web app that imports Azure DevOps time-tracking CSVs into PostgreSQL and generates styled Excel/PDF reports sent via SMTP.

**Request flow:**
1. Frontend (Vue 3, port 5179) proxies all `/api/*` requests to the FastAPI backend (port 8007).
2. All endpoints except `/api/auth/login` require `Authorization: Bearer <JWT>` — tokens are valid for 8 hours and signed with `SECRET_KEY`.
3. The backend stores data in two tables: `time_entries` (imported CSV rows) and `email_logs` (send audit trail).

**Key backend modules:**
- `main.py` — all FastAPI routes and business logic (CSV parsing, summary aggregation)
- `auth.py` — bcrypt + python-jose JWT; user/password loaded from `.env` at startup; password hashed once on process start
- `database.py` — SQLAlchemy async engine, `TimeEntry` and `EmailLog` ORM models, `init_db()` lifespan hook
- `email_service.py` — builds the full HTML email (with inline logo CID), attaches Excel/PDF, sends via aiosmtplib STARTTLS
- `report_generator.py` — `build_excel()` (three sheets: Resumen, Por Día pivot, Detalle) and `build_pdf()` (landscape A4 via ReportLab); both accept `(date_from, date_to, rows, summary)` and return `bytes`

**Frontend components (`frontend/src/`):**
- `App.vue` — shell: checks `localStorage` for token, mounts `Login` or `Dashboard`
- `Login.vue` — posts form to `/api/auth/login`, emits `login` event with token
- `Dashboard.vue` — tabs (month selector vs. free date range), Chart.js graphs, email send modal

## Environment Setup

Copy `backend/.env.example` to `backend/.env`. Required variables:

| Variable | Notes |
|----------|-------|
| `DATABASE_URL` | Use port `5434` when running via Docker Compose |
| `APP_USER` / `APP_PASSWORD` | Single-user credentials for the web login |
| `SECRET_KEY` | JWT signing key — change from default in production |
| `SMTP_HOST/PORT/USER/PASSWORD/FROM` | Gmail: use an App Password (not account password) |

## CSV Import

Drop Azure DevOps CSV exports into `reportes_mensuales/` (gitignored). File names must follow the pattern `{mes_español}-{año}.csv` (e.g. `marzo-2026.csv`). The filename determines the `report_month` key stored in the DB. Re-importing a month deletes previous rows for that month and reloads from file.

## Extending the Model

To add a column to `TimeEntry`:
1. Add `Mapped[...]` field in `database.py`
2. Read the new column in `parse_csv_file()` in `main.py`
3. Expose it in `entry_to_dict()` in `main.py`
4. Recreate the table (drop Docker volume or use Alembic migrations)
