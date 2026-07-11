from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datamodel.model import Search
import requests

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.post("/")
def home(search: Search):
    url = "https://jsearch.p.rapidapi.com/search-v2"
    url_2 = "https://www.themuse.com/api/public/jobs"

    querystring = {"query":"developer jobs in chicago","num_pages":"1","country":"us","date_posted":"all"}
    querystring_2 = {'page': 2}

    headers = {
        "x-rapidapi-key": "301b180464msh055a6626a0f3c1cp125de5jsn506259e0473c",
        "x-rapidapi-host": "jsearch.p.rapidapi.com",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=querystring)

    response_2 = requests.get(url_2, params=querystring_2)

    if response.status_code == 200 and response_2.status_code == 200:
        data = response.json()
        data_2 = response_2.json()

        jobs = []
        jobs_2 = []

        for i in data["data"]['jobs']:
                
                if search.search.lower() in i['job_title'].lower():
                    jobs.append({
                        "Job_Title": i['job_title'],
                        "Company_Name": i['employer_name'],
                        "Location": f"{i.get('job_city') or 'Unknown City'}, {i.get('job_state') or 'Unknown State'}, {i.get('job_country') or 'Unknown Country'}",
                        "URL": i['job_apply_link'],
                        "Salary": i.get('job_salary', "not provided"),
                        "is_remote": i['job_is_remote']
                    })

        for i in data_2['results']:
             if search.search.lower() in i['name'].lower():
                jobs_2.append({
                    "Job title": i['name'],
                    "Company Name": i['company']['short_name'],
                    "Location": i['locations'][0]['name'],
                    "URL": i['refs']['landing_page'],
                })



        return {"jobs": jobs, "jobs_2": jobs_2}
    
    elif response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )


if __name__ == "__main__":
    home()
