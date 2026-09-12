from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

DB_PATH = Path(__file__).with_name("ai_api.db")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
ADMIN_KEY = os.getenv("ADMIN_KEY", "admin-secret-key")
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "2000"))

PLANS = {
    "starter": {
        "name": "Starter",
        "free_calls": 30,
        "bonus_calls": 10,
        "total_calls": 40,
        "price": "$10/month",
    },
    "pro": {
        "name": "Pro",
        "free_calls": 500,
        "bonus_calls": 150,
        "total_calls": 650,
        "price": "$49/month",
    },
    "enterprise": {
        "name": "Enterprise",
        "free_calls": 2000,
        "bonus_calls": 500,
        "total_calls": 2500,
        "price": "Custom",
    },
}

app = FastAPI(
    title="AI Revenue API",
    version="2.0.0",
    description=(
        "A production-ready AI monetization API with SQLite persistence, billing-ready plans, "
        "usage tracking, and admin analytics."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)


class UpgradeRequest(BaseModel):
    plan: str = Field(..., description="Plan to upgrade to: starter, pro, or enterprise")
    payment_status: str = Field(default="paid", description="Payment status, typically paid or trial")


class UsageReport(BaseModel):
    plan: str
    payment_status: str
    calls_used: int
    free_remaining: int
    bonus_remaining: int
    total_remaining: int
    status: str


class RegisterResponse(BaseModel):
    api_key: str
    name: str
    plan: str
    message: str
    usage_plan: dict[str, Any]


class ChatResponse(BaseModel):
    reply: str
    usage: UsageReport


class UserSummary(BaseModel):
    id: int
    name: str
    api_key: str
    plan: str
    payment_status: str
    calls_used: int
    created_at: str


class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_calls_used: int
    plan_breakdown: dict[str, int]


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.on_event("startup")
def startup_event() -> None:
    init_db()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                api_key TEXT NOT NULL UNIQUE,
                plan TEXT NOT NULL DEFAULT 'starter',
                payment_status TEXT NOT NULL DEFAULT 'trial',
                calls_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_plan ON users(plan)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_logs_api_key ON usage_logs(api_key)"
        )
        conn.commit()


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def normalize_name(name: str) -> str:
    cleaned_name = name.strip()
    if len(cleaned_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must be at least 2 characters long.",
        )
    return cleaned_name


def get_plan(plan_name: str) -> dict[str, Any]:
    normalized = plan_name.lower()
    if normalized not in PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported plan '{plan_name}'. Supported plans: {', '.join(PLANS.keys())}",
        )
    return PLANS[normalized]


def fetch_user(api_key: str) -> dict[str, Any] | None:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE api_key = ?",
            (api_key,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def build_usage_report(user: dict[str, Any]) -> UsageReport:
    plan = get_plan(user["plan"])
    calls_used = int(user["calls_used"])

    free_remaining = max(0, plan["free_calls"] - calls_used)
    bonus_used = max(0, calls_used - plan["free_calls"])
    bonus_remaining = max(0, plan["bonus_calls"] - bonus_used)
    total_remaining = free_remaining + bonus_remaining

    return UsageReport(
        plan=user["plan"],
        payment_status=user["payment_status"],
        calls_used=calls_used,
        free_remaining=free_remaining,
        bonus_remaining=bonus_remaining,
        total_remaining=total_remaining,
        status="active" if total_remaining > 0 else "payment_required",
    )


def create_user_entry(name: str) -> dict[str, Any]:
    normalized_name = normalize_name(name)
    api_key = generate_api_key()
    now = now_iso()
    plan = get_plan("starter")

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (name, api_key, plan, payment_status, calls_used, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_name,
                api_key,
                "starter",
                "trial",
                0,
                now,
                now,
            ),
        )
        conn.commit()

    return {
        "api_key": api_key,
        "name": normalized_name,
        "plan": "starter",
        "message": (
            f"Your API key has been created successfully. You receive {plan['free_calls']} free calls "
            f"and {plan['bonus_calls']} bonus calls for a total of {plan['total_calls']} calls."
        ),
        "usage_plan": {
            "plan": "starter",
            "free_calls": plan["free_calls"],
            "bonus_calls": plan["bonus_calls"],
            "total_calls": plan["total_calls"],
            "currency": "USD",
            "pricing": plan["price"],
        },
    }


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )

    user = fetch_user(x_api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )
    return x_api_key


async def verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> str:
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Admin-Key header.",
        )
    return x_admin_key


def track_usage(api_key: str) -> dict[str, Any]:
    user = fetch_user(api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is not registered.",
        )

    plan = get_plan(user["plan"])

    if user["calls_used"] >= plan["total_calls"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Payment required. You have used all {plan['free_calls']} free calls and {plan['bonus_calls']} bonus calls on the {user['plan']} plan."
            ),
        )

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE users SET calls_used = calls_used + 1, updated_at = ? WHERE api_key = ?",
            (now_iso(), api_key),
        )
        conn.commit()

    user["calls_used"] += 1
    return user


@app.get("/", tags=["General"])
async def root() -> dict[str, Any]:
    return {
        "name": app.title,
        "version": app.version,
        "message": "AI Revenue API is running successfully.",
        "docs": "/docs",
        "register": "/register",
        "chat": "/chat",
        "usage": "/usage",
        "plans": "/plans",
        "admin": "/admin",
    }


@app.get("/health", tags=["General"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": app.title}


@app.get("/plans", tags=["General"])
async def plans() -> dict[str, Any]:
    return {
        "plans": [
            {
                "name": plan_name,
                **plan_details,
            }
            for plan_name, plan_details in PLANS.items()
        ]
    }


@app.post("/register", response_model=RegisterResponse, tags=["Auth"])
async def register_user(payload: RegisterRequest) -> RegisterResponse:
    result = create_user_entry(payload.name)
    return RegisterResponse(**result)


@app.get("/register", response_model=RegisterResponse, tags=["Auth"])
async def register_user_get(name: str) -> RegisterResponse:
    result = create_user_entry(name)
    return RegisterResponse(**result)


@app.post("/chat", response_model=ChatResponse, tags=["AI"])
async def chat(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key),
) -> ChatResponse:
    user = track_usage(api_key)

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO usage_logs (api_key, message, created_at) VALUES (?, ?, ?)",
            (api_key, request.message, now_iso()),
        )
        conn.commit()

    reply = (
        f"Hello {user['name']}! You sent: {request.message}. "
        "This is a professional AI reply generated by your monetized API backend."
    )

    usage = build_usage_report(user)

    return ChatResponse(
        reply=reply,
        usage=usage,
    )


@app.get("/usage", response_model=UsageReport, tags=["Usage"])
async def get_usage(api_key: str = Depends(verify_api_key)) -> UsageReport:
    user = fetch_user(api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is not registered.",
        )
    return build_usage_report(user)


@app.post("/billing/upgrade", tags=["Billing"])
async def upgrade_plan(
    payload: UpgradeRequest,
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    plan = get_plan(payload.plan)

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE users SET plan = ?, payment_status = ?, updated_at = ? WHERE api_key = ?",
            (payload.plan.lower(), payload.payment_status.lower(), now_iso(), api_key),
        )
        conn.commit()

    user = fetch_user(api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh user data after upgrade.",
        )

    return {
        "message": f"Plan successfully upgraded to {plan['name']}.",
        "user": {
            "name": user["name"],
            "plan": user["plan"],
            "payment_status": user["payment_status"],
        },
        "usage": build_usage_report(user),
    }


@app.get("/admin", response_class=HTMLResponse, tags=["Admin"])
async def admin_dashboard(x_admin_key: str = Depends(verify_admin_key)) -> HTMLResponse:
    stats = get_admin_stats()
    users = get_all_users()

    rows = "".join(
        f"<tr><td>{u['id']}</td><td>{u['name']}</td><td>{u['api_key'][:8]}...</td><td>{u['plan']}</td><td>{u['payment_status']}</td><td>{u['calls_used']}</td></tr>"
        for u in users
    )

    html = f"""
    <html>
      <head>
        <title>AI Revenue API Admin</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 40px; background: #f6f8fb; color: #1d2430; }}
          .card {{ background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 24px rgba(0,0,0,0.05); margin-bottom: 20px; }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }}
          .metric {{ background: #eef4ff; border-radius: 12px; padding: 18px; }}
          table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
          th, td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }}
          th {{ background: #f1f5f9; }}
        </style>
      </head>
      <body>
        <div class="card">
          <h1>AI Revenue API Admin Dashboard</h1>
          <p>Professional operating view for user growth, plan performance, and billing readiness.</p>
        </div>

        <div class="grid">
          <div class="card metric">
            <h3>Total Users</h3>
            <h2>{stats['total_users']}</h2>
          </div>
          <div class="card metric">
            <h3>Active Users</h3>
            <h2>{stats['active_users']}</h2>
          </div>
          <div class="card metric">
            <h3>Total Calls Used</h3>
            <h2>{stats['total_calls_used']}</h2>
          </div>
        </div>

        <div class="card">
          <h2>Plan Breakdown</h2>
          <ul>
            <li>Starter: {stats['plan_breakdown'].get('starter', 0)}</li>
            <li>Pro: {stats['plan_breakdown'].get('pro', 0)}</li>
            <li>Enterprise: {stats['plan_breakdown'].get('enterprise', 0)}</li>
          </ul>
        </div>

        <div class="card">
          <h2>Users</h2>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>API Key</th>
                <th>Plan</th>
                <th>Payment</th>
                <th>Calls Used</th>
              </tr>
            </thead>
            <tbody>
              {rows}
            </tbody>
          </table>
        </div>
      </body>
    </html>
    """

    return HTMLResponse(content=html)


@app.get("/admin/stats", tags=["Admin"])
async def admin_stats(x_admin_key: str = Depends(verify_admin_key)) -> AdminStats:
    stats = get_admin_stats()
    return AdminStats(**stats)


@app.get("/admin/users", tags=["Admin"])
async def admin_users(x_admin_key: str = Depends(verify_admin_key)) -> list[UserSummary]:
    users = get_all_users()
    return [UserSummary(**user) for user in users]


def get_admin_stats() -> dict[str, Any]:
    with get_db_connection() as conn:
        total_users_row = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()
        active_row = conn.execute(
            "SELECT COUNT(*) as count FROM users WHERE calls_used > 0"
        ).fetchone()
        total_calls_row = conn.execute(
            "SELECT COALESCE(SUM(calls_used), 0) as total FROM users"
        ).fetchone()
        plan_rows = conn.execute(
            "SELECT plan, COUNT(*) as count FROM users GROUP BY plan"
        ).fetchall()

    stats = {
        "total_users": int(total_users_row["count"]),
        "active_users": int(active_row["count"]),
        "total_calls_used": int(total_calls_row["total"]),
        "plan_breakdown": {"starter": 0, "pro": 0, "enterprise": 0},
    }

    for row in plan_rows:
        stats["plan_breakdown"][row["plan"]] = int(row["count"])

    return stats


def get_all_users() -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
