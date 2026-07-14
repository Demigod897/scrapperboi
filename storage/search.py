import meilisearch
import structlog

from config.settings import settings

logger = structlog.get_logger(__name__)

_client: meilisearch.Client | None = None


def get_search_client() -> meilisearch.Client:
    global _client
    if _client is None:
        _client = meilisearch.Client(settings.meili_url, settings.meili_master_key)
    return _client


def setup_indexes():
    """Create and configure Meilisearch indexes."""
    client = get_search_client()

    # Violations index (primary search surface)
    try:
        client.create_index("violations", {"primaryKey": "id"})
    except meilisearch.errors.MeilisearchApiError:
        pass  # Index already exists

    violations_index = client.index("violations")
    violations_index.update_settings({
        "searchableAttributes": [
            "entity_name",
            "summary",
            "violation_category",
            "violation_subtype",
            "regulator_code",
            "raw_excerpt",
        ],
        "filterableAttributes": [
            "regulator_code",
            "violation_category",
            "violation_subtype",
            "order_date",
            "penalty_amount_inr",
            "entity_type",
            "review_status",
            "severity",
        ],
        "sortableAttributes": [
            "order_date",
            "penalty_amount_inr",
            "created_at",
        ],
        "typoTolerance": {
            "enabled": True,
            "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8},
        },
    })

    # Entities index
    try:
        client.create_index("entities", {"primaryKey": "id"})
    except meilisearch.errors.MeilisearchApiError:
        pass

    entities_index = client.index("entities")
    entities_index.update_settings({
        "searchableAttributes": ["entity_name", "cin", "aliases"],
        "filterableAttributes": ["entity_type", "mca_status"],
        "typoTolerance": {"enabled": True},
    })

    logger.info("search_indexes_configured")


def index_violation(violation: dict):
    """Index a single violation document for search."""
    client = get_search_client()
    index = client.index("violations")

    doc = {
        "id": violation["id"],
        "entity_name": violation.get("entity_name", ""),
        "cin": violation.get("cin"),
        "regulator_code": violation.get("regulator_code", ""),
        "violation_category": violation.get("violation_category"),
        "violation_subtype": violation.get("violation_subtype"),
        "severity": violation.get("severity"),
        "summary": violation.get("summary", ""),
        "raw_excerpt": violation.get("raw_excerpt", "")[:500],
        "order_date": violation.get("order_date"),
        "penalty_amount_inr": violation.get("penalty_amount_inr", 0),
        "entity_type": violation.get("entity_type"),
        "review_status": violation.get("review_status", "auto_approved"),
        "created_at": violation.get("created_at"),
    }

    index.add_documents([doc])
    logger.debug("violation_indexed", violation_id=violation["id"])


def index_entity(entity: dict):
    """Index a single entity for search."""
    client = get_search_client()
    index = client.index("entities")

    doc = {
        "id": entity["id"],
        "entity_name": entity.get("entity_name", ""),
        "cin": entity.get("cin"),
        "entity_type": entity.get("entity_type"),
        "mca_status": entity.get("mca_status"),
        "aliases": entity.get("aliases", []),
    }

    index.add_documents([doc])


def search_violations(
    query: str,
    filters: str | None = None,
    sort: list[str] | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict:
    """Search violations using Meilisearch.

    Args:
        query: Search query string
        filters: Meilisearch filter string, e.g. "regulator_code = 'RBI'"
        sort: List of sort criteria, e.g. ["order_date:desc"]
        offset: Pagination offset
        limit: Results per page

    Returns:
        Meilisearch search result dict
    """
    client = get_search_client()
    index = client.index("violations")

    search_params = {
        "offset": offset,
        "limit": limit,
    }
    if filters:
        search_params["filter"] = filters
    if sort:
        search_params["sort"] = sort

    result = index.search(query, search_params)
    logger.info(
        "search_executed",
        query=query,
        hits=result.get("estimatedTotalHits", 0),
    )
    return result
