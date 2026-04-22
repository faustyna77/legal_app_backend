import time
import logging
import re
import warnings
import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore", message="Unverified HTTPS request")
logger = logging.getLogger(__name__)

BASE_URL = "https://orzeczenia.nsa.gov.pl"

_KNOWN_RES_LABELS = {
    "Data orzeczenia", "Data wpływu", "Sąd", "Sędziowie",
    "Symbol z opisem", "Symbole z opisem", "Hasła tematyczne", "Powiązane",
    "Skarżony organ", "Treść wyniku", "Sentencja", "Prawomocność",
    "Rodzaj orzeczenia", "Sygnatura",
}


def _parse_res_div_fields(res_div) -> dict[str, list[str]]:
    """Parse res-div-list block into {label: [values]} using known label names as delimiters."""
    parts = [p.strip() for p in res_div.get_text(separator="|", strip=True).split("|") if p.strip()]
    fields: dict[str, list[str]] = {}
    current_label: str | None = None
    current_values: list[str] = []
    for part in parts:
        if part in _KNOWN_RES_LABELS:
            if current_label is not None:
                fields[current_label] = current_values
            current_label = part
            current_values = []
        elif current_label is not None:
            current_values.append(part)
    if current_label is not None:
        fields[current_label] = current_values
    return fields

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

        # Extract judgment type prefix from court_full (e.g. "Postanowienie WSA w Warszawie")
        _type_match = re.match(
            r'^(Wyrok|Postanowienie|Uchwała|Zarządzenie|Uzasadnienie)\s+',
            court_full, re.IGNORECASE
        )
        judgment_type_from_header = _type_match.group(1).lower() if _type_match else None
        if _type_match:
            court_full = court_full[_type_match.end():].strip()

        res_div = soup.find("div", class_="res-div-list")
        date = None
        city = None
        judgment_type = judgment_type_from_header
        is_final = None
        keywords: list[str] = []
        related_case_numbers: list[str] = []

        if res_div:
            fields = _parse_res_div_fields(res_div)

            date_vals = fields.get("Data orzeczenia") or []
            if date_vals and re.match(r"\d{4}-\d{2}-\d{2}", date_vals[0]):
                date = date_vals[0]

            court_vals = fields.get("Sąd") or []
            if court_vals:
                city_m = re.search(r"w\s+(\w+(?:\s+\w+)?)\s*$", court_vals[0])
                if city_m:
                    city = city_m.group(1).strip()

            type_vals = fields.get("Rodzaj orzeczenia") or []
            if type_vals:
                judgment_type = type_vals[0].strip().lower()
            # judgment_type_from_header already set as default above

            # Prawomocność: osobne pole lub embedded w wartościach "Data orzeczenia"
            final_candidates = (fields.get("Prawomocność") or []) + (fields.get("Data orzeczenia") or [])
            for candidate in final_candidates:
                raw = candidate.strip().lower()
                if "nieprawomocn" in raw:
                    is_final = "nieprawomocny"
                    break
                if "prawomocn" in raw:
                    is_final = "prawomocny"
                    break

            keywords = [k.strip() for k in (fields.get("Hasła tematyczne") or []) if k.strip()]

            related_case_numbers = [
                c.strip() for c in (fields.get("Powiązane") or [])
                if c.strip() and re.search(r"\d+/\d{2,4}", c)
            ]

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
            "keywords": keywords,
            "doc_id": doc_id,
            "source_url": url,
            "source": "nsa",
            "legal_area": "administracyjne",
            "regulations": regulations,
            "judgment_type": judgment_type,
            "is_final": is_final,
            "related_case_numbers": related_case_numbers,
        }

    def scrape_range(self, date_from: str, date_to: str, limit: int = 500) -> list[dict]:
        results = []
        page = 1

        # Set server-side date filter via session POST
        try:
            self.session.get(f"{BASE_URL}/cbo/query", timeout=15)
            self.session.post(
                f"{BASE_URL}/cbo/search",
                data={"odDaty": date_from, "doDaty": date_to, "submit": "Szukaj"},
                timeout=15,
            )
            logger.info("NSA session date filter set: %s – %s", date_from, date_to)
        except requests.RequestException as e:
            logger.error("Failed to init NSA search session: %s", e)
            return results

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
                    results.append(judgment)
                    logger.info("Scraped %s date=%s (%d/%d)", judgment["case_number"], judgment.get("date", "?"), len(results), limit)
                time.sleep(self.delay)

            page += 1

        return results
