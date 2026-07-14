import re
from datetime import datetime
from urllib.parse import urljoin

import structlog
from bs4 import BeautifulSoup

from scrapers.base import AbstractBaseScraper, DocumentType, ScrapedDocument

logger = structlog.get_logger(__name__)


class RBIScraper(AbstractBaseScraper):
    """Scraper for RBI penalty orders and press releases.

    RBI publishes penalty orders as press releases on rbi.org.in.
    The site uses ASP.NET with __VIEWSTATE-based pagination.
    Penalty-related press releases link to PDF orders.
    """

    PENALTY_SECTION = "P"  # Press release section for penalties
    LISTING_PATH = "/Scripts/BS_PressReleaseDisplay.aspx"

    def __init__(self, config: dict):
        super().__init__(config)
        self._viewstate_fields = [
            "__VIEWSTATE",
            "__VIEWSTATEGENERATOR",
            "__EVENTVALIDATION",
            "__EVENTTARGET",
            "__EVENTARGUMENT",
        ]

    def _build_listing_url(self) -> str:
        return f"{self.base_url}{self.LISTING_PATH}"

    def _extract_asp_fields(self, soup: BeautifulSoup) -> dict:
        """Extract ASP.NET hidden form fields for postback."""
        fields = {}
        for field_name in self._viewstate_fields:
            tag = soup.find("input", {"name": field_name})
            if tag:
                fields[field_name] = tag.get("value", "")
        return fields

    def _has_next_page(self, soup: BeautifulSoup) -> tuple[bool, str | None]:
        """Check if there's a next page link in the pagination."""
        # RBI uses GridView pagination with page number links
        pager = soup.find("tr", class_="pager") or soup.find("div", class_="pager")
        if not pager:
            # Try finding pagination by looking for page number links
            pager = soup.find("table")
            if pager:
                # Look for "Next" or ">" link
                next_link = pager.find("a", string=re.compile(r"(Next|>|>>|\.\.\.)", re.IGNORECASE))
                if next_link:
                    href = next_link.get("href", "")
                    # ASP.NET postback: javascript:__doPostBack('ctl00$...','Page$Next')
                    match = re.search(r"__doPostBack\('([^']+)','([^']+)'\)", href)
                    if match:
                        return True, match.group(0)
        return False, None

    def parse_listing_page(self, html: str) -> list[dict]:
        """Extract penalty order links from a listing page."""
        soup = BeautifulSoup(html, "lxml")
        documents = []

        # RBI press releases are typically in a table or list
        # Look for links containing penalty-related keywords
        penalty_keywords = [
            "penalty", "penalt", "fine", "monetary",
            "show cause", "direction", "enforcement",
        ]

        # Find all links on the page
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True).lower()
            href = link["href"]

            # Check if this is a penalty-related press release
            is_penalty = any(kw in text for kw in penalty_keywords)

            # Also check for PDF links that might be penalty orders
            is_pdf = href.lower().endswith(".pdf")

            if is_penalty or is_pdf:
                abs_url = self.make_absolute_url(href)
                # Try to extract date from surrounding context
                parent = link.find_parent("tr") or link.find_parent("div")
                date_hint = ""
                if parent:
                    date_match = re.search(
                        r"(\d{1,2}[./\-]\d{1,2}[./\-]\d{4}|\w+\s+\d{1,2},?\s+\d{4})",
                        parent.get_text(),
                    )
                    if date_match:
                        date_hint = date_match.group(1)

                documents.append({
                    "url": abs_url,
                    "title": link.get_text(strip=True),
                    "date_hint": date_hint,
                    "is_pdf": is_pdf,
                })

        logger.info(
            "parsed_listing_page",
            regulator=self.regulator_code,
            documents_found=len(documents),
        )
        return documents

    async def discover_documents(self) -> list[dict]:
        """Discover all penalty order URLs by paginating through the listing."""
        all_documents = []
        listing_url = self._build_listing_url()

        # Fetch first page
        logger.info("discovering_documents", regulator=self.regulator_code, url=listing_url)
        resp = await self.fetch(listing_url)
        html = resp.text
        soup = BeautifulSoup(html, "lxml")

        # Parse first page
        documents = self.parse_listing_page(html)
        all_documents.extend(documents)

        # Paginate using ASP.NET postbacks
        page_num = 1
        max_pages = 100  # safety limit

        while page_num < max_pages:
            has_next, postback = self._has_next_page(soup)
            if not has_next or not postback:
                break

            page_num += 1
            logger.info(
                "paginating",
                regulator=self.regulator_code,
                page=page_num,
            )

            # Build postback form data
            asp_fields = self._extract_asp_fields(soup)
            match = re.search(r"__doPostBack\('([^']+)','([^']+)'\)", postback)
            if match:
                asp_fields["__EVENTTARGET"] = match.group(1)
                asp_fields["__EVENTARGUMENT"] = match.group(2)

            try:
                resp = await self.fetch_post(listing_url, data=asp_fields)
                html = resp.text
                soup = BeautifulSoup(html, "lxml")
                documents = self.parse_listing_page(html)

                if not documents:
                    logger.info("no_more_documents", page=page_num)
                    break

                all_documents.extend(documents)
            except Exception as e:
                logger.error("pagination_failed", page=page_num, error=str(e))
                break

        # Deduplicate by URL
        seen_urls = set()
        unique_documents = []
        for doc in all_documents:
            if doc["url"] not in seen_urls:
                seen_urls.add(doc["url"])
                unique_documents.append(doc)

        logger.info(
            "discovery_complete",
            regulator=self.regulator_code,
            total_documents=len(unique_documents),
            pages_scraped=page_num,
        )
        return unique_documents

    async def _fetch_document(self, doc_info: dict) -> ScrapedDocument | None:
        """Fetch a single document and return ScrapedDocument."""
        url = doc_info["url"]
        try:
            if doc_info.get("is_pdf", False) or url.lower().endswith(".pdf"):
                # RBI CDN (rbidocs.rbi.org.in) blocks bot User-Agents; use browser UA
                client = await self._get_client()
                await self._polite_delay()
                resp = await client.get(url, headers={
                    "Referer": self.base_url,
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                })
                resp.raise_for_status()
                content = resp.content
                doc_type = DocumentType.PDF
            else:
                resp = await self.fetch(url)
                content = resp.content

                # Check if the press release page links to a PDF
                soup = BeautifulSoup(resp.text, "lxml")
                pdf_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.IGNORECASE))

                if pdf_links:
                    # Fetch the PDF; CDN blocks bot User-Agents
                    pdf_url = self.make_absolute_url(pdf_links[0]["href"])
                    cdn_client = await self._get_client()
                    await self._polite_delay()
                    pdf_resp = await cdn_client.get(pdf_url, headers={
                        "Referer": self.base_url,
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        ),
                    })
                    pdf_resp.raise_for_status()
                    content = pdf_resp.content
                    doc_type = DocumentType.PDF
                    url = pdf_url
                else:
                    doc_type = DocumentType.HTML

            return ScrapedDocument(
                source_url=url,
                regulator=self.regulator_code,
                document_type=doc_type,
                raw_content=content,
                content_hash=self.content_hash(content),
                scraped_at=datetime.utcnow(),
                title=doc_info.get("title", ""),
                metadata={
                    "date_hint": doc_info.get("date_hint", ""),
                    "original_listing_url": doc_info.get("url", ""),
                },
            )
        except Exception as e:
            logger.error(
                "fetch_document_failed",
                url=url,
                regulator=self.regulator_code,
                error=str(e),
            )
            return None

    async def scrape(self) -> list[ScrapedDocument]:
        """Full scrape: discover all penalty orders and fetch them."""
        logger.info("scrape_started", regulator=self.regulator_code)

        # Discover document URLs
        doc_infos = await self.discover_documents()

        # Fetch each document
        documents = []
        for doc_info in doc_infos:
            doc = await self._fetch_document(doc_info)
            if doc:
                documents.append(doc)

        logger.info(
            "scrape_complete",
            regulator=self.regulator_code,
            documents_scraped=len(documents),
            documents_discovered=len(doc_infos),
        )

        await self.close()
        return documents


class RBIPenaltyOrderScraper(RBIScraper):
    """Specialized scraper for RBI penalty orders page.

    Targets the specific penalty orders listing at:
    https://www.rbi.org.in/Scripts/BS_ViewMasCirculardetails.aspx
    and the penalty press releases section.
    """

    # RBI has a dedicated penalty orders page
    PENALTY_ORDERS_PATH = "/Scripts/Penaltyorders.aspx"

    async def discover_penalty_orders(self) -> list[dict]:
        """Discover penalty orders from the dedicated penalty page."""
        url = f"{self.base_url}{self.PENALTY_ORDERS_PATH}"
        all_docs = []

        try:
            resp = await self.fetch(url)
            soup = BeautifulSoup(resp.text, "lxml")

            # The penalty orders page lists orders in a table
            # Each row has: date, entity name, link to order PDF
            rows = soup.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    link = row.find("a", href=True)
                    if link:
                        href = link["href"]
                        abs_url = self.make_absolute_url(href)
                        title = link.get_text(strip=True)

                        # Extract date from first cell
                        date_hint = cells[0].get_text(strip=True) if cells else ""

                        all_docs.append({
                            "url": abs_url,
                            "title": title,
                            "date_hint": date_hint,
                            "is_pdf": href.lower().endswith(".pdf"),
                        })

            logger.info(
                "penalty_orders_discovered",
                regulator=self.regulator_code,
                count=len(all_docs),
            )
        except Exception as e:
            logger.error("penalty_orders_discovery_failed", error=str(e))

        return all_docs

    async def scrape(self) -> list[ScrapedDocument]:
        """Scrape from both penalty orders page and press releases."""
        # Get penalty orders from dedicated page
        penalty_docs = await self.discover_penalty_orders()

        # Also get from general press releases
        press_docs = await self.discover_documents()

        # Merge and deduplicate
        seen_urls = set()
        all_doc_infos = []
        for doc in penalty_docs + press_docs:
            if doc["url"] not in seen_urls:
                seen_urls.add(doc["url"])
                all_doc_infos.append(doc)

        # Fetch all documents
        documents = []
        for doc_info in all_doc_infos:
            doc = await self._fetch_document(doc_info)
            if doc:
                documents.append(doc)

        logger.info(
            "full_scrape_complete",
            regulator=self.regulator_code,
            penalty_page_docs=len(penalty_docs),
            press_release_docs=len(press_docs),
            total_fetched=len(documents),
        )

        await self.close()
        return documents
