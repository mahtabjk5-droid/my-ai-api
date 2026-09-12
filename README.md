# AI Revenue API

A professional FastAPI project designed as a clean SaaS-style AI API starter for monetization, onboarding, and usage tracking.

## What was fixed

The original project had several issues:

- weak input validation
- inconsistent API design
- no structured response models
- ambiguous usage tracking logic
- no professional project documentation

This version upgrades the app into a more polished, business-ready backend with:

- secure API key-based authentication
- validated request models
- structured response schemas
- usage tracking with free and bonus calls
- health, plans, and docs endpoints
- industry-style project organization

## Features

- `POST /register` - create a new API key
- `GET /register` - register with a query parameter
- `POST /chat` - send a message using the API key
- `GET /usage` - check remaining quota
- `GET /plans` - view pricing plan options
- `GET /health` - API health check
- `GET /docs` - interactive FastAPI docs
- `POST /billing/upgrade` - upgrade user plan and payment status
- `GET /admin` - admin dashboard for users and stats
- real OpenAI-powered AI replies when `OPENAI_API_KEY` is configured

## Setup

1. Create a virtual environment
2. Install dependencies
3. Start the API

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Environment variables

Create a `.env` file in the project root if you want to enable real AI responses and custom settings:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
ADMIN_KEY=your-admin-secret
HOST=0.0.0.0
PORT=8000
MAX_MESSAGE_LENGTH=2000
```

If `OPENAI_API_KEY` is not set, the app falls back to a polished mock AI reply.

## Example usage

Register a user:

```bash
curl "http://localhost:8000/register?name=John"
```

Chat with the API:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from the AI Revenue API"}'
```

Check usage:

```bash
curl -H "X-API-Key: YOUR_API_KEY" "http://localhost:8000/usage"
```

## Notes

This is a strong, polished starter project that can be extended with:

- real AI model integration (now enabled via environment variables)
- Stripe or Razorpay billing
- admin dashboard
- analytics and logs
- deployment to cloud platforms

## Project status

The codebase has been validated with Python syntax checks and dependency verification in the current workspace.
