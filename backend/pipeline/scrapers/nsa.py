import time
import logging
import re
import warnings
import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore", message="Unverified HTTPS request")
logger = logging.getLogger(__name__)

BASE_URL = "https://orzeczenia.nsa.gov.pl"

_ARTICLE_PATTERN = re.compile(
    r"\bart\.\s*\d+[a-z]?(?:\s*§\s*\d+[a-z]?)?(?:\s*ust\.\s*\d+[a-z]?)?(?:\s*pkt\s*\d+[a-z]?)?",
    re.IGNORECASE,
)

_ACT_KEYWORDS = {
    "prawo bankowe": "Ustawa z dnia 29 sierpnia 1997 r. - Prawo bankowe",
    "kodeks cywilny": "Ustawa z dnia 23 kwietnia 1964 r. - Kodeks cywilny",
    "kodeks postępowania cywilnego": "Ustawa z dnia 17 listopada 1964 r. - Kodeks postępowania cywilnego",
    "kodeks postepowania cywilnego": "Ustawa z dnia 17 listopada 1964 r. - Kodeks postępowania cywilnego",
    "kodeks postępowania administracyjnego": "Ustawa z dnia 14 czerwca 1960 r. - Kodeks postępowania administracyjnego",
    "kodeks postepowania administracyjnego": "Ustawa z dnia 14 czerwca 1960 r. - Kodeks postępowania administracyjnego",
    "ordynacja podatkowa": "Ustawa z dnia 29 sierpnia 1997 r. - Ordynacja podatkowa",
    "prawo o postępowaniu przed sądami administracyjnymi": "Ustawa z dnia 30 sierpnia 2002 r. - Prawo o postępowaniu przed sądami administracyjnymi",
    "prawo o postepowaniu przed sadami administracyjnymi": "Ustawa z dnia 30 sierpnia 2002 r. - Prawo o postępowaniu przed sądami administracyjnymi",
    "p.p.s.a": "Ustawa z dnia 30 sierpnia 2002 r. - Prawo o postępowaniu przed sądami administracyjnymi",
    "k.p.a": "Ustawa z dnia 14 czerwca 1960 r. - Kodeks postępowania administracyjnego",
    "k.p.c": "Ustawa z dnia 17 listopada 1964 r. - Kodeks postępowania cywilnego",
    "k.c": "Ustawa z dnia 23 kwietnia 1964 r. - Kodeks cywilny",
}


class NSAScraper:
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        self.session.verify = False

    @staticmethod
    def _normalize_article(article: str) -> str:
        normalized = " ".join((article or "").split())
        return normalized.lower().strip()

    def extract_regulations(self, content: str) -> list[dict]:
        if not content:
            return []

        found_articles = _ARTICLE_PATTERN.findall(content)
        seen = set()
        articles = []
        for article in found_articles:
            normalized = self._normalize_article(article)
            if normalized and normalized not in seen:
                seen.add(normalized)
                articles.append(normalized)

        content_l = content.lower()
        regulations = []
        seen_acts = set()
        for keyword, act_title in _ACT_KEYWORDS.items():
            if keyword in content_l and act_title not in seen_acts:
                seen_acts.add(act_title)
                regulations.append(
                    {
                        "act_title": act_title,
                        "act_year": None,
                        "journal_no": None,
                        "articles": articles,
                    }
                )

        if articles and not regulations:
            regulations.append(
                {
                    "act_title": "Nieustalony akt prawny (NSA regex)",
                    "act_year": None,
                    "journal_no": None,
                    "articles": articles,
                }
            )

        return regulations

    def scrape_judgment(self, doc_id: str) -> dict | None:
        url = f"{BASE_URL}/doc/{doc_id}"
        try:
            response = self.session.get(url, timeout=30)
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
        judgment_type = None
        is_final = None
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
            type_m = re.search(r"Rodzaj orzeczenia\|([^|]+)", res_text)
            if type_m:
                judgment_type = type_m.group(1).strip().lower()
            final_m = re.search(r"Prawomocno[śs][ćc]\|([^|]+)", res_text)
            if final_m:
                raw_final = final_m.group(1).strip().lower()
                if "prawomocn" in raw_final and "nie" not in raw_final:
                    is_final = "prawomocny"
                elif "nieprawomocn" in raw_final or ("nie" in raw_final and "prawomocn" in raw_final):
                    is_final = "nieprawomocny"
                else:
                    is_final = raw_final

        content_tags = soup.find_all("span", class_="info-list-value-uzasadnienie")
        if not content_tags:
            logger.warning("No content found for %s", doc_id)
            return None

        content_parts = [tag.get_text(separator="\n").strip() for tag in content_tags if tag.get_text(strip=True)]
        content = "\n\n".join(content_parts).strip()
        regulations = self.extract_regulations(content)

        thesis_tag = soup.find("span", class_="info-list-value-teza")
        thesis = thesis_tag.get_text(separator="\n").strip() if thesis_tag else None

        court_type = None
        if "Naczelny Sąd Administracyjny" in court_full or court_full.startswith("NSA"):
            court_type = "NSA"
        elif "Wojewódzki Sąd Administracyjny" in court_full or "WSA" in court_full:
            court_type = "WSA"

        return {
            "case_number": case_number,
            "court": court_full,
            "court_type": court_type,
            "city": city,
            "date": date,
            "content": content,
            "thesis": thesis,
            "keywords": [],
            "doc_id": doc_id,
            "source_url": url,
            "source": "nsa",
            "legal_area": "administracyjne",
            "regulations": regulations,
            "judgment_type": judgment_type,
            "is_final": is_final,
        }

    def scrape_range(self, date_from: str, date_to: str, limit: int = 500) -> list[dict]:
        results = []
        page = 1
        consecutive_out_of_range = 0

        while len(results) < limit:
            try:
                response = self.session.get(
                    f"{BASE_URL}/cbo/find",
                    params={"p": page},
                    timeout=30,
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
                    j_date = judgment.get("date") or ""
                    if date_from <= j_date <= date_to:
                        results.append(judgment)
                        consecutive_out_of_range = 0
                        logger.info("Scraped %s date=%s (%d/%d)", judgment["case_number"], j_date, len(results), limit)
                    elif j_date < date_from:
                        consecutive_out_of_range += 1
                        logger.info("Skipped %s date=%s (too old)", judgment["case_number"], j_date)
                        if consecutive_out_of_range >= 5:
                            logger.info("5 consecutive old judgments, stopping")
                            return results
                    else:
                        logger.info("Skipped %s date=%s (too new)", judgment["case_number"], j_date)
                time.sleep(self.delay)

            page += 1

        return results
