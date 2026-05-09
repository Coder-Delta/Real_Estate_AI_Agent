# Aria Real Estate AI Sales Assistant

Aria is a small full-stack AI assistant for qualifying real-estate leads. It combines a FastAPI backend, a Streamlit chat frontend, optional Gemini-powered responses, and a local fallback flow so the assistant can still respond when the LLM is disabled or unavailable.

## What It Does

- Runs a chat-based real-estate intake assistant
- Qualifies buyer and seller leads
- Tracks lead details such as intent, location, budget, timeline, email, and phone
- Falls back to local rule-based logic when Gemini is disabled or fails
- Stores completed leads in CSV
- Stores conversation history in JSON
- Can send email notifications for completed leads

## Tech Stack

- Python
- FastAPI
- Streamlit
- Gemini API via `google-generativeai`
- SMTP for notifications

## Project Layout

```text
Real_Estate_AI_Agent/
├── README.md
└── ai-agent/
    ├── .env
    ├── .env.example
    ├── .gitignore
    ├── Procfile
    ├── render.yaml
    ├── runtime.txt
    ├── backend/
    │   ├── booking.py
    │   ├── emailer.py
    │   ├── llm.py
    │   ├── logic.py
    │   └── main.py
    ├── frontend/
    │   └── app.py
    ├── utils/
    │   ├── config.py
    │   └── sheets.py
    └── data/
        └── conversations.json
```

## How It Works

1. The Streamlit frontend sends the conversation to the FastAPI backend.
2. The backend tries Gemini first when `ENABLE_GEMINI=true`.
3. If Gemini is disabled, unavailable, or returns an invalid result, the backend uses local qualification logic.
4. When the lead is complete enough, the backend marks it as `completed`.
5. Completed leads are written to `ai-agent/data/leads.csv`.
6. Conversation history is written to `ai-agent/data/conversations.json`.

## Configuration

The app currently loads configuration from `ai-agent/.env`.

Create your local config:

```bash
cd ai-agent
cp .env.example .env
```

Example:

```env
BACKEND_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:8501

ENABLE_GEMINI=true
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3-flash-preview
GEMINI_TIMEOUT_SECONDS=30

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=sales@example.com
```

## Local Setup

1. Create a virtual environment:

```bash
cd ai-agent
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install fastapi uvicorn streamlit requests pydantic python-dotenv google-generativeai
```

3. Create the `.env` file from `.env.example`.

4. Start the backend:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

5. In a second terminal, start the frontend:

```bash
cd ai-agent
source .venv/bin/activate
streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

6. Open:

```text
http://127.0.0.1:8501
```

## API Endpoints

### `GET /health`

Basic health check:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### `POST /chat`

Send a conversation to the assistant:

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

Example response:

```json
{
  "status": "ongoing",
  "intent": "buy",
  "name": null,
  "budget": null,
  "location": "Miami",
  "timeline": null,
  "email": null,
  "phone": null,
  "preferred_contact_method": null,
  "preferred_contact_time": null,
  "action": "none",
  "reply": "That sounds exciting. Which area are you hoping to focus on?"
}
```

## Lead Output

Completed leads are saved to:

```text
ai-agent/data/leads.csv
```

Conversation history is saved to:

```text
ai-agent/data/conversations.json
```

## Notes For Developers

- The backend entrypoint is `ai-agent/backend/main.py`.
- Gemini integration lives in `ai-agent/backend/llm.py`.
- Local fallback logic lives in `ai-agent/backend/logic.py`.
- Frontend UI lives in `ai-agent/frontend/app.py`.
- Settings are loaded from `ai-agent/.env` by `ai-agent/utils/config.py`.

## Current Limitations

- The repository currently references `requirements.txt` in `render.yaml`, but that file is not present in the repo.
- The current backend exposes `/health` and `/chat` only.
- The existing code includes email support, but not a live SMS webhook endpoint.

## License

No license is currently defined in this repository.
