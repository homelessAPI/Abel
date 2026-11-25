from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator

class CustomSource(BaseModel):
    url: str
    api_key: str | None = None
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "

    @field_validator("url")
    @classmethod
    def validate_url(cls, value):
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Custom source URLs must use HTTPS.")
        if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Local addresses are not allowed.")
        return value

class Search(BaseModel):
    keywords: str = Field(default="", max_length=120)
    location: str | None = Field(default=None, max_length=120)
    country: str = Field(default="us", min_length=2, max_length=2)
    experience_level: Literal["entry", "junior", "mid", "senior", "internship"] | None = None
    employment_type: Literal["FULLTIME", "PARTTIME", "CONTRACTOR", "INTERN", "TEMPORARY"] | None = None
    remote: bool | None = None
    date_posted: Literal["all", "today", "3days", "week", "month"] = "all"
    page: int = Field(default=1, ge=1, le=20)
    limit: int = Field(default=50, ge=1, le=100)
    source_mode: Literal["default", "custom"] = "default"
    custom_source: CustomSource | None = None

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value):
        return value.lower()
