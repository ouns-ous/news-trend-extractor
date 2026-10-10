"""Multi-source news feed scraper supporting RSS 2.0, Atom feeds, and custom HTML scraping."""

from __future__ import annotations
from datetime import datetime
from email.utils import parsedate_to_datetime
import html
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from news_extractor.models import Article
from news_extractor.config import SourceConfig

try:
    from bs4 import BeautifulSoup  # type: ignore
    HAS_BEAUTIFUL_SOUP = True
except ImportError:
    HAS_BEAUTIFUL_SOUP = False

logger = logging.getLogger(__name__)


class MultiSourceScraper:
    """Engine for fetching and parsing news stories across diverse formats."""

    def __init__(
        self,
        user_agent: str = "NewsPulseBot/1.0 (+https://github.com/ouns-ous/news-trend-extractor)",
        timeout_seconds: int = 10,
        fixtures_dir: Optional[Path] = None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.fixtures_dir = fixtures_dir or (Path(__file__).resolve().parent.parent / "fixtures")

    def _clean_text(self, text: Optional[str]) -> str:
        """Strip HTML tags, unescape HTML entities, and collapse excess whitespace."""
        if not text:
            return ""
        # Remove HTML tags if any exist
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = html.unescape(clean)
        return " ".join(clean.split())

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse RFC 822/2822 or ISO 8601 timestamps gracefully."""
        if not date_str:
            return None
        date_str = date_str.strip()
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            pass

        # Attempt ISO 8601 parsing
        try:
            clean_iso = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_iso)
        except Exception:
            pass

        return None

    def fetch_url(self, url: str) -> str:
        """Fetch remote URL contents with realistic browser headers and timeout."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")

    def parse_rss(
        self, xml_content: str, source_name: str, default_category: str = "General", max_items: int = 30
    ) -> List[Article]:
        """Parse RSS 2.0 XML document into Article instances."""
        articles: List[Article] = []
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.warning("Failed to parse RSS XML for %s: %s", source_name, e)
            return articles

        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else root.findall(".//item")

        for item in items[:max_items]:
            title_elem = item.find("title")
            link_elem = item.find("link")
            desc_elem = item.find("description")
            pub_elem = item.find("pubDate")
            cat_elem = item.find("category")
            creator_elem = item.find("{http://purl.org/dc/elements/1.1/}creator")

            title = self._clean_text(title_elem.text if title_elem is not None else "")
            if not title:
                continue

            link = (link_elem.text or "").strip() if link_elem is not None else ""
            summary = self._clean_text(desc_elem.text if desc_elem is not None else "")
            published_at = self._parse_date(pub_elem.text if pub_elem is not None else None)
            category = self._clean_text(cat_elem.text) if cat_elem is not None and cat_elem.text else default_category
            author = self._clean_text(creator_elem.text) if creator_elem is not None and creator_elem.text else ""

            articles.append(
                Article(
                    title=title,
                    url=link,
                    source=source_name,
                    summary=summary,
                    category=category,
                    author=author,
                    published_at=published_at,
                )
            )

        return articles

    def parse_atom(
        self, xml_content: str, source_name: str, default_category: str = "General", max_items: int = 30
    ) -> List[Article]:
        """Parse Atom feed XML document into Article instances."""
        articles: List[Article] = []
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.warning("Failed to parse Atom XML for %s: %s", source_name, e)
            return articles

        def _local_tag(elem: ET.Element) -> str:
            return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        # Find all entry elements regardless of namespace prefix
        entries = [elem for elem in root.iter() if _local_tag(elem) == "entry"]

        for entry in entries[:max_items]:
            title_text = ""
            summary_text = ""
            updated_text = ""
            link = ""

            for child in entry:
                tag = _local_tag(child)
                if tag == "title" and child.text:
                    title_text = child.text
                elif tag in ("summary", "content") and child.text and not summary_text:
                    summary_text = child.text
                elif tag in ("updated", "published") and child.text:
                    updated_text = child.text
                elif tag == "link":
                    href = child.attrib.get("href", "")
                    rel = child.attrib.get("rel", "alternate")
                    if rel in ("alternate", "") and href:
                        link = href
                elif tag == "id" and not link and child.text:
                    link = child.text.strip()

            title = self._clean_text(title_text)
            if not title:
                continue

            summary = self._clean_text(summary_text)
            published_at = self._parse_date(updated_text)

            articles.append(
                Article(
                    title=title,
                    url=link,
                    source=source_name,
                    summary=summary,
                    category=default_category,
                    published_at=published_at,
                )
            )

        return articles

    def parse_html(
        self, html_content: str, source_name: str, default_category: str = "General", selector: Optional[str] = None
    ) -> List[Article]:
        """Extract headline articles from HTML markup."""
        articles: List[Article] = []
        if HAS_BEAUTIFUL_SOUP:
            soup = BeautifulSoup(html_content, "html.parser")
            cards = soup.select(selector or "article, .news-card, .story")
            if not cards:
                # Fallback to headline links
                links = soup.find_all("a")
                for a in links:
                    text = self._clean_text(a.get_text())
                    href = a.get("href", "")
                    if len(text.split()) >= 4 and href:
                        articles.append(
                            Article(
                                title=text,
                                url=href,
                                source=source_name,
                                summary="",
                                category=default_category,
                            )
                        )
                return articles

            for card in cards:
                headline_elem = card.find(["h1", "h2", "h3", "h4", "a"])
                link_elem = card.find("a")
                p_elem = card.find("p")
                cat_elem = card.find(class_=re.compile(r"category|tag|label", re.I))

                title = self._clean_text(headline_elem.get_text() if headline_elem else "")
                if not title or len(title.split()) < 3:
                    continue

                link = link_elem.get("href", "") if link_elem else ""
                summary = self._clean_text(p_elem.get_text() if p_elem else "")
                category = self._clean_text(cat_elem.get_text() if cat_elem else default_category)

                articles.append(
                    Article(
                        title=title,
                        url=link,
                        source=source_name,
                        summary=summary,
                        category=category or default_category,
                    )
                )
        else:
            # Simple regex fallback if BeautifulSoup is missing
            pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
            for match in pattern.finditer(html_content):
                link, raw_title = match.groups()
                title = self._clean_text(raw_title)
                if len(title.split()) >= 4:
                    articles.append(
                        Article(
                            title=title,
                            url=link,
                            source=source_name,
                            category=default_category,
                        )
                    )

        return articles

    def fetch_source(self, source: SourceConfig) -> List[Article]:
        """Fetch and parse a single configured source."""
        content = self.fetch_url(source.url)
        feed_type = source.feed_type.lower()

        if feed_type == "rss":
            return self.parse_rss(content, source.name, source.category, source.max_items)
        elif feed_type == "atom":
            return self.parse_atom(content, source.name, source.category, source.max_items)
        elif feed_type == "html":
            return self.parse_html(content, source.name, source.category, source.html_selector)
        else:
            # Auto-detect RSS vs Atom
            if "<rss" in content or "<channel" in content:
                return self.parse_rss(content, source.name, source.category, source.max_items)
            elif "<feed" in content:
                return self.parse_atom(content, source.name, source.category, source.max_items)
            return self.parse_html(content, source.name, source.category, source.html_selector)

    def fetch_offline_fixtures(self) -> List[Article]:
        """Load articles deterministically from local XML and HTML fixtures."""
        articles: List[Article] = []

        tech_file = self.fixtures_dir / "tech_feed.xml"
        if tech_file.exists():
            xml_text = tech_file.read_text(encoding="utf-8")
            articles.extend(self.parse_rss(xml_text, "TechPulse (Offline)", "Technology"))

        world_file = self.fixtures_dir / "world_feed.xml"
        if world_file.exists():
            xml_text = world_file.read_text(encoding="utf-8")
            articles.extend(self.parse_rss(xml_text, "Global Dispatch (Offline)", "World"))

        html_file = self.fixtures_dir / "custom_page.html"
        if html_file.exists():
            html_text = html_file.read_text(encoding="utf-8")
            articles.extend(self.parse_html(html_text, "Daily Chronicle (Offline)", "General"))

        return articles

    def scrape_all(
        self, sources: List[SourceConfig], offline: bool = False
    ) -> Tuple[List[Article], List[str]]:
        """Scrape all enabled sources, returning collected articles and encountered errors."""
        if offline:
            return self.fetch_offline_fixtures(), []

        all_articles: List[Article] = []
        errors: List[str] = []

        for source in sources:
            if not source.enabled:
                continue
            try:
                found = self.fetch_source(source)
                all_articles.extend(found)
            except Exception as e:
                err_msg = f"Failed to scrape {source.name} ({source.url}): {e}"
                logger.warning(err_msg)
                errors.append(err_msg)

        # If live scraping failed on all sources (e.g. no internet), fallback cleanly to fixtures
        if not all_articles and errors:
            logger.info("Falling back to local offline fixtures due to network errors.")
            all_articles = self.fetch_offline_fixtures()

        return all_articles, errors
