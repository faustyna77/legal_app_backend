import html
import logging
import re
import time
import requests
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

BASE_URL = "https://www.saos.org.pl/api"

_LEGAL_AREA_KEYWORDS = [
    ("Prawo pracy", ["prawo pracy", "kodeks pracy", "wynagrodzenie", "pracownik", "pracodawca", "urlop", "zwolnienie", "stosunek pracy"]),
    ("Prawo cywilne", ["prawo cywilne", "kodeks cywilny", "umowa", "odszkodowanie", "własność", "spadek", "zadośćuczynienie", "dobra osobiste", "najem", "dzierżawa"]),
    ("Prawo karne", ["prawo karne", "kodeks karny", "przestępstwo", "kara", "skazanie", "oskarżony", "wykroczenie"]),
    ("Prawo administracyjne", ["prawo administracyjne", "postępowanie administracyjne", "decyzja administracyjna", "organ administracji", "skarga"]),
    ("Prawo podatkowe", ["podatek", "vat", "pit", "cit", "ordynacja podatkowa", "urząd skarbowy", "zobowiązanie podatkowe"]),
    ("Prawo gospodarcze", ["prawo gospodarcze", "spółka", "przedsiębiorca", "działalność gospodarcza", "krs", "handlowy"]),
    ("Prawo rodzinne", ["prawo rodzinne", "alimenty", "rozwód", "władza rodzicielska", "małżeństwo", "kuratela"]),
    ("Prawo ubezpieczeń", ["ubezpieczenie", "zus", "renta", "emerytura", "zasiłek", "ubezpieczenie społeczne"]),
    ("Prawo budowlane", ["prawo budowlane", "budowa", "pozwolenie na budowę", "roboty budowlane"]),
]

_CASE_PREFIX_TO_AREA = {
    "ACa": "Prawo cywilne",
    "AKa": "Prawo karne",
    "APa": "Prawo pracy",
    "AUa": "Prawo ubezpieczeń",
    "AGa": "Prawo gospodarcze",
    "Aca": "Prawo cywilne",
    "C":   "Prawo cywilne",
    "GC":  "Prawo gospodarcze",
    "PC":  "Prawo pracy",
    "U":   "Prawo ubezpieczeń",
    "FSK": "Prawo podatkowe",
    "FPS": "Prawo podatkowe",
    "OSK": "Prawo administracyjne",
    "OPS": "Prawo administracyjne",
    "SA":  "Prawo administracyjne",
    "II SA": "Prawo administracyjne",
}

_CITY_LOCATIVE = {
    "warszawie": "Warszawa",
    "krakowie": "Kraków",
    "łodzi": "Łódź",
    "wrocławiu": "Wrocław",
    "poznaniu": "Poznań",
    "gdańsku": "Gdańsk",
    "szczecinie": "Szczecin",
    "bydgoszczy": "Bydgoszcz",
    "lublinie": "Lublin",
    "białymstoku": "Białystok",
    "rzeszowie": "Rzeszów",
    "katowicach": "Katowice",
    "kielcach": "Kielce",
    "olsztynie": "Olsztyn",
    "opolu": "Opole",
    "toruniu": "Toruń",
    "gorzowie wielkopolskim": "Gorzów Wielkopolski",
    "zielonej górze": "Zielona Góra",
}


def _classify_legal_area(keywords: list[str], court_name: str, case_number: str = "") -> str | None:
    if case_number:
        # strip Roman numeral prefix: "I ACa 1002/22" -> "ACa 1002/22"
        stripped = re.sub(r"^(I{1,3}|IV|VI{0,3}|IX|X{0,2}I{0,3}|V)\s+", "", case_number.strip(), flags=re.IGNORECASE)
        for key, area in _CASE_PREFIX_TO_AREA.items():
            if stripped.startswith(key + " ") or stripped.startswith(key + "/"):
                return area

    combined = " ".join(keywords).lower() + " " + court_name.lower()
    for area, terms in _LEGAL_AREA_KEYWORDS:
        if any(t in combined for t in terms):
            return area
    return None


def _extract_city_from_court(court_name: str) -> str | None:
    m = re.search(r"\bw\s+([A-ZŁŚĄĘ][a-złśąęóżźćńA-ZŁŚĄĘ\-]+(?:\s+[A-ZŁŚĄĘ][a-złśąęóżźćńA-ZŁŚĄĘ]+)?)\s*$", court_name)
    if m:
        raw = m.group(1).strip()
        return _CITY_LOCATIVE.get(raw.lower(), raw)
    return None


_JUDGMENT_TYPE_MAP = {
    "SENTENCE": "wyrok",
    "DECISION": "postanowienie",
    "RESOLUTION": "uchwała",
    "REASONS": "uzasadnienie",
    "REGULATION": "zarządzenie",
    "ORDER_DISMISSING_APPEAL": "postanowienie",
    "ORDER": "postanowienie",
}

# Court types that are always final (last instance)
_ALWAYS_FINAL_COURT_TYPES = {"SUPREME", "CONSTITUTIONAL_TRIBUNAL", "NATIONAL_APPEAL_CHAMBER"}

_IS_FINAL_TEXT_PATTERN = re.compile(
    r'(orzeczenie|wyrok|postanowienie)\s+(jest\s+)?nieprawomocn',
    re.IGNORECASE,
)
_IS_PRAWOMOCNY_TEXT_PATTERN = re.compile(
    r'(orzeczenie|wyrok|postanowienie)\s+(jest\s+)?prawomocn',
    re.IGNORECASE,
)


def _infer_is_final(court_type_raw: str, court_name: str, content: str) -> str | None:
    ct = (court_type_raw or "").upper()
    cn = (court_name or "").lower()

    if ct in _ALWAYS_FINAL_COURT_TYPES:
        return "prawomocny"
    if "sąd apelacyjny" in cn or "apelacyjny" in cn:
        return "prawomocny"

    # Parse text for explicit finality statements
    if content:
        if _IS_FINAL_TEXT_PATTERN.search(content):
            return "nieprawomocny"
        if _IS_PRAWOMOCNY_TEXT_PATTERN.search(content):
            return "prawomocny"

    return None

_COURT_TYPE_MAP = {
    "COMMON": "Sąd powszechny",
    "SUPREME": "Sąd Najwyższy",
    "ADMINISTRATIVE": "Sąd administracyjny",
    "CONSTITUTIONAL_TRIBUNAL": "Trybunał Konstytucyjny",
    "NATIONAL_APPEAL_CHAMBER": "Krajowa Izba Odwoławcza",
    "MILITARY": "Sąd wojskowy",
}


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def get_text(self) -> str:
        text = " ".join(self._parts)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()


def _strip_html(raw: str) -> str:
    if not raw:
        return raw
    raw = html.unescape(raw)
    stripper = _HTMLStripper()
    stripper.feed(raw)
    return stripper.get_text()


class SAOSScraper:
    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "LegalResearch/1.0"})

    def fetch_judgments(
        self,
        page_number: int = 0,
        page_size: int = 20,
        court_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        keyword: str | None = None,
    ) -> dict:
        params: dict = {"pageNumber": page_number, "pageSize": page_size}
        if court_type:
            params["courtType"] = court_type
        if date_from:
            params["judgmentDateFrom"] = date_from
        if date_to:
            params["judgmentDateTo"] = date_to
        if keyword:
            params["all"] = keyword

        response = self.session.get(f"{BASE_URL}/search/judgments", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def fetch_judgment_detail(self, href: str) -> dict | None:
        try:
            response = self.session.get(href, timeout=30)
            response.raise_for_status()
            return response.json().get("data", {})
        except requests.RequestException as e:
            logger.error("Failed to fetch detail %s: %s", href, e)
            return None

    def extract_thesis(self, detail: dict) -> str | None:
        for field in ("summary", "theses", "thesis", "reasoning"):
            val = detail.get(field)
            if val and isinstance(val, str) and val.strip():
                return val.strip()[:2000]
            if val and isinstance(val, list) and val:
                return " ".join(str(v) for v in val).strip()[:2000]
        return None

    def extract_regulations(self, judgment_data: dict) -> list[dict]:
        regulations = []
        for reg in judgment_data.get("referencedRegulations", []):
            regulations.append(
                {
                    "act_title": reg.get("journalTitle", ""),
                    "act_year": reg.get("journalYear"),
                    "journal_no": reg.get("journalNo"),
                    "articles": [art.get("text", "") for art in reg.get("referencedArticles", [])],
                }
            )
        return regulations

    def _parse_item(self, item: dict, detail: dict | None = None) -> dict:
        case_numbers = [c.get("caseNumber", "") for c in item.get("courtCases", [])]
        case_number = case_numbers[0] if case_numbers else str(item.get("id", ""))

        division = item.get("division") or {}
        court_obj = division.get("court") or {}
        court_name = court_obj.get("name") or division.get("name") or item.get("courtType", "UNKNOWN")

        keywords = item.get("keywords") or []
        city = _extract_city_from_court(court_name)
        legal_area = _classify_legal_area(keywords, court_name, case_number)

        content = item.get("textContent") or ""
        if content:
            content = _strip_html(content)
        thesis = None
        regulations = []

        if detail:
            raw_content = detail.get("textContent") or ""
            content = _strip_html(raw_content) if raw_content else content
            thesis = self.extract_thesis(detail)
            regulations = self.extract_regulations(detail)
            if thesis:
                thesis = _strip_html(thesis)
            if not legal_area:
                detail_keywords = detail.get("keywords") or keywords
                legal_area = _classify_legal_area(detail_keywords, court_name, case_number)

        raw_court_type = item.get("courtType") or ""
        mapped_court_type = _COURT_TYPE_MAP.get(raw_court_type.upper(), raw_court_type)

        raw_judgment_type = item.get("judgmentType") or ""
        judgment_type = _JUDGMENT_TYPE_MAP.get(raw_judgment_type.upper()) or (raw_judgment_type.lower() if raw_judgment_type else None)

        raw_href = item.get("href") or ""
        web_url = (
            raw_href.replace("/api/judgments/", "/judgments/")
            if raw_href
            else f"https://www.saos.org.pl/judgments/{item.get('id')}"
        )

        is_final = _infer_is_final(raw_court_type, court_name, content)

        return {
            "saos_id": item.get("id"),
            "case_number": case_number,
            "court": court_name,
            "court_type": mapped_court_type,
            "date": item.get("judgmentDate"),
            "content": content,
            "thesis": thesis,
            "keywords": keywords,
            "city": city,
            "legal_area": legal_area,
            "doc_id": str(item.get("id")) if item.get("id") else None,
            "source_url": web_url,
            "source": "saos",
            "regulations": regulations,
            "judgment_type": judgment_type,
            "is_final": is_final,
        }

    def scrape_range(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        court_type: str | None = None,
        keyword: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        results = []
        page = 0
        page_size = min(20, limit)

        while len(results) < limit:
            try:
                data = self.fetch_judgments(
                    page_number=page,
                    page_size=page_size,
                    court_type=court_type,
                    date_from=date_from,
                    date_to=date_to,
                    keyword=keyword,
                )
            except requests.RequestException as e:
                logger.error("SAOS API error on page %d: %s", page, e)
                break

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                if len(results) >= limit:
                    break

                detail = None
                detail_url = item.get("href")
                if detail_url:
                    detail = self.fetch_judgment_detail(detail_url)
                    time.sleep(self.delay)

                parsed = self._parse_item(item, detail)

                if not parsed["content"]:
                    logger.debug("Skipping %s - no content", parsed["case_number"])
                    continue

                results.append(parsed)
                logger.info("Scraped SAOS %s (%d/%d)", parsed["case_number"], len(results), limit)

            total = (data.get("info") or {}).get("totalResults") or 0
            if total > 0 and (page + 1) * page_size >= total:
                break
            if len(items) < page_size:
                break

            page += 1
            time.sleep(self.delay)

        return results
