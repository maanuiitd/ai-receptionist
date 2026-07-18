"""Central, typed configuration. Import `settings` everywhere; never read os.environ directly."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"

    # Vapi
    vapi_api_key: str
    vapi_webhook_secret: str
    human_handoff_number: str
    emergency_handoff_number: str

    # Airtable
    airtable_api_key: str
    airtable_base_id: str
    airtable_contacts_table: str = "Contacts"
    airtable_appointments_table: str = "Appointments"
    airtable_call_logs_table: str = "CallLogs"

    # Google Calendar
    google_service_account_file: str
    google_calendar_id: str = "primary"
    business_timezone: str = "Asia/Kolkata"
    business_hours_start: str = "09:00"
    business_hours_end: str = "18:00"
    appointment_duration_minutes: int = 60

    # App
    app_env: str = "dev"
    log_level: str = "INFO"
    kb_file: str = "./data/knowledge_base.md"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
