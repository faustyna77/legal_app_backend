import io
import logging
import time
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://api.sejm.gov.pl/eli"
PUBLISHER = "DU"


def _extract_text_from_pdf(pdf_bytes: bytes) -> str | None:
    try:
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(pdf_bytes))
    except Exception as e:
        logger.warning("PDF extraction failed: %s", e)
        return None


class ISAPScraper:
    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})

    def fetch_years(self) -> list[int]:
        r = self.session.get(f"{BASE_URL}/acts/{PUBLISHER}", timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("years", [])

    def fetch_acts_for_year(self, year: int) -> list[dict]:
        r = self.session.get(f"{BASE_URL}/acts/{PUBLISHER}/{year}", timeout=15)
        r.raise_for_status()
        return r.json().get("items", [])

    def fetch_act_detail(self, address: str) -> dict | None:
        try:
            r = self.session.get(f"{BASE_URL}/acts/{address}", timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error("Failed to fetch act %s: %s", address, e)
            return None

    def fetch_act_text_html(self, address: str) -> str | None:
        html_types = ["H", "3", "2"]
        for t in html_types:
            url = f"https://isap.sejm.gov.pl/isap.nsf/download.xsp?id={address}&type={t}"
            try:
                r = self.session.get(url, timeout=20, allow_redirects=True)
                ct = r.headers.get("Content-Type", "")
                if r.status_code == 200 and "text/html" in ct and "Request Rejected" not in r.text[:200]:
                    return r.text
            except requests.RequestException:
                pass
            time.sleep(self.delay)
        return None

    def fetch_act_text_pdf(self, address: str) -> str | None:
        pdf_types = ["T", "O", "I"]
        for t in pdf_types:
            url = f"https://isap.sejm.gov.pl/isap.nsf/download.xsp?id={address}&type={t}"
            try:
                r = self.session.get(url, timeout=30, allow_redirects=True)
                ct = r.headers.get("Content-Type", "")
                if r.status_code == 200 and "pdf" in ct.lower() and "Request Rejected" not in r.content[:50].decode("utf-8", errors="ignore"):
                    text = _extract_text_from_pdf(r.content)
                    if text and len(text.strip()) > 100:
                        return text
            except requests.RequestException:
                pass
            time.sleep(self.delay)
        return None

    @staticmethod
    def _split_paragraphs(article_number: str, content: str) -> list[dict]:
        import re
        parts = re.split(r"(?=§\s*\d+[a-z]?\.)", content)
        if len(parts) <= 1:
            return [{"number": article_number, "paragraph": None, "content": content}]
        result = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            m = re.match(r"(§\s*\d+[a-z]?\.)\s*", part)
            if m:
                para = m.group(1).strip()
                para_content = part[m.end():].strip()
                result.append({"number": article_number, "paragraph": para, "content": para_content or part})
            else:
                result.append({"number": article_number, "paragraph": None, "content": part})
        return result

    def parse_articles_from_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        articles = []

        for tag in soup.find_all(["div", "p", "article"], class_=lambda c: c and ("art" in c.lower() or "article" in c.lower())):
            num_tag = tag.find(class_=lambda c: c and ("art-num" in c or "num" in c)) or tag.find("b")
            content_tag = tag.find(class_=lambda c: c and "content" in c) or tag
            if num_tag and content_tag:
                num = num_tag.get_text(strip=True)
                content = content_tag.get_text(separator="\n", strip=True)
                articles.extend(self._split_paragraphs(num, content))

        if not articles:
            for tag in soup.find_all(["h3", "h4"], string=lambda t: t and ("Art." in str(t) or "art." in str(t))):
                num = tag.get_text(strip=True)
                content_parts = []
                for sib in tag.find_next_siblings():
                    if sib.name in ["h3", "h4"]:
                        break
                    content_parts.append(sib.get_text(separator="\n", strip=True))
                if content_parts:
                    content = "\n".join(content_parts)
                    articles.extend(self._split_paragraphs(num, content))

        return articles

    @staticmethod
    def parse_articles_from_text(text: str) -> list[dict]:
        import re
        articles = []
        pattern = re.compile(r"(Art\.\s*\d+[a-z]?\.?)", re.IGNORECASE)
        parts = pattern.split(text)
        i = 1
        while i < len(parts) - 1:
            num = parts[i].strip().rstrip(".")
            content = parts[i + 1].strip()
            if content:
                articles.append({"number": num, "paragraph": None, "content": content[:2000]})
            i += 2
        return articles

    def search_acts(self, keyword: str, limit: int = 50, years: list[int] | None = None, act_types: list[str] | None = None) -> list[dict]:
        act_types = act_types or ["Ustawa", "Kodeks", "Rozporządzenie"]
        results = []

        try:
            all_years = years or self.fetch_years()
        except Exception as e:
            logger.error("Failed to fetch years: %s", e)
            return []

        for year in sorted(all_years, reverse=True):
            if len(results) >= limit:
                break
            try:
                items = self.fetch_acts_for_year(year)
            except Exception as e:
                logger.warning("Failed to fetch year %d: %s", year, e)
                continue

            for item in items:
                if len(results) >= limit:
                    break

                title = item.get("title", "")
                act_type = item.get("type", "")

                if keyword.lower() not in title.lower():
                    continue
                if act_type not in act_types:
                    continue

                address = item.get("address")
                if not address:
                    continue

                detail = self.fetch_act_detail(address)
                if not detail:
                    time.sleep(self.delay)
                    continue

                articles = []
                if detail.get("textHTML"):
                    html = self.fetch_act_text_html(address)
                    if html:
                        articles = self.parse_articles_from_html(html)

                if not articles and detail.get("textPDF"):
                    pdf_text = self.fetch_act_text_pdf(address)
                    if pdf_text:
                        articles = self.parse_articles_from_text(pdf_text)

                if not articles:
                    articles = [{"number": "Art. 1", "paragraph": None, "content": f"{title}\nTyp: {act_type}\nStatus: {detail.get('status', '')}\nData wejścia w życie: {detail.get('entryIntoForce', detail.get('promulgation', ''))}"}]

                act = {
                    "title": title,
                    "type": act_type.lower(),
                    "source_url": f"https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id={address}",
                    "articles": articles,
                    "year": item.get("year"),
                    "isap_id": address,
                    "journal_number": f"Dz.U. {item.get('year')} poz. {item.get('pos')}" if item.get("pos") else None,
                }
                results.append(act)
                logger.info("Scraped act: %s (%d articles)", title[:60], len(articles))
                time.sleep(self.delay)

        logger.info("Total acts scraped: %d", len(results))
        return results
