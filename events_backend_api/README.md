# events_backend_api (FastAPI)

## Environment variables

Required (set in `.env` by orchestrator/deployment):

- `DATABASE_URL` - e.g. `postgresql+psycopg://user:pass@host:5432/db`
- `JWT_SECRET` - secret used to sign JWTs

Already present in this template `.env` (used for CORS/config):

- `ALLOWED_ORIGINS`, `ALLOWED_HEADERS`, `ALLOWED_METHODS`, `CORS_MAX_AGE`

## Run (dev)

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

OpenAPI docs: `GET /docs`
Health: `GET /healthz`
