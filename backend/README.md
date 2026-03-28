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

## Deploy On Render

You can deploy this backend in two ways.

### Option 1: Using `render.yaml` (recommended)

1. Push this repository to GitHub.
2. In Render, click **New** -> **Blueprint**.
3. Select this GitHub repo.
4. Render reads `render.yaml` and creates the web service automatically.

Render uses:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn --chdir backend app:app`
- Health check path: `/health`

### Option 2: Manual Web Service Setup

If you do not use Blueprint:

1. In Render, click **New** -> **Web Service**.
2. Connect this GitHub repo.
3. Set:

- Environment: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --chdir backend app:app`

4. Add environment variables in Render:

- `FLASK_ENV=production`
- `SECRET_KEY=<strong-random-secret>`
- `DATABASE_URL=<your-postgres-url>`
- `GOOGLE_CLIENT_ID=<optional-if-using-google-login>`
- `GOOGLE_CLIENT_SECRET=<optional-if-using-google-login>`
- `RESEND_API_KEY=<optional-if-using-email-otp>`
- `RESEND_FROM_EMAIL=<optional-if-using-email-otp>`

5. Deploy and test:

- `https://your-service-name.onrender.com/health`

### Common Issues

- If deployment fails with missing modules, confirm `requirements.txt` is at repository root.
- If DB connection fails, verify `DATABASE_URL` is set correctly in Render environment variables.
- First request on free tier can be slow due to cold start.
