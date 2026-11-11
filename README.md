# AIRWISE 360°

India-oriented air-quality intelligence dashboard.

## Local setup

### Backend (from project root)
1. Create and activate a Python virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add a valid `OPENAQ_API_KEY`.
4. Start the API: `uvicorn backend.main:app --reload`
5. API docs: `http://127.0.0.1:8000/docs`

### Frontend
1. Open a second terminal: `cd frontend`
2. Install dependencies: `npm ci`
3. Copy `.env.example` to `.env` and set `VITE_API_BASE_URL=http://127.0.0.1:8000`
4. Start: `npm run dev`

## Historical station ingestion
In Swagger, call:
`POST /api/india/stations/openaq/{station_id}/ingest?hours=36`
Then call:
`GET /api/india/stations/openaq/{station_id}/aqi`

Ingestion only stores observations actually returned by OpenAQ. CPCB-methodology AQI remains unavailable until valid hourly observations, compatible units, averaging periods and pollutant coverage meet the calculation requirements. This is not an official CPCB-reported AQI.

## Deployment outline
- Deploy the FastAPI backend using the root `render.yaml`.
- Set `OPENAQ_API_KEY` and `AIRWISE_CORS_ORIGINS` in the backend hosting dashboard.
- Deploy `frontend` as a Vercel project. Set `VITE_API_BASE_URL` to the deployed backend URL.
- Do not commit `.env` files or API keys.

## Data and model transparency
OpenAQ station coverage varies by location and pollutant. A station selector can only offer locations present in the configured station registry. Model forecasts are estimates, not ground observations. Do not claim a fixed national training-data volume unless the dataset is actually ingested, counted, quality-checked and used in a reproducible training run.
