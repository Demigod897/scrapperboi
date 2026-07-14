from fastapi import APIRouter, Query

from storage.search import search_violations

router = APIRouter()


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    regulator: str | None = Query(None, description="Filter by regulator code"),
    violation_category: str | None = Query(None),
    severity: str | None = Query(None),
    sort_by: str | None = Query(None, description="Sort field: order_date, penalty_amount_inr"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Full-text search across violations using Meilisearch.

    Supports typo-tolerant search on entity names, summaries,
    violation types, and excerpts.
    """
    # Build filter string
    filters = []
    if regulator:
        filters.append(f"regulator_code = '{regulator.upper()}'")
    if violation_category:
        filters.append(f"violation_category = '{violation_category}'")
    if severity:
        filters.append(f"severity = '{severity.upper()}'")

    filter_str = " AND ".join(filters) if filters else None

    # Build sort
    sort = None
    if sort_by:
        sort = [f"{sort_by}:{sort_order}"]

    result = search_violations(
        query=q,
        filters=filter_str,
        sort=sort,
        offset=offset,
        limit=limit,
    )

    return {
        "query": q,
        "total": result.get("estimatedTotalHits", 0),
        "offset": offset,
        "limit": limit,
        "hits": result.get("hits", []),
        "processing_time_ms": result.get("processingTimeMs", 0),
    }
