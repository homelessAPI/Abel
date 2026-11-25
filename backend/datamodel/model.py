from typing import Literal

from pydantic import BaseModel, Field, field_validator

from main import safe_custom_url


class CustomSource(BaseModel):
    url: str
    api_key: str | None = None
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "

    @field_validator("url")
    @classmethod
    def validate_url(cls, value):
        return safe_custom_url(value)

    @field_validator("auth_header")
    @classmethod
    def validate_header(cls, value):
        if not value or any(char in value for char in "\r\n:"):
            raise ValueError("Invalid authentication header name.")
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
