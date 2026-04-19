# Aria Real Estate AI Sales Assistant

Aria is a simple real-estate lead qualification assistant with a FastAPI backend and a Streamlit frontend. It can run with Gemini for dynamic responses, and it also includes a local fallback flow so the chat remains usable if the model is slow or unavailable.

## Features

- Streamlit chat interface for real-estate conversations
- FastAPI backend with `/health` and `/chat` endpoints
- Gemini-powered assistant responses
- Local fallback assistant logic for better reliability
- Lead capture with name, budget, location, timeline, and intent
- Automatic lead persistence to CSV
- Optional email notification for completed leads
- Suggested meeting date for qualified buy/sell leads

## Project Structure

```text
Agent_tutorial/
├── README.md
└── ai-agent/
    ├── .env.example
    ├── requirements.txt
    ├── backend/
    │   ├── main.py
    │   ├── llm.py
    │   ├── logic.py
    │   ├── emailer.py
    │   └── booking.py
    ├── frontend/
    │   └── app.py
    ├── utils/
    │   ├── config.py
    │   └── sheets.py
    └── data/
        └── leads.csv
```

## Requirements

- Python 3.13+ recommended
- A Gemini API key if you want LLM responses
- Optional SMTP credentials for email alerts

## Setup

1. Move into the app directory:

```bash
cd ai-agent
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create your environment file:

```bash
cp .env.example .env
```

5. Edit `.env` and fill in your values.

## Environment Variables

Example configuration:

```env
BACKEND_URL=http://127.0.0.1:8000
CORS_ORIGINS=http://localhost:8501

ENABLE_GEMINI=true
GEMINI_API_KEY=your_real_gemini_api_key
GEMINI_MODEL=gemini-3-flash-preview
GEMINI_TIMEOUT_SECONDS=30

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=sales@example.com
```

Notes:

- Set `ENABLE_GEMINI=false` to force the local assistant flow.
- `GEMINI_TIMEOUT_SECONDS` is optional. Default is `30`.
- If Gemini fails or times out, the backend falls back to local logic instead of breaking the chat.

## Run The App

1. Navigate to the app directory and activate the virtual environment:

```bash
cd ai-agent
source .venv/bin/activate
```

2. Start the backend in one terminal:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

3. Start the frontend in another terminal:

```bash
streamlit run frontend/app.py --server.headless true --server.address 127.0.0.1 --server.port 8501
```

4. Open the app in your browser:

```text
http://127.0.0.1:8501
```

### Optional: Force local assistant logic only

If you want to disable Gemini and use only the local fallback:

```bash
ENABLE_GEMINI=false uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## API

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

### Chat

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "assistant", "content": "Hi, it is lovely to connect."},
      {"role": "user", "content": "I want to buy an apartment in Miami."}
    ]
  }'
```

Typical response shape:

```json
{
  "status": "ongoing",
  "intent": "buy",
  "name": null,
  "budget": null,
  "location": "Miami",
  "timeline": null,
  "action": "none",
  "reply": "That sounds exciting. Which area are you hoping to focus on?"
}
```

## Lead Storage

Completed leads are appended to:

```text
ai-agent/data/leads.csv
```

All conversation history is stored in:

```text
ai-agent/data/conversations.json
```

The CSV includes:

- `intent`
- `name`
- `budget`
- `location`
- `timeline`
- `status`
- `action`
- `lead_summary`
- `suggested_meeting_date`
- `reply`
- `transcript`

## How It Works

1. The Streamlit frontend sends the full chat history to the backend.
2. The backend tries Gemini first when enabled.
3. If Gemini is unavailable, invalid, or times out, the backend falls back to local qualification logic.
4. When a lead is sufficiently qualified, the backend marks it as completed.
5. Completed leads are saved to CSV and can optionally trigger an email notification.

## Troubleshooting

### Port already in use

If `8000` is already busy, either stop the old process or run the backend on another port:

```bash
/home/zedx/Codes/Agent_tutorial/ai-agent/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

If you change the backend port, also update `BACKEND_URL` in `.env`.

### Gemini request failed

Check these first:

- `GEMINI_API_KEY` is real and active
- `GEMINI_MODEL` is valid for your account
- your internet connection is working
- the timeout is high enough for your network

The backend logs Gemini errors in the terminal. If Gemini fails, the app should still answer using the local fallback logic.

### Frontend cannot reach backend

Make sure:

- the backend is running
- `BACKEND_URL` in `.env` matches the backend port
- both services were restarted after `.env` changes

## Development Notes

- Backend entrypoint: [ai-agent/backend/main.py](/home/zedx/Codes/Agent_tutorial/ai-agent/backend/main.py)
- Gemini integration: [ai-agent/backend/llm.py](/home/zedx/Codes/Agent_tutorial/ai-agent/backend/llm.py)
- Local assistant logic: [ai-agent/backend/logic.py](/home/zedx/Codes/Agent_tutorial/ai-agent/backend/logic.py)
- Frontend UI: [ai-agent/frontend/app.py](/home/zedx/Codes/Agent_tutorial/ai-agent/frontend/app.py)

## License

Add your preferred license here.
