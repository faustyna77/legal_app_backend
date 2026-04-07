import logging
import re
import time
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://arslege.pl"


class ArslegeScraper:
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    def _get_soup(self, url: str) -> BeautifulSoup | None:
        try:
            r = self.session.get(url, timeout=15)
            r.raise_for_status()
            return BeautifulSoup(r.content, "html.parser")
        except requests.RequestException as e:
            logger.error("Failed to fetch %s: %s", url, e)
            return None

    def _get_section_urls(self, start_url: str) -> list[str]:
        soup = self._get_soup(start_url)
        if not soup:
            return []
        toc = soup.find("div", class_="spis_tresci")
        if not toc:
            logger.warning("No TOC found at %s", start_url)
            return []
        seen = set()
        urls = []
        for a in toc.find_all("a", href=True):
            href = a["href"]
            if href not in seen:
                seen.add(href)
                urls.append(BASE_URL + href if href.startswith("/") else href)
        return urls

    def _parse_section(self, url: str) -> list[dict]:
        soup = self._get_soup(url)
        if not soup:
            return []
        articles = []
        for art_tag in soup.find_all("article", class_="art_box"):
            h3 = art_tag.find("h3", class_="art_indeks")
            tresc = art_tag.find("div", class_="art_tresc")
            if not h3 or not tresc:
                continue
            title = h3.get_text(strip=True)
            content = tresc.get_text(separator="\n", strip=True)
            number_m = re.match(r"(Art\.\s*\d+[a-z\d]*\.?)", title)
            number = number_m.group(1).strip().rstrip(".") if number_m else title
            articles.append({
                "number": number,
                "paragraph": None,
                "content": f"{title}\n{content}",
                "source_url": url,
            })
        return articles

    def _get_act_meta(self, start_url: str) -> dict:
        soup = self._get_soup(start_url)
        title = ""
        act_type = "ustawa"
        if soup:
            textel = soup.find("div", class_="textelement")
            if textel:
                raw = textel.get_text(strip=True)
                title = raw
                if "kodeks" in raw.lower():
                    act_type = "kodeks"
                elif "rozporządzenie" in raw.lower():
                    act_type = "rozporządzenie"
        return {"title": title, "type": act_type}

    def scrape_act(self, start_url: str) -> dict | None:
        """
        Scrape a full legal act from arslege.pl.

        Args:
            start_url: URL of any section of the act, e.g.
                       https://arslege.pl/kodeks-postepowania-cywilnego/k14/s583/

        Returns:
            dict with keys: title, type, source_url, articles
            or None on failure.
        """
        logger.info("Fetching TOC from %s", start_url)
        section_urls = self._get_section_urls(start_url)
        if not section_urls:
            return None

        meta = self._get_act_meta(start_url)
        logger.info("Act: %s | %d sections to scrape", meta["title"][:80], len(section_urls))

        all_articles = []
        seen_numbers: set[str] = set()

        for i, url in enumerate(section_urls):
            articles = self._parse_section(url)
            new = 0
            for art in articles:
                key = art["number"]
                if key not in seen_numbers:
                    seen_numbers.add(key)
                    all_articles.append(art)
                    new += 1
            if articles:
                logger.info("Section %d/%d: %s -> %d articles (%d new)",
                            i + 1, len(section_urls), url.split("/")[-2], len(articles), new)
            time.sleep(self.delay)

        logger.info("Scraped %d unique articles from %s", len(all_articles), meta["title"][:60])
        return {
            "title": meta["title"],
            "type": meta["type"],
            "source_url": start_url,
            "articles": all_articles,
        }
