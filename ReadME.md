# Abel

Abel is a job discovery application. Search by keyword, location, experience level, employment type, remote preference, and posting date. Standard mode queries built-in sources; custom mode connects a user-provided HTTPS JSON API.

## Stack
- FastAPI + Requests backend
- React + Vite frontend

## Local development
Backend: `cd backend && uv sync && uv run uvicorn main:app --reload --port 1011`
Frontend: `cd frontend/Abel && npm install && npm run dev`

Standard mode uses free public APIs from Himalayas and Remote OK; no API key, RapidAPI subscription, or paid plan is required. Set `CORS_ORIGINS` to the frontend origin and `VITE_API_URL` to the backend base URL.

## Default job sources
- [Himalayas](https://himalayas.app): free public remote-jobs API with keyword, country, seniority, and employment-type filters. Abel links to the original listing and credits Himalayas.
- [Remote OK](https://remoteok.com): free public remote-jobs feed. Abel links to each original listing and credits Remote OK.

Public feeds are cached in memory for one hour to reduce unnecessary requests. Provider availability and rate limits can change; Abel reports source warnings instead of silently treating a failed source as an empty search.

## Custom source
Custom endpoints must use HTTPS and return JSON with a top-level list or a list under `jobs`, `results`, `data`, or `items`. Abel passes `query`, `location`, `experience`, `employment_type`, `remote`, and `page` query parameters. Authentication supports `Authorization: Bearer` and `x-api-key`. Custom credentials are sent to the backend for the current request and are not persisted. Private/internal targets are rejected and redirects are disabled.

Never commit real API keys. Revoke and replace any key previously committed to Git history.

## Limitations
The default sources focus on remote roles; they do not provide comprehensive local/on-site job coverage. Experience-level matching is heuristic. Custom APIs must follow the documented query and response contract. Abel links to original application pages; it does not apply on the user's behalf.
