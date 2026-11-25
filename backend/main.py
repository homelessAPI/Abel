import ipaddress
import os
import socket
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from datamodel.model import Search


load_dotenv()

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
    if value is None or isinstance(value, (dict, list)):
        return ""

    return str(value).strip()


def safe_custom_url(url):
    parsed_url = urlparse(url)

    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise ValueError("Custom source URLs must use HTTPS.")

    hostname = parsed_url.hostname.lower()

    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local and internal addresses are not allowed.")

    try:
        ip_address = ipaddress.ip_address(hostname)

        if not ip_address.is_global:
            raise ValueError("Private or reserved IP addresses are not allowed.")

    except ValueError as error:
        if "not allowed" in str(error):
            raise

        try:
            addresses = socket.getaddrinfo(
                hostname,
                parsed_url.port or 443,
                type=socket.SOCK_STREAM
            )
        except socket.gaierror:
            raise ValueError("The custom source hostname could not be resolved.")

        for address_info in addresses:
            ip_address = ipaddress.ip_address(address_info[4][0])

            if not ip_address.is_global:
                raise ValueError("The custom source resolves to a private or reserved address.")

    return url


def get_job_company(job_data):
    company = (
        job_data.get("employer_name")
        or job_data.get("company")
        or job_data.get("company_name")
        or job_data.get("companyName")
    )

    if isinstance(company, dict):
        company = company.get("name") or company.get("short_name")

    return clean_text(company) or "Company not listed"


def get_job_location(job_data, is_remote):
    location = (
        job_data.get("job_location")
        or job_data.get("location")
        or job_data.get("locations")
    )

    if isinstance(location, list):
        location = ", ".join(
            clean_text(item.get("name") if isinstance(item, dict) else item)
            for item in location
        )

    elif isinstance(location, dict):
        location = ", ".join(filter(None, [
            clean_text(location.get("city")),
            clean_text(location.get("state")),
            clean_text(location.get("country")),
            clean_text(location.get("name")),
        ]))

    restrictions = job_data.get("locationRestrictions")

    if not location and isinstance(restrictions, list):
        location = ", ".join(restrictions) if restrictions else "Remote (Worldwide)"

    if not location:
        location = ", ".join(filter(None, [
            clean_text(job_data.get("job_city") or job_data.get("city")),
            clean_text(job_data.get("job_state") or job_data.get("state")),
            clean_text(job_data.get("job_country") or job_data.get("country")),
        ]))

    return clean_text(location) or ("Remote" if is_remote else "Location not listed")


def get_job_url(job_data):
    apply_url = (
        job_data.get("job_apply_link")
        or job_data.get("applicationLink")
        or job_data.get("url")
        or job_data.get("apply_url")
        or job_data.get("job_url")
        or job_data.get("position_url")
    )

    refs = job_data.get("refs")

    if not apply_url and isinstance(refs, dict):
        apply_url = refs.get("landing_page")

    return clean_text(apply_url)


def get_job_salary(job_data):
    salary = (
        job_data.get("job_salary")
        or job_data.get("salary")
        or job_data.get("salary_range")
        or job_data.get("salaryText")
    )

    minimum = (
        job_data.get("min_salary")
        or job_data.get("salary_min")
        or job_data.get("minSalary")
    )

    maximum = (
        job_data.get("max_salary")
        or job_data.get("salary_max")
        or job_data.get("maxSalary")
    )

    if not salary and (minimum is not None or maximum is not None):
        currency = clean_text(job_data.get("currency"))
        period = clean_text(job_data.get("salaryPeriod"))

        salary = " - ".join(filter(None, [
            clean_text(minimum),
            clean_text(maximum),
        ]))

        if currency:
            salary += " " + currency

        if period:
            salary += " / " + period

    return clean_text(salary) or "Not disclosed"


def get_remote_status(job_data, source_name):
    remote = job_data.get("job_is_remote")

    if remote is None:
        remote = job_data.get("is_remote")

    if remote is None:
        remote = job_data.get("remote")

    if isinstance(remote, str):
        remote = remote.lower() in ("true", "yes", "1", "remote")

    if remote is None and source_name in ("Himalayas", "Remote OK"):
        remote = True

    if remote is None:
        workplace_type = clean_text(job_data.get("workplace_type")).lower()
        remote = "remote" in workplace_type

    return bool(remote)


def normalize_job(job_data, source_name):
    if not isinstance(job_data, dict):
        return None

    title = (
        job_data.get("job_title")
        or job_data.get("position")
        or job_data.get("name")
        or job_data.get("title")
    )

    apply_url = get_job_url(job_data)

    if not title or not apply_url:
        return None

    is_remote = get_remote_status(job_data, source_name)
    company = get_job_company(job_data)
    location = get_job_location(job_data, is_remote)
    salary = get_job_salary(job_data)

    employment_type = (
        job_data.get("job_employment_type")
        or job_data.get("employment_type")
        or job_data.get("employmentType")
        or job_data.get("job_types")
        or job_data.get("type")
    )

    if isinstance(employment_type, list):
        employment_type = ", ".join(clean_text(item) for item in employment_type)

    experience_level = (
        job_data.get("job_required_experience")
        or job_data.get("experience_level")
        or job_data.get("seniority")
    )

    if isinstance(experience_level, list):
        experience_level = ", ".join(clean_text(item) for item in experience_level)

    tags = job_data.get("tags") or job_data.get("categories") or []

    if isinstance(tags, list):
        tags_text = " ".join(clean_text(item) for item in tags)
    else:
        tags_text = clean_text(tags)

    description = clean_text(
        job_data.get("job_description")
        or job_data.get("description")
        or job_data.get("excerpt")
    )

    description = (description + " " + tags_text).strip()

    posted_at = (
        job_data.get("job_posted_at_datetime_utc")
        or job_data.get("posted_at")
        or job_data.get("pubDate")
        or job_data.get("created_at")
        or job_data.get("date")
    )

    if isinstance(posted_at, (int, float)):
        posted_at = datetime.fromtimestamp(posted_at, timezone.utc).isoformat()

    source_urls = {
        "Himalayas": "https://himalayas.app",
        "Remote OK": "https://remoteok.com",
    }

    return {
        "id": clean_text(
            job_data.get("job_id")
            or job_data.get("guid")
            or job_data.get("id")
            or job_data.get("slug")
            or apply_url
        ),
        "title": clean_text(title),
        "company": company,
        "location": location,
        "employment_type": clean_text(employment_type) or "Not specified",
        "experience_level": clean_text(experience_level),
        "salary": salary,
        "remote": is_remote,
        "description": description,
        "posted_at": clean_text(posted_at),
        "url": apply_url,
        "source": source_name,
        "source_url": source_urls.get(source_name, ""),
    }


def extract_items(response_data):
    if isinstance(response_data, list):
        return response_data

    if not isinstance(response_data, dict):
        return []

    for key in ("jobs", "results", "data", "items"):
        items = response_data.get(key)

        if isinstance(items, list):
            return items

        if isinstance(items, dict):
            nested_items = extract_items(items)

            if nested_items:
                return nested_items

    return []


# Public feeds are cached so Abel does not request the same data every time.
JOB_FEED_CACHE = {}
JOB_FEED_CACHE_SECONDS = 3600


def get_cached_feed(source_name, url, params=None):
    cache_key = (source_name, tuple(sorted((params or {}).items())))
    cached_data = JOB_FEED_CACHE.get(cache_key)
    current_time = time.time()

    if cached_data and current_time - cached_data["saved_at"] < JOB_FEED_CACHE_SECONDS:
        return cached_data["payload"]

    response = SESSION.get(url, params=params, timeout=20)
    response.raise_for_status()

    response_data = response.json()

    JOB_FEED_CACHE[cache_key] = {
        "saved_at": current_time,
        "payload": response_data,
    }

    return response_data


def get_provider_jobs(response_data):
    if isinstance(response_data, list):
        return response_data

    return extract_items(response_data)


def fetch_himalayas(search_data):
    params = {
        "page": search_data.page,
        "sort": "recent",
    }

    if search_data.keywords:
        params["q"] = search_data.keywords

    if search_data.location and search_data.location.strip().lower() == "remote":
        params["worldwide"] = "true"
    else:
        params["country"] = search_data.country.upper()

    seniority_options = {
        "entry": "Entry-level",
        "junior": "Entry-level",
        "mid": "Mid-level",
        "senior": "Senior",
        "internship": "Entry-level",
    }

    seniority = seniority_options.get(search_data.experience_level)

    if seniority:
        params["seniority"] = seniority

    employment_options = {
        "FULLTIME": "Full Time",
        "PARTTIME": "Part Time",
        "CONTRACTOR": "Contractor",
        "INTERN": "Intern",
        "TEMPORARY": "Temporary",
    }

    employment_type = employment_options.get(search_data.employment_type)

    if employment_type:
        params["employment_type"] = employment_type

    response_data = get_cached_feed(
        "Himalayas",
        "https://himalayas.app/jobs/api/search",
        params,
    )

    provider_jobs = get_provider_jobs(response_data)
    jobs = []

    for job_data in provider_jobs:
        job = normalize_job(job_data, "Himalayas")

        if job:
            jobs.append(job)

    return jobs, None


def fetch_remote_ok(search_data):
    params = {}

    if search_data.keywords:
        params["tag"] = search_data.keywords.split()[0].lower()

    response_data = get_cached_feed(
        "Remote OK",
        "https://remoteok.com/api",
        params,
    )

    provider_jobs = get_provider_jobs(response_data)
    jobs = []

    for job_data in provider_jobs:
        job = normalize_job(job_data, "Remote OK")

        if job:
            jobs.append(job)

    return jobs, None


def fetch_custom(search_data):
    config = search_data.custom_source

    if not config:
        return [], "Custom source configuration is missing."

    safe_custom_url(config.url)

    headers = {"Accept": "application/json"}

    if config.api_key:
        headers[config.auth_header] = config.auth_prefix + config.api_key

    params = {
        "query": search_data.keywords,
        "location": search_data.location,
        "experience": search_data.experience_level,
        "employment_type": search_data.employment_type,
        "remote": search_data.remote,
        "page": search_data.page,
    }

    params = {
        key: value
        for key, value in params.items()
        if value not in (None, "")
    }

    response = SESSION.get(
        config.url,
        headers=headers,
        params=params,
        timeout=15,
        allow_redirects=False,
    )

    response.raise_for_status()

    response_data = response.json()
    provider_jobs = extract_items(response_data)
    jobs = []

    for job_data in provider_jobs:
        job = normalize_job(job_data, "Custom source")

        if job:
            jobs.append(job)

    return jobs, None


def matches_filters(job, search_data):
    if search_data.date_posted != "all" and job["posted_at"]:
        try:
            posted_at = datetime.fromisoformat(
                job["posted_at"].replace("Z", "+00:00")
            )

            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=timezone.utc)

            date_options = {
                "today": 1,
                "3days": 3,
                "week": 7,
                "month": 30,
            }

            days = date_options.get(search_data.date_posted)

            if days and datetime.now(timezone.utc) - posted_at > timedelta(days=days):
                return False

        except (TypeError, ValueError):
            pass

    job_text = " ".join([
        job["title"],
        job["company"],
        job["description"],
        job["employment_type"],
        job["experience_level"],
    ]).lower()

    if search_data.keywords:
        keywords = search_data.keywords.lower().split()

        for word in keywords:
            if word not in job_text:
                return False

    if search_data.location:
        location = search_data.location.lower()

        if location not in job["location"].lower():
            # Himalayas already filters by country, so keep US-eligible remote jobs.
            is_us_remote_job = (
                job["remote"]
                and search_data.country.lower() == "us"
                and job["source"] == "Himalayas"
            )

            if not is_us_remote_job:
                return False

    if search_data.remote is not None and job["remote"] != search_data.remote:
        return False

    if search_data.employment_type:
        employment_options = {
            "FULLTIME": ("full time", "full-time", "fulltime"),
            "PARTTIME": ("part time", "part-time", "parttime"),
            "CONTRACTOR": ("contractor", "contract"),
            "INTERN": ("intern", "internship"),
            "TEMPORARY": ("temporary", "temp"),
        }

        employment_terms = employment_options.get(
            search_data.employment_type,
            (search_data.employment_type.lower(),),
        )

        job_employment = job["employment_type"].lower()

        if not any(term in job_employment for term in employment_terms):
            return False

    if search_data.experience_level:
        experience_level = search_data.experience_level.lower()

        job_experience = (
            job["title"]
            + " "
            + job["experience_level"]
            + " "
            + job["description"]
        ).lower()

        experience_options = {
            "entry": ("entry", "junior", "intern", "graduate", "associate"),
            "junior": ("junior", "entry", "associate"),
            "mid": ("mid", "intermediate"),
            "senior": ("senior", "lead", "principal", "staff"),
            "internship": ("intern", "internship"),
        }

        experience_terms = experience_options.get(
            experience_level,
            (experience_level,),
        )

        if not any(term in job_experience for term in experience_terms):
            return False

    return True


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "Abel API",
    }


@app.post("/api/jobs")
def search_jobs(search_data: Search):
    jobs = []
    errors = []
    sources_used = []

    try:
        if search_data.source_mode == "custom":
            custom_jobs, error = fetch_custom(search_data)
            jobs.extend(custom_jobs)
            sources_used.append("Custom source")

            if error:
                errors.append(error)

        else:
            job_sources = [
                ("Himalayas", fetch_himalayas),
                ("Remote OK", fetch_remote_ok),
            ]

            for source_name, fetch_jobs in job_sources:
                try:
                    source_jobs, error = fetch_jobs(search_data)
                    jobs.extend(source_jobs)

                    if source_jobs:
                        sources_used.append(source_name)

                    if error:
                        errors.append(error)

                except requests.RequestException as error:
                    errors.append(source_name + ": " + str(error))

                except (ValueError, KeyError) as error:
                    errors.append(
                        source_name + ": invalid response (" + str(error) + ")"
                    )

    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail="Custom source request failed: " + str(error),
        )

    except (ValueError, KeyError) as error:
        raise HTTPException(
            status_code=502,
            detail="Custom source returned invalid JSON: " + str(error),
        )

    filtered_jobs = []

    for job in jobs:
        if matches_filters(job, search_data):
            filtered_jobs.append(job)

    unique_jobs = {}

    for job in filtered_jobs:
        unique_jobs[job["url"]] = job

    results = list(unique_jobs.values())[:search_data.limit]

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
