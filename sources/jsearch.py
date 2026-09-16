"""
JSearch job source (via RapidAPI).

Reads Google for Jobs, which indexes LinkedIn, Indeed, Glassdoor,
ZipRecruiter, and thousands of company career pages. Broadest single-API
coverage available.

Free tier: 500 requests/month on RapidAPI.
Sign up: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
"""

import requests
from config import settings
from sources.base import BaseJobSource, DiscoveredJob


class JSearchSource(BaseJobSource):

    BASE_URL = "https://jsearch.p.rapidapi.com/search"

    @property
    def name(self) -> str:
        return "jsearch"

    def is_configured(self) -> bool:
        return bool(settings.JSEARCH_API_KEY)

    def search(
        self,
        query: str,
        location: str = "",
        remote_only: bool = False,
        num_results: int = 10,
    ) -> list[DiscoveredJob]:
        if not self.is_configured():
            return []

        search_query = query
        if location:
            search_query += f" in {location}"

        params = {
            "query": search_query,
            "page": "1",
            "num_pages": "1",
            "date_posted": "month",  # Last 30 days
        }
        if remote_only:
            params["remote_jobs_only"] = "true"

        headers = {
            "X-RapidAPI-Key": settings.JSEARCH_API_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

        try:
            resp = requests.get(self.BASE_URL, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            jobs = []
            for item in data.get("data", [])[:num_results]:
                # Determine remote type
                remote_type = ""
                if item.get("job_is_remote"):
                    remote_type = "remote"

                # Build salary string
                salary = ""
                sal_min = item.get("job_min_salary")
                sal_max = item.get("job_max_salary")
                sal_currency = item.get("job_salary_currency", "USD")
                if sal_min and sal_max:
                    salary = f"{sal_currency} {sal_min:,.0f} - {sal_max:,.0f}"
                elif sal_min:
                    salary = f"{sal_currency} {sal_min:,.0f}+"

                # Build location string
                city = item.get("job_city", "")
                state = item.get("job_state", "")
                country = item.get("job_country", "")
                location_parts = [p for p in [city, state, country] if p]
                job_location = ", ".join(location_parts)

                jobs.append(DiscoveredJob(
                    source=self.name,
                    title=item.get("job_title", ""),
                    company=item.get("employer_name", ""),
                    location=job_location,
                    remote_type=remote_type,
                    salary_range=salary,
                    description=item.get("job_description", "")[:3000],  # Cap length
                    url=item.get("job_apply_link", "") or item.get("job_google_link", ""),
                    posted_at=item.get("job_posted_at_datetime_utc", ""),
                    employment_type=item.get("job_employment_type", ""),
                ))

            return jobs

        except requests.RequestException as e:
            print(f"  [JSearch] API error: {e}")
            return []
        except (KeyError, ValueError) as e:
            print(f"  [JSearch] Parse error: {e}")
            return []
