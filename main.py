from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import stripe
import os
from dotenv import load_dotenv

# 1. Load .env file
load_dotenv()

# 2. Initialize FastAPI
app = FastAPI()

# 3. Get Stripe Key from .env (it's there, we checked via cat)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# 4. Root endpoint to check if server is alive
@app.get("/")
def read_root():
    return {"message": "🚀 Server is running! Use POST /create-checkout"}

# 5. The main Multi-Currency Checkout endpoint (Fixed: using @app, not @router)
@app.post("/create-checkout")
async def create_checkout_session(currency: str = "usd"):
    try:
        # Validate currency
        if currency.lower() not in ["usd", "eur", "gbp"]:
            return {"error": "Currency not supported. Use usd, eur, or gbp."}

        # Create Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": currency.lower(),
                    "product_data": {
                        "name": f"AI Query Pack (Pay in {currency.upper()})",
                    },
                    "unit_amount": 999,  # $9.99
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        return {"checkout_url": session.url, "currency": currency}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))