import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.health import router as health_router
from app.api.v1.products import router as products_router
from app.api.v1.policies import router as policies_router
from app.api.v1.agents import router as agents_router
from app.api.v1.requests import router as requests_router
from app.api.v1.audit import router as audit_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.merchants import router as merchants_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.agent_router import router as agent_commerce_router
from app.api.v1.payment_router import router as payment_webhook_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.negotiations import router as negotiations_router
from app.api.v1.transactions import router as transactions_router

# Setup Logging
setup_logging()
logger = logging.getLogger("aveniq.app")

from fastapi.openapi.utils import get_openapi

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AVENIQ - Commerce Passport for AI Agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="AVENIQ - Commerce Passport for AI Agents",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "Enter raw Agent API Key (avq_live_...)"
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# CORS Configuration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

cors_env = os.getenv("CORS_ORIGINS")
if cors_env:
    origins.extend([o.strip() for o in cors_env.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured Error Handling
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP error on {request.method} {request.url.path}: [{exc.status_code}] {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled system error on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )

# Include API v1 Routers
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(products_router, prefix=settings.API_V1_STR)
app.include_router(policies_router, prefix=settings.API_V1_STR)
app.include_router(agents_router, prefix=settings.API_V1_STR)
app.include_router(requests_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(merchants_router, prefix=settings.API_V1_STR)
app.include_router(integrations_router, prefix=settings.API_V1_STR)
app.include_router(agent_commerce_router, prefix=settings.API_V1_STR)
app.include_router(payment_webhook_router, prefix=settings.API_V1_STR)
app.include_router(approvals_router, prefix=settings.API_V1_STR)
app.include_router(negotiations_router, prefix=settings.API_V1_STR)
app.include_router(transactions_router, prefix=settings.API_V1_STR)

def get_agent_passport_manifest():
    merchant_info = {
        "business_name": "AVENIQ Merchant Store",
        "merchant_code": "MERCHANT_PRIMARY",
        "country": "IND",
        "currency": "INR"
    }
    try:
        merchant = MerchantService.get_active_merchant()
        if merchant:
            merchant_info = {
                "business_name": merchant.get("business_name", "AVENIQ Merchant Store"),
                "merchant_code": merchant.get("merchant_code", "MERCHANT_PRIMARY"),
                "country": merchant.get("country", "IND"),
                "currency": merchant.get("currency", "INR")
            }
    except Exception:
        pass

    return {
        "name": "AVENIQ",
        "version": "1.0.0",
        "aveniq_version": "2.0.0",
        "description": "Commerce Passport & Autonomous Purchasing Engine for AI Agents",
        "api_version": "v1",
        "base_url": settings.API_V1_STR,
        "documentation_url": "/docs",
        "merchant": merchant_info,
        "authentication": {
            "type": "Bearer / API Key",
            "header_names": ["Authorization", "X-Agent-API-Key"],
            "format": "Bearer avq_live_<raw_key>",
            "scopes": {
                "read:passport": "Discover merchant passport, rulesets, and system metadata",
                "read:products": "Query product catalog, pricing, and stock inventory",
                "write:proposals": "Submit natural language negotiation requests & counter-offers",
                "write:checkout": "Initiate Razorpay checkout orders and verify payment signatures"
            }
        },
        "supported_authentication": ["Bearer Token", "API Key (x-api-key)", "Cryptographic ECDSA Signature"],
        "endpoints": {
            "base_url": settings.API_V1_STR,
            "product_discovery": f"{settings.API_V1_STR}/products",
            "negotiation": f"{settings.API_V1_STR}/negotiations/start",
            "checkout": f"{settings.API_V1_STR}/checkout/razorpay/create-order",
            "checkout_verify": f"{settings.API_V1_STR}/checkout/razorpay/verify",
            "audit_verify": f"{settings.API_V1_STR}/audit/verify"
        },
        "supported_capabilities": [
            "product_discovery",
            "autonomous_bargaining",
            "policy_compliance_check",
            "approval_overrides",
            "razorpay_payment_integration",
            "cryptographic_audit_ledger"
        ],
        "permission_scopes": [
            "read:passport",
            "read:products",
            "write:proposals",
            "write:checkout"
        ],
        "payment_provider": "razorpay",
        "supported_currencies": ["INR"],
        "governance_policy_eval": True,
        "webhook_support": True,
        "capabilities": {
            "product_discovery": True,
            "autonomous_bargaining": True,
            "policy_compliance_check": True,
            "approval_overrides": True,
            "razorpay_payment_integration": True,
            "cryptographic_audit_ledger": True
        },
        "payments": {
            "supported_providers": ["razorpay"],
            "currency": "INR",
            "webhooks_supported": True
        }
    }

@app.get("/.well-known/agent-passport.json")
@app.get(f"{settings.API_V1_STR}/passport")
def get_well_known_agent_passport():
    """
    Public machine-readable Agent Passport discovery endpoint for autonomous AI agents.
    Conforms to standard .well-known discovery specifications.
    """
    return get_agent_passport_manifest()

@app.get("/")
def read_root():
    """
    Root endpoint serving basic API metadata.
    """
    return {
        "project": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "active",
        "docs_url": "/docs",
        "passport_url": "/.well-known/agent-passport.json",
        "reload_trigger": 1
    }
