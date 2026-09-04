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
    return x_api_key

# --- Usage Tracking (30 Free + 10 Bonus = 40 Total) ---
def track_usage(api_key: str):
    """Usage track karo aur limit check karo (30 free + 10 bonus calls)"""
    user = users_db[api_key]
    
    # Agar 40 calls ho chuki hain (30 free + 10 bonus), toh 402 error do.
    if user["calls_used"] >= 40:
        raise HTTPException(
            status_code=402,
            detail="Payment Required. You have used all 30 free calls and 10 bonus calls. Please upgrade."
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
        "message": "Keep this API Key safe. You have 30 free calls + 10 bonus calls (Total 40)."
    }

# --- Endpoint 2: Chat (Main API) ---
@app.post("/chat")
async def chat(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    user = track_usage(api_key)
    
    # Mock reply
    reply = f"Hello {user['name']}! You sent: {request.message}. This is a mock reply."
    
    # --- Bonus Calculation Logic ---
    calls_used = user["calls_used"]
    free_remaining = max(0, 30 - calls_used)          # Abhi kitni free calls bachi hain?
    bonus_used = max(0, calls_used - 30)              # Kitni bonus calls use ho chuki hain?
    bonus_remaining = max(0, 10 - bonus_used)         # Kitni bonus calls bachi hain?
    total_remaining = free_remaining + bonus_remaining # Total remaining calls

    return {
        "reply": reply,
        "usage": {
            "calls_used": calls_used,
            "free_remaining": free_remaining,
            "bonus_remaining": bonus_remaining,
            "total_remaining": total_remaining
        }
    }

# --- Endpoint 3: Usage Check ---
@app.get("/usage")
async def get_usage(api_key: str = Depends(verify_api_key)):
    """Check karo ke kitni calls bachi hain (Free + Bonus)."""
    user = users_db[api_key]
    calls_used = user["calls_used"]
    
    free_remaining = max(0, 30 - calls_used)
    bonus_used = max(0, calls_used - 30)
    bonus_remaining = max(0, 10 - bonus_used)
    total_remaining = free_remaining + bonus_remaining
    
    return {
        "api_key": api_key[:8] + "...",
        "calls_used": calls_used,
        "free_remaining": free_remaining,
        "bonus_remaining": bonus_remaining,
        "total_remaining": total_remaining,
        "status": "active" if total_remaining > 0 else "payment_required"
    }

# --- Endpoint 4: Root Check ---
@app.get("/")
async def root():
    return {"message": "AI API is running. Use /register to get your API Key."}

# --- Run (Direct) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)