# Aria Real Estate AI Sales Assistant

Aria is a simple real-estate lead qualification assistant with a FastAPI backend and a Streamlit frontend. It can run with Gemini for dynamic responses, and it also includes a local fallback flow so the chat remains usable if the model is slow or unavailable.

## Features

- Streamlit chat interface for real-estate conversations
- FastAPI backend with `/health`, `/chat`, and `/sms` endpoints
- Gemini-powered assistant responses (with local fallback)
- Lead capture with name, budget, location, timeline, and intent
- Automatic lead persistence to CSV
- Optional email notification for completed leads
- SMS webhook integration for incoming Twilio messages
- Suggested meeting date for qualified buy/sell leads

## Project Structure

```text
Agent_tutorial/
├── README.md
└── ai-agent/
    ├── .env                    # Environment variables (create from .env.example)
    ├── .env.example            # Template for environment variables
    ├── requirements.txt        # Python dependencies
    ├── Procfile                # Deployment configuration (Heroku/Render)
    ├── render.yaml             # Render.com deployment config
    ├── runtime.txt             # Python version for deployment
    ├── backend/
    │   ├── main.py             # FastAPI app, /chat and /sms endpoints
    │   ├── llm.py              # Gemini/LLM integration
    │   ├── logic.py            # Conversation state & lead qualification
    │   ├── emailer.py          # Email notifications
    │   └── booking.py          # Meeting date suggestions
    ├── frontend/
    │   └── app.py              # Streamlit chat interface
    ├── utils/
    │   ├── config.py           # Settings loader from .env
    │   └── sheets.py           # Google Sheets integration
    └── data/
        ├── leads.csv           # Completed leads (auto-created)
        ├── conversations.json   # Chat history (auto-created)
        └── leads.json          # Leads backup (optional)
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

## SMS Configuration (Twilio)

To enable SMS support:

1. Get a Twilio account and phone number
2. Set your webhook URL in Twilio console:
   - **Messaging → Phone Numbers → Your Number → Messaging**
   - **Webhook URL:** `https://your-domain:8000/sms`
   - **HTTP Method:** POST
3. When SMS arrives, Twilio sends `From`, `Body`, and `MessageSid`
4. The backend routes the SMS through Gemini (or local fallback)
5. The response is returned as TwiML XML for Twilio to send back

Example SMS conversation:

```
User SMS:  "Hi, I want to buy a house in Miami"
Response:  "That sounds exciting. Which area are you hoping to focus on?"

User SMS:  "Downtown Miami"
Response:  "Got it. What price range feels right for you?"
```

All SMS interactions are logged to `data/conversations.json` with `source: "sms"`.

## Run The App

### Quick Start (2 terminals)

**Terminal 1: Start the backend**

```bash
cd ai-agent
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2: Start the frontend**

```bash
cd ai-agent
source .venv/bin/activate
streamlit run frontend/app.py --server.headless true --server.address 127.0.0.1 --server.port 8501
```

Then open: `http://127.0.0.1:8501`

### With Custom Ports

If `8000` or `8501` are busy, use different ports:

```bash
# Backend on port 8001
uvicorn backend.main:app --host 127.0.0.1 --port 8001

# Frontend on port 8502
streamlit run frontend/app.py --server.port 8502
```

Update `BACKEND_URL` in `.env` to match:

```env
BACKEND_URL=http://127.0.0.1:8001
```

### Disable Gemini (use local fallback only)

```bash
ENABLE_GEMINI=false uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Or edit `.env`:

```env
ENABLE_GEMINI=false
```

## API

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

### Chat Endpoint

Send messages via JSON:

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

### SMS Webhook Endpoint

Receive incoming SMS from Twilio and route to LLM:

```bash
curl -X POST http://127.0.0.1:8000/sms \
  -d 'From=%2B15551234567' \
  -d 'Body=I+want+to+buy+in+Miami' \
  -d 'MessageSid=SM1234567890abcdef' \
  -H "Content-Type: application/x-www-form-urlencoded"
```

Response is Twilio-compatible TwiML XML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>That sounds exciting. Which area are you hoping to focus on?</Message>
</Response>
```

**Configure your Twilio webhook to:**

```text
POST https://your-domain:8000/sms
```

Twilio automatically sends:
- `From`: sender's phone number
- `Body`: message text
- `MessageSid`: unique message identifier


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

1. **Chat requests** come from the Streamlit frontend or `/chat` API endpoint.
2. **SMS requests** come from Twilio and hit the `/sms` webhook.
3. Both are converted to `ChatMessage` objects and sent to the conversation logic.
4. The backend tries Gemini (LLM) first when `ENABLE_GEMINI=true`.
5. If Gemini is unavailable, invalid, or times out, the backend falls back to local qualification logic.
6. When a lead is sufficiently qualified, the backend marks it as `completed`.
7. Completed leads are saved to CSV and can optionally trigger an email notification.
8. SMS responses are returned as Twilio-compatible TwiML XML.

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
