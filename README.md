# FarmShield AI

AI-Powered Precision Agriculture & Farm Risk Intelligence Platform.

## Repository Layout
- `backend/` - FastAPI, SQLAlchemy 2.x, GeoAlchemy2, PostGIS 3.4 Backend Foundation. See [backend/README.md](backend/README.md).
- `docker-compose.yml` - Local PostGIS 16 + 3.4 database service.

## Quick Start
1. Setup Python virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r backend/requirements.txt
   ```
2. Start PostgreSQL + PostGIS via Docker:
   ```powershell
   docker compose up -d db
   ```
3. Run backend:
   ```powershell
   .venv\Scripts\uvicorn.exe app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
   ```
4. Access API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
