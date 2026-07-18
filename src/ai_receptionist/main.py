"""App entrypoint: `uvicorn ai_receptionist.main:app --reload`"""
import structlog
from fastapi import FastAPI

from ai_receptionist.api.routes import health, vapi_webhook, custom_llm
from ai_receptionist.config import settings

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(__import__("logging"), settings.log_level.upper(), 20)
    )
)

app = FastAPI(title="AI Receptionist", version="0.1.0")

app.include_router(custom_llm.router)
app.include_router(health.router)
# app.include_router(vapi_webhook.router)