import secrets
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel

# --- App Initialize ---
app = FastAPI()

# --- Models ---
class ChatRequest(BaseModel):
    message: str

# --- In-Memory DB ---
users_db = {}

def generate_api_key():
    """Naya API Key generate karo (32 bytes safe token)"""
    return secrets.token_urlsafe(32)

# --- Middleware: API Key Verify ---
async def verify_api_key(x_api_key: str = Header(...)):
    """Middleware: Header mein X-API-Key check karo. Agar invalid toh 403 error."""
    if x_api_key not in users_db:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return x_api_key  # Agar key sahi hai toh wapas bhejo

# --- Usage Tracking ---
def track_usage(api_key: str):
    """Usage track karo aur limit check karo (30 calls)"""
    user = users_db[api_key]
    if user["calls_used"] >= 30:
        raise HTTPException(
            status_code=402,
            detail="Payment Required. You have used all 30 free calls. Please upgrade."
        )
    user["calls_used"] += 1
    return user

# --- Endpoint 1: Register (Get API Key) ---
@app.get("/register")
async def register_user(name: str):
    """Register karo aur naya API Key lo. Example: GET /register?name=Mahtab"""
    api_key = generate_api_key()
    users_db[api_key] = {
        "name": name,
        "calls_used": 0
    }
    return {
        "api_key": api_key,
        "name": name,
        "message": "Keep this API Key safe. You have 30 free calls."
    }

# --- Endpoint 2: Chat (Main API) ---
@app.post("/chat")
async def chat(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    user = track_usage(api_key)
    # Mock reply (abhi ke liye)
    reply = f"Hello {user['name']}! You sent: {request.message}. This is a mock reply."
    return {
        "reply": reply,
        "usage": {
            "calls_used": user["calls_used"],
            "remaining": 30 - user["calls_used"]
        }
    }

# --- Endpoint 3: Usage Check ---
@app.get("/usage")
async def get_usage(api_key: str = Depends(verify_api_key)):
    """Check karo ke kitni calls bachi hain."""
    user = users_db[api_key]
    remaining = 30 - user["calls_used"]
    return {
        "api_key": api_key[:8] + "...",  # Security: Sirf pehle 8 chars
        "calls_used": user["calls_used"],
        "calls_limit": 30,
        "remaining_calls": remaining,
        "status": "active" if remaining > 0 else "payment_required"
    }

# --- Endpoint 4: Root Check ---
@app.get("/")
async def root():
    return {"message": "AI API is running. Use /register to get your API Key."}

# --- Run (Direct) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)