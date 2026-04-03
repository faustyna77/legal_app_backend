import time
import logging
import re
import warnings
import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore", message="Unverified HTTPS request")
logger = logging.getLogger(__name__)

BASE_URL = "https://orzeczenia.nsa.gov.pl"


class NSAScraper:
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        self.session.verify = False

    def scrape_judgment(self, doc_id: str) -> dict | None:
        url = f"{BASE_URL}/doc/{doc_id}"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch %s: %s", url, e)
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        header_tag = soup.find("span", class_="war_header")
        if not header_tag:
            logger.warning("No header found for %s", doc_id)
            return None

        header_text = header_tag.get_text(strip=True)
        case_number = header_text.split(" - ")[0].strip() if " - " in header_text else doc_id
        court_full = header_text.split(" - ", 1)[1].strip() if " - " in header_text else "NSA"

        res_div = soup.find("div", class_="res-div-list")
        date = None
        city = None
        if res_div:
            res_text = res_div.get_text(separator="|", strip=True)
            date_m = re.search(r"Data orzeczenia\|(\d{4}-\d{2}-\d{2})", res_text)
            if date_m:
                date = date_m.group(1)
            city_m = re.search(r"S[aą]d\|([^|]+)", res_text)
            if city_m:
                court_name = city_m.group(1).strip()
                city_m2 = re.search(r"w\s+(\w+(?:\s+\w+)?)\s*$", court_name)
                if city_m2:
                    city = city_m2.group(1).strip()

        content_tag = soup.find("span", class_="info-list-value-uzasadnienie")
        if not content_tag:
            logger.warning("No content found for %s", doc_id)
            return None

        content = content_tag.get_text(separator="\n").strip()

        thesis_tag = soup.find("span", class_="info-list-value-teza")
        thesis = thesis_tag.get_text(separator="\n").strip() if thesis_tag else None

        return {
            "case_number": case_number,
            "court": court_full,
            "city": city,
            "date": date,
            "content": content,
            "thesis": thesis,
            "keywords": [],
            "doc_id": doc_id,
            "source_url": url,
            "source": "nsa",
        }

    def scrape_range(self, date_from: str, date_to: str, limit: int = 500) -> list[dict]:
        results = []
        page = 1

        while len(results) < limit:
            try:
                response = self.session.get(
                    f"{BASE_URL}/cbo/find",
                    params={
                        "dataOd": date_from,
                        "dataDo": date_to,
                        "strona": page,
                    },
                    timeout=15,
                )
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error("Failed to fetch listing page %d: %s", page, e)
                break

            soup = BeautifulSoup(response.content, "html.parser")
            links = [a["href"] for a in soup.find_all("a", href=True) if "/doc/" in a.get("href", "")]

            if not links:
                break

            for href in links:
                if len(results) >= limit:
                    break
                doc_id = href.split("/doc/")[-1]
                judgment = self.scrape_judgment(doc_id)
                if judgment:
                    results.append(judgment)
                    logger.info("Scraped %s (%d/%d)", judgment["case_number"], len(results), limit)
                time.sleep(self.delay)

            page += 1

        return results
