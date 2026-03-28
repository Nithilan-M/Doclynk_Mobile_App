# DocLynk Backend

This folder contains the Python/Flask backend for DocLynk.

## Contents

- `app.py` - Flask app entry point
- `api_routes.py` - API endpoints
- `db_config.py` - Database connection helper
- `security.py` - Auth and security helpers
- `email_service.py` - OTP and email helpers
- `check_tables.py` - DB schema check utility
- `test_db.py` - Database connectivity test utility

## Prerequisites

- Python 3.10+
- A virtual environment (recommended)
- PostgreSQL database URL in environment variables

## Environment Variables

Set these in the project `.env` file (one level above this folder):

- `DATABASE_URL` - PostgreSQL connection URL
- `SECRET_KEY` - Flask secret key
- `PORT` - API port (optional, default: `5000`)
- `FLASK_ENV` - `development` or `production`

## Run Backend

From project root:

```powershell
python backend/app.py
```

From backend folder:

```powershell
python app.py
```

## Utilities

Test database connection:

```powershell
python backend/test_db.py
```

Check tables/columns in public schema:

```powershell
python backend/check_tables.py
```

## Notes

- The app exposes `/health` for health checks.
- API routes are registered under `/api`.
