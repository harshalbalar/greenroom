"""
Adzuna job source.

Direct API — no middleman like RapidAPI. Strong UK/EU coverage,
decent US. Supports country-specific endpoints for global search.

Free tier: 1,000 calls/month.
Sign up: https://developer.adzuna.com
"""

import requests
from config import settings
from sources.base import BaseJobSource, DiscoveredJob
 

# Adzuna uses country codes in the URL
COUNTRY_MAP = {
    # Common search targets — extend as needed
    "us": "us", "usa": "us", "united states": "us",
    "uk": "gb", "united kingdom": "gb", "england": "gb",
    "de": "de", "germany": "de", "deutschland": "de",
    "fr": "fr", "france": "fr",
    "ca": "ca", "canada": "ca",
    "au": "au", "australia": "au",
    "in": "in", "india": "in",
    "nl": "nl", "netherlands": "nl",
    "remote": "us",  # Default to US for remote searches
}


class AdzunaSource(BaseJobSource):

    BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

    @property
    def name(self) -> str:
        return "adzuna"

    def is_configured(self) -> bool:
        return bool(settings.ADZUNA_APP_ID and settings.ADZUNA_APP_KEY)

    def _resolve_country(self, location: str) -> str:
        """Map a location string to an Adzuna country code."""
        loc_lower = location.lower().strip()
        for key, code in COUNTRY_MAP.items():
            if key in loc_lower:
                return code
        return "us"  # Default fallback

    def search(
        self,
        query: str,
        location: str = "",
        remote_only: bool = False,
        num_results: int = 10,
    ) -> list[DiscoveredJob]:
        if not self.is_configured():
            return []

        country = self._resolve_country(location)
        url = self.BASE_URL.format(country=country, page=1)

        params = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "results_per_page": min(num_results, 20),
            "what": query,
            "content-type": "application/json",
            "max_days_old": 30,
        }

        # Adzuna uses 'where' for location within a country
        if location and not remote_only:
            # Strip country-level terms, keep city/region
            loc_clean = location
            for term in COUNTRY_MAP.keys():
                loc_clean = loc_clean.lower().replace(term, "").strip(" ,")
            if loc_clean:
                params["where"] = loc_clean

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            jobs = []
            for item in data.get("results", [])[:num_results]:
                # Build salary string
                salary = ""
                sal_min = item.get("salary_min")
                sal_max = item.get("salary_max")
                if sal_min and sal_max:
                    salary = f"${sal_min:,.0f} - ${sal_max:,.0f}"
                elif sal_min:
                    salary = f"${sal_min:,.0f}+"

                # Location
                loc_data = item.get("location", {})
                job_location = loc_data.get("display_name", "")

                # Company
                company_data = item.get("company", {})
                company_name = company_data.get("display_name", "")

                # Description — Adzuna returns HTML fragments, strip basic tags
                desc = item.get("description", "")

                jobs.append(DiscoveredJob(
                    source=self.name,
                    title=item.get("title", ""),
                    company=company_name,
                    location=job_location,
                    remote_type="",  # Adzuna doesn't have a clean remote flag
                    salary_range=salary,
                    description=desc[:3000],
                    url=item.get("redirect_url", ""),
                    posted_at=item.get("created", ""),
                    employment_type=item.get("contract_time", ""),
                ))

            return jobs

        except requests.RequestException as e:
            print(f"  [Adzuna] API error: {e}")
            return []
        except (KeyError, ValueError) as e:
            print(f"  [Adzuna] Parse error: {e}")
            return []
