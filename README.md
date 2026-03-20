# DBMS-IATRS

ATS backend with Flask + MySQL and a static frontend dashboard.

## Project Structure

```text
DBMS-IATRS/
|- ats_api/              # Flask app package (factory, routes, config, db helpers)
|- frontend/             # Static HTML pages
|- app.py                # Application entrypoint
|- setup_mysql.py        # Creates DB, applies schema, seeds data
|- schema.sql            # MySQL schema
|- requirements.txt      # Runtime dependencies
|- .env.example          # Environment template
```

## Prerequisites

- Python 3.10+ (recommended)
- MySQL server running locally or remotely

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` from `.env.example` and set DB credentials.
4. Initialize DB schema and seed data:
   ```bash
   python setup_mysql.py
   ```

## Run

Start API server:

```bash
python app.py
```

Default API URL: `http://127.0.0.1:5000`

Serve frontend (optional, from `frontend/`):

```bash
python -m http.server 8080
```

Frontend URL: `http://127.0.0.1:8080`

## API Endpoints

- `GET /`
- `GET /health`
- `GET /jobs`
- `GET /jobs?status=Open|Closed|Paused`
- `GET /jobs/<job_id>`
- `POST /jobs`
- `POST /apply`
- `GET /applications`

## Request Examples

Create job:

```json
{
  "title": "Backend Engineer",
  "department": "Engineering",
  "location": "Remote",
  "recruiter_id": 1,
  "status": "Open"
}
```

Apply for a job:

```json
{
  "candidate_id": 1,
  "job_id": 1
}
```
