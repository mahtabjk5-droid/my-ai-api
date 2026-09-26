# AI Revenue API

A production-style FastAPI backend built as a SaaS starter for AI usage tracking, onboarding, API key authentication, and monetization-ready APIs.

## Overview

This project was designed to transform a basic API into a more polished backend with realistic SaaS patterns. It includes secure authentication, structured responses, rate limiting, and a clean API architecture suitable for portfolio and demo use.

## Features

- User registration with generated API keys
- API key authentication via request headers
- Request validation and structured responses
- Usage tracking with plan-based limits
- Free and premium plan logic
- Health and monitoring endpoints
- Admin-style dashboard access
- OpenAI integration when configured
- Mock fallback responses when no API key is available

## Tech Stack

- Python 3.11+
- FastAPI
- Pydantic
- SQLite
- OpenAI SDK
- Pytest

## Project Structure

```text
my-ai-api/
├── main.py
├── requirements.txt
├── .env.example
├── README.md
├── tests/
└── app/
```

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
ADMIN_KEY=your-admin-secret
HOST=0.0.0.0
PORT=8000
MAX_MESSAGE_LENGTH=2000
```

### 4. Run the application

```bash
python main.py
```

or:

```bash
uvicorn main:app --reload
```

## Example Requests

### Register a user

```bash
curl "http://localhost:8000/register?name=John"
```

### Send a chat request

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from the AI API"}'
```

### Check usage

```bash
curl "http://localhost:8000/usage" \
  -H "X-API-Key: YOUR_API_KEY"
```

## Notes

This project is suitable as a portfolio backend, SaaS starter, or prototype for AI monetization features. It demonstrates production-oriented patterns while remaining easy to extend.

## License

This project is licensed under the MIT License.
