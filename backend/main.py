import ipaddress
import os
import socket
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from datamodel.model import Search

app = FastAPI(title="Abel API", version="1.0.0")

origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "AbelJobSearch/1.0"})


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    return str(value).strip()


def safe_custom_url(value):
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Custom source URLs must use HTTPS.")
    host = parsed.hostname.lower()
    if host in {"localhost"} or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local and internal addresses are not allowed.")
    try:
        address = ipaddress.ip_address(host)
        if not address.is_global:
            raise ValueError("Private or reserved IP addresses are not allowed.")
    except ValueError as error:
        if "not allowed" in str(error):
            raise
        try:
            addresses = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise ValueError("The custom source hostname could not be resolved.")
        for address_info in addresses:
            ip = ipaddress.ip_address(address_info[4][0])
            if not ip.is_global:
                raise ValueError("The custom source resolves to a private or reserved address.")
    return value


def normalize_job(raw, source):
    if not isinstance(raw, dict):
        return None

    company = raw.get("employer_name") or raw.get("company") or raw.get("company_name")
    if isinstance(company, dict):
        company = company.get("name") or company.get("short_name")

    location = raw.get("job_location") or raw.get("location") or raw.get("locations")
    if isinstance(location, list):
        location = ", ".join(
            clean_text(item.get("name") if isinstance(item, dict) else item)
            for item in location
        )
    elif isinstance(location, dict):
        location = ", ".join(
            filter(None, [
                clean_text(location.get("city")),
                clean_text(location.get("state")),
                clean_text(location.get("country")),
                clean_text(location.get("name")),
            ])
        )

    if not location:
        location = ", ".join(filter(None, [
            clean_text(raw.get("job_city") or raw.get("city")),
            clean_text(raw.get("job_state") or raw.get("state")),
            clean_text(raw.get("job_country") or raw.get("country")),
        ]))

    apply_url = (
        raw.get("job_apply_link")
        or raw.get("url")
        or raw.get("apply_url")
        or raw.get("job_url")
    )
    refs = raw.get("refs")
    if not apply_url and isinstance(refs, dict):
        apply_url = refs.get("landing_page")

    title = raw.get("job_title") or raw.get("name") or raw.get("title")
    if not title or not apply_url:
        return None

    salary = raw.get("job_salary") or raw.get("salary") or raw.get("salary_range")
    if not salary:
        minimum = raw.get("min_salary") or raw.get("salary_min")
        maximum = raw.get("max_salary") or raw.get("salary_max")
        if minimum or maximum:
            salary = " - ".join(filter(None, [clean_text(minimum), clean_text(maximum)]))

    remote = raw.get("job_is_remote")
    if remote is None:
        remote = raw.get("is_remote")
    if remote is None:
        remote = "remote" in clean_text(raw.get("workplace_type")).lower()

    return {
        "id": clean_text(raw.get("job_id") or raw.get("id") or apply_url),
        "title": clean_text(title),
        "company": clean_text(company) or "Company not listed",
        "location": clean_text(location) or "Location not listed",
        "employment_type": clean_text(
            raw.get("job_employment_type") or raw.get("employment_type") or raw.get("type")
        ) or "Not specified",
        "experience_level": clean_text(
            raw.get("job_required_experience") or raw.get("experience_level") or raw.get("seniority")
        ),
        "salary": clean_text(salary) or "Not disclosed",
        "remote": bool(remote),
        "description": clean_text(raw.get("job_description") or raw.get("description")),
        "posted_at": clean_text(raw.get("job_posted_at_datetime_utc") or raw.get("posted_at") or raw.get("date")),
        "url": clean_text(apply_url),
        "source": source,
    }


def extract_items(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("jobs", "results", "data", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = extract_items(value)
            if nested:
                return nested
    return []


def fetch_jsearch(search):
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return [], "JSearch is not configured. Add RAPIDAPI_KEY to the backend environment."
    query_parts = [search.keywords or "jobs"]
    if search.location:
        query_parts.append("in " + search.location)
    if search.experience_level:
        query_parts.append(search.experience_level + " level")
    if search.employment_type:
        query_parts.append(search.employment_type)
    if search.remote is True:
        query_parts.append("remote")
    params = {
        "query": " ".join(query_parts),
        "page": str(search.page),
        "num_pages": "1",
        "country": search.country,
        "date_posted": search.date_posted,
    }
    response = SESSION.get(
        "https://jsearch.p.rapidapi.com/search",
        headers={
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        },
        params=params,
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    return [
        job for job in (normalize_job(item, "JSearch") for item in extract_items(payload))
        if job
    ], None


def fetch_themuse(search):
    params = {"page": max(search.page - 1, 0)}
    if search.location:
        params["location"] = search.location
    response = SESSION.get(
        "https://www.themuse.com/api/public/jobs",
        params=params,
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    return [
        job for job in (normalize_job(item, "The Muse") for item in extract_items(payload))
        if job
    ], None


def fetch_custom(search):
    config = search.custom_source
    if not config:
        return [], "Custom source configuration is missing."
    headers = {"Accept": "application/json"}
    if config.api_key:
        headers[config.auth_header] = config.auth_prefix + config.api_key
    params = {
        "query": search.keywords,
        "location": search.location,
        "experience": search.experience_level,
        "employment_type": search.employment_type,
        "remote": search.remote,
        "page": search.page,
    }
    params = {key: value for key, value in params.items() if value not in (None, "")}
    response = SESSION.get(
        config.url,
        headers=headers,
        params=params,
        timeout=15,
        allow_redirects=False,
    )
    response.raise_for_status()
    return [
        job for job in (normalize_job(item, "Custom source") for item in extract_items(response.json()))
        if job
    ], None


def matches_filters(job, search):
    haystack = " ".join([
        job["title"], job["company"], job["description"], job["employment_type"],
        job["experience_level"],
    ]).lower()
    if search.keywords and not all(
        word in haystack for word in search.keywords.lower().split()
    ):
        return False
    if search.location and search.location.lower() not in job["location"].lower():
        return False
    if search.remote is not None and job["remote"] != search.remote:
        return False
    if search.employment_type:
        if search.employment_type.lower() not in job["employment_type"].lower():
            return False
    if search.experience_level:
        level = search.experience_level.lower()
        text = (job["title"] + " " + job["experience_level"] + " " + job["description"]).lower()
        terms = {
            "entry": ("entry", "junior", "intern", "graduate", "associate"),
            "junior": ("junior", "entry", "associate"),
            "mid": ("mid", "intermediate"),
            "senior": ("senior", "lead", "principal", "staff"),
            "internship": ("intern", "internship"),
        }.get(level, (level,))
        if not any(term in text for term in terms):
            return False
    return True


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Abel API"}


@app.post("/api/jobs")
def search_jobs(search: Search):
    jobs = []
    errors = []
    sources_used = []

    try:
        if search.source_mode == "custom":
            custom_jobs, error = fetch_custom(search)
            jobs.extend(custom_jobs)
            sources_used.append("Custom source")
            if error:
                errors.append(error)
        else:
            for source_name, fetcher in (
                ("JSearch", fetch_jsearch),
                ("The Muse", fetch_themuse),
            ):
                try:
                    source_jobs, error = fetcher(search)
                    jobs.extend(source_jobs)
                    if source_jobs:
                        sources_used.append(source_name)
                    if error:
                        errors.append(error)
                except requests.RequestException as error:
                    errors.append(source_name + ": " + str(error))
                except (ValueError, KeyError) as error:
                    errors.append(source_name + ": invalid response (" + str(error) + ")")
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail="Custom source request failed: " + str(error))
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=502, detail="Custom source returned invalid JSON: " + str(error))

    filtered = [job for job in jobs if matches_filters(job, search)]
    unique = {}
    for job in filtered:
        unique[job["url"]] = job
    results = list(unique.values())[:search.limit]

    if not results and errors and not jobs:
        return {
            "jobs": [],
            "total": 0,
            "sources": sources_used,
            "warnings": errors,
            "message": "No job sources returned results. Check the source configuration and try again.",
        }

    return {
        "jobs": results,
        "total": len(results),
        "sources": sources_used,
        "warnings": errors,
        "message": None if results else "No matching jobs found. Try broadening your filters.",
    }
