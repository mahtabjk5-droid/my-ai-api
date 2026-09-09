import os
import secrets
import logging
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from typing import Optional
import uvicorn

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- App Initialize ---
app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- OpenAI Client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-dummy-key-for-testing"))

# --- Models ---
class ChatRequest(BaseModel):
    message: str

# --- In-Memory DB ---
users_db = {}

# --- Helper Functions ---
def generate_api_key():
    return secrets.token_urlsafe(32)

# --- Middleware: API Key Verify ---
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in users_db:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return x_api_key

# --- Usage Tracking ---
def track_usage(api_key: str):
    user = users_db[api_key]
    if user["calls_used"] >= 40:
        raise HTTPException(status_code=402, detail="Payment Required. Limit reached.")
    user["calls_used"] += 1
    return user

# --- Endpoint: Register ---
@app.get("/register")
async def register_user(name: str):
    api_key = generate_api_key()
    users_db[api_key] = {"name": name, "calls_used": 0}
    return {
        "api_key": api_key,
        "name": name,
        "message": "Keep this API Key safe. You have 30 free + 10 bonus calls (Total 40)."
    }

# --- Endpoint: Chat ---
@app.post("/chat")
async def chat(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    user = track_usage(api_key)
    
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a helpful assistant. The user's name is {user['name']}."},
                {"role": "user", "content": request.message}
            ],
            max_tokens=150,
            temperature=0.7
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI error: {str(e)}")
        reply = f"Hello {user['name']}! I'm currently experiencing technical issues. Please try again later."
    
    free_remaining = max(0, 30 - user["calls_used"])
    bonus_used = max(0, user["calls_used"] - 30)
    bonus_remaining = max(0, 10 - bonus_used)
    total_remaining = free_remaining + bonus_remaining
    
    return {
        "reply": reply,
        "usage": {
            "calls_used": user["calls_used"],
            "free_remaining": free_remaining,
            "bonus_remaining": bonus_remaining,
            "total_remaining": total_remaining
        }
    }

# --- Endpoint: Usage ---
@app.get("/usage")
async def get_usage(api_key: str = Depends(verify_api_key)):
    user = users_db[api_key]
    calls_used = user["calls_used"]
    free_remaining = max(0, 30 - calls_used)
    bonus_used = max(0, calls_used - 30)
    bonus_remaining = max(0, 10 - bonus_used)
    total_remaining = free_remaining + bonus_remaining
    
    return {
        "api_key": api_key[:8] + "...",
        "name": user["name"],
        "calls_used": calls_used,
        "free_remaining": free_remaining,
        "bonus_remaining": bonus_remaining,
        "total_remaining": total_remaining,
        "status": "active" if total_remaining > 0 else "payment_required"
    }

# --- Endpoint: Root ---
@app.get("/")
async def root():
    return {"message": "Mahtab AI API is running.", "docs": "/docs", "register": "/register?name=YourName"}

# --- Run ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)