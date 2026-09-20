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
    "us": "us", "usa": "us", "united states": "us",
    "uk": "gb", "united kingdom": "gb", "england": "gb",
    "de": "de", "germany": "de", "deutschland": "de",
    "fr": "fr", "france": "fr",
    "ca": "ca", "canada": "ca",
    "au": "au", "australia": "au",
    "in": "in", "india": "in",
    "nl": "nl", "netherlands": "nl",
    "at": "at", "austria": "at", "österreich": "at",
    "ch": "ch", "switzerland": "ch", "schweiz": "ch",
    "pl": "pl", "poland": "pl",
    "it": "it", "italy": "it",
    "es": "es", "spain": "es",
    "remote": "de",  # Default to user's likely country for remote
}

# Known cities → country (for when users just type a city name)
CITY_COUNTRY = {
    # Germany
    "berlin": "de", "hamburg": "de", "münchen": "de", "munich": "de",
    "köln": "de", "cologne": "de", "frankfurt": "de", "stuttgart": "de",
    "düsseldorf": "de", "dortmund": "de", "essen": "de", "leipzig": "de",
    "bremen": "de", "dresden": "de", "hannover": "de", "nürnberg": "de",
    "braunschweig": "de", "wolfsburg": "de", "wolfenbüttel": "de",
    "magdeburg": "de", "göttingen": "de", "kassel": "de", "bielefeld": "de",
    "karlsruhe": "de", "mannheim": "de", "augsburg": "de", "wiesbaden": "de",
    "bonn": "de", "münster": "de", "aachen": "de", "freiburg": "de",
    "heidelberg": "de", "darmstadt": "de", "paderborn": "de",
    # UK
    "london": "gb", "manchester": "gb", "birmingham": "gb", "edinburgh": "gb",
    "glasgow": "gb", "bristol": "gb", "leeds": "gb", "liverpool": "gb",
    "cambridge": "gb", "oxford": "gb",
    # France
    "paris": "fr", "lyon": "fr", "marseille": "fr", "toulouse": "fr",
    # Netherlands
    "amsterdam": "nl", "rotterdam": "nl", "utrecht": "nl", "eindhoven": "nl",
    # US
    "new york": "us", "san francisco": "us", "los angeles": "us",
    "chicago": "us", "seattle": "us", "austin": "us", "boston": "us",
    "denver": "us", "atlanta": "us", "miami": "us",
    # India
    "bangalore": "in", "mumbai": "in", "delhi": "in", "hyderabad": "in",
    "pune": "in", "chennai": "in",
}


class AdzunaSource(BaseJobSource):

    BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

    @property
    def name(self) -> str:
        return "adzuna"

    def is_configured(self) -> bool:
        return bool(settings.ADZUNA_APP_ID and settings.ADZUNA_APP_KEY)

    def _resolve_country(self, location: str) -> str:
        """Map a location string to an Adzuna country code.

        Checks country names first, then known city names.
        Defaults to 'de' (Germany) instead of 'us' — most users
        on a German-deployed instance are in Germany.
        """
        loc_lower = location.lower().strip()

        # Check country names/codes first
        for key, code in COUNTRY_MAP.items():
            if key in loc_lower:
                return code

        # Check known city names
        for city, code in CITY_COUNTRY.items():
            if city in loc_lower:
                return code

        # Default — configurable via env, falls back to Germany
        return settings.DEFAULT_COUNTRY if hasattr(settings, 'DEFAULT_COUNTRY') else "de"

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
            loc_clean = location
            # Strip country-level terms and known country keys
            for term in list(COUNTRY_MAP.keys()) + ["germany", "deutschland", "remote"]:
                loc_clean = loc_clean.lower().replace(term, "").strip(" ,")
            if loc_clean:
                params["where"] = loc_clean

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            print(f"  [Adzuna] API error: {e}")
            return []
        except Exception as e:
            print(f"  [Adzuna] Error: {e}")
            return []

        results = []
        for item in data.get("results", []):
            loc_parts = []
            loc_obj = item.get("location", {})
            for area in loc_obj.get("area", []):
                if area and area not in loc_parts:
                    loc_parts.append(area)

            salary_min = item.get("salary_min")
            salary_max = item.get("salary_max")
            salary = ""
            if salary_min and salary_max:
                salary = f"${int(salary_min):,} - ${int(salary_max):,}" if country == "us" else f"€{int(salary_min):,} - €{int(salary_max):,}"
            elif salary_min:
                salary = f"${int(salary_min):,}+" if country == "us" else f"€{int(salary_min):,}+"

            results.append(DiscoveredJob(
                source="adzuna",
                title=item.get("title", "").title(),
                company=item.get("company", {}).get("display_name", "Unknown"),
                location=", ".join(loc_parts) if loc_parts else "",
                remote_type="remote" if "remote" in item.get("title", "").lower() or "remote" in item.get("description", "").lower()[:200] else "",
                salary_range=salary,
                description=item.get("description", ""),
                url=item.get("redirect_url", ""),
                posted_at=item.get("created", ""),
                employment_type=item.get("contract_type", ""),
            ))

        return results