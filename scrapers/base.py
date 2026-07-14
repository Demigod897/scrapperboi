import asyncio
import hashlib
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from urllib.robotparser import RobotFileParser

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings

logger = structlog.get_logger(__name__)


class DocumentType(Enum):
    PDF = "pdf"
    HTML = "html"
    IMAGE = "image"


@dataclass
class ScrapedDocument:
    """A single document fetched from a regulator's website."""

    source_url: str
    regulator: str
    document_type: DocumentType
    raw_content: bytes
    content_hash: str
    scraped_at: datetime
    title: str = ""
    metadata: dict = field(default_factory=dict)


class AbstractBaseScraper(ABC):
    """Base class for all regulator scrapers.

    Provides polite fetching, rate limiting, content hashing, and retry logic.
    Every regulator scraper inherits this and implements:
      - discover_documents(): find document URLs from listing pages
      - scrape(): full scrape cycle
      - parse_listing_page(): extract links from a listing page
    """

    def __init__(self, config: dict):
        self.config = config
        self.regulator_code = config.get("code", "UNKNOWN")
        self.base_url = config.get("base_url", "")
        self.min_delay = config.get("min_delay_sec", settings.scrape_default_min_delay)
        self.max_delay = config.get("max_delay_sec", settings.scrape_default_max_delay)
        self.max_concurrent = config.get("max_concurrent", 1)
        self.retry_attempts = config.get("retry_attempts", 3)
        self._robot_parser: RobotFileParser | None = None
        self._robots_fetched: bool = False
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": settings.scrape_user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                follow_redirects=True,
                verify=True,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _polite_delay(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug("polite_delay", regulator=self.regulator_code, delay_sec=round(delay, 1))
        await asyncio.sleep(delay)

    async def _check_robots(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        if not self.config.get("respect_robots_txt", True):
            return True

        if not self._robots_fetched:
            self._robots_fetched = True
            robots_url = f"{self.base_url}/robots.txt"
            try:
                client = await self._get_client()
                resp = await client.get(robots_url)
                if resp.status_code == 200:
                    self._robot_parser = RobotFileParser()
                    self._robot_parser.parse(resp.text.splitlines())
                # non-200 (incl. 418): _robot_parser stays None = allow all
            except Exception:
                pass  # _robot_parser stays None = allow all

        if self._robot_parser is None:
            return True

        return self._robot_parser.can_fetch(settings.scrape_user_agent, url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
    async def fetch(self, url: str) -> httpx.Response:
        """Fetch a URL with polite delay and retry logic."""
        if not await self._check_robots(url):
            logger.warning("robots_blocked", url=url, regulator=self.regulator_code)
            raise PermissionError(f"URL blocked by robots.txt: {url}")

        await self._polite_delay()
        client = await self._get_client()
        logger.info("fetching", url=url, regulator=self.regulator_code)
        resp = await client.get(url)
        resp.raise_for_status()
        return resp

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
    async def fetch_post(self, url: str, data: dict) -> httpx.Response:
        """POST request with polite delay and retry."""
        await self._polite_delay()
        client = await self._get_client()
        logger.info("posting", url=url, regulator=self.regulator_code)
        resp = await client.post(url, data=data)
        resp.raise_for_status()
        return resp

    async def fetch_binary(self, url: str) -> bytes:
        """Fetch binary content (PDFs, images)."""
        resp = await self.fetch(url)
        return resp.content

    @staticmethod
    def content_hash(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def make_absolute_url(self, path: str) -> str:
        """Convert relative URL to absolute."""
        if path.startswith("http"):
            return path
        if path.startswith("/"):
            return f"{self.base_url}{path}"
        return f"{self.base_url}/{path}"

    @abstractmethod
    async def discover_documents(self) -> list[dict]:
        """Discover document URLs from listing pages.

        Returns list of dicts with at minimum:
          - url: str
          - title: str (optional)
          - date_hint: str (optional, for ordering)
        """
        ...

    @abstractmethod
    async def scrape(self) -> list[ScrapedDocument]:
        """Full scrape cycle: discover + fetch + package."""
        ...

    @abstractmethod
    def parse_listing_page(self, html: str) -> list[dict]:
        """Extract document links from a listing/index page."""
        ...
