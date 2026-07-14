from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_db
from storage.db import Entity, Penalty, Regulator, Violation

router = APIRouter()


@router.get("/violations")
async def list_violations(
    regulator: str | None = Query(None, description="Regulator code (e.g., RBI, SEBI)"),
    entity_name: str | None = Query(None, description="Filter by entity name (partial match)"),
    violation_type: str | None = Query(None, description="Violation category (e.g., BANKING_REGULATORY)"),
    severity: str | None = Query(None, description="Severity: LOW, MEDIUM, HIGH, CRITICAL"),
    date_from: date | None = Query(None, description="Order date from (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="Order date to (YYYY-MM-DD)"),
    min_penalty: float | None = Query(None, description="Minimum penalty amount (INR)"),
    review_status: str | None = Query(None, description="Review status filter"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List violations with filtering, pagination, and sorting."""
    query = (
        select(Violation)
        .options(selectinload(Violation.entity), selectinload(Violation.penalties))
        .order_by(Violation.order_date.desc().nullslast(), Violation.id.desc())
    )

    # Apply filters
    if regulator:
        query = query.join(Regulator).where(Regulator.code == regulator.upper())
    if entity_name:
        query = query.join(Entity).where(Entity.entity_name.ilike(f"%{entity_name}%"))
    if violation_type:
        if "/" in violation_type:
            cat, sub = violation_type.split("/", 1)
            query = query.where(
                Violation.violation_category == cat,
                Violation.violation_subtype == sub,
            )
        else:
            query = query.where(Violation.violation_category == violation_type)
    if severity:
        query = query.where(Violation.severity == severity.upper())
    if date_from:
        query = query.where(Violation.order_date >= date_from)
    if date_to:
        query = query.where(Violation.order_date <= date_to)
    if min_penalty:
        query = query.join(Penalty).where(Penalty.amount_inr >= min_penalty)
    if review_status:
        query = query.where(Violation.review_status == review_status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    violations = result.scalars().unique().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "data": [_serialize_violation(v) for v in violations],
    }


@router.get("/violations/{violation_id}")
async def get_violation(
    violation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get full violation details including document, entity, and penalties."""
    query = (
        select(Violation)
        .options(
            selectinload(Violation.entity),
            selectinload(Violation.penalties),
            selectinload(Violation.document),
            selectinload(Violation.regulator),
        )
        .where(Violation.id == violation_id)
    )

    result = await db.execute(query)
    violation = result.scalar_one_or_none()

    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    data = _serialize_violation(violation)
    # Add document and regulator details
    if violation.document:
        data["document"] = {
            "id": violation.document.id,
            "source_url": violation.document.source_url,
            "title": violation.document.title,
            "extraction_method": violation.document.extraction_method,
            "language": violation.document.language,
            "page_count": violation.document.page_count,
            "scraped_at": violation.document.scraped_at.isoformat() if violation.document.scraped_at else None,
        }
    if violation.regulator:
        data["regulator"] = {
            "code": violation.regulator.code,
            "full_name": violation.regulator.full_name,
            "website_url": violation.regulator.website_url,
        }

    return data


@router.get("/recidivists")
async def list_recidivists(
    min_violations: int = Query(2, ge=2, description="Minimum number of violations"),
    regulator: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List repeat offenders with multiple violations."""
    query = (
        select(
            Entity.id,
            Entity.entity_name,
            Entity.cin,
            Entity.entity_type,
            func.count(Violation.id).label("violation_count"),
            func.sum(Penalty.amount_inr).label("total_penalty_inr"),
            func.min(Violation.order_date).label("first_violation"),
            func.max(Violation.order_date).label("latest_violation"),
        )
        .join(Violation, Violation.entity_id == Entity.id)
        .outerjoin(Penalty, Penalty.violation_id == Violation.id)
        .group_by(Entity.id, Entity.entity_name, Entity.cin, Entity.entity_type)
        .having(func.count(Violation.id) >= min_violations)
        .order_by(func.count(Violation.id).desc())
    )

    if regulator:
        query = query.join(Regulator, Violation.regulator_id == Regulator.id).where(
            Regulator.code == regulator.upper()
        )

    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    rows = result.all()

    return {
        "page": page,
        "per_page": per_page,
        "data": [
            {
                "entity_id": row.id,
                "entity_name": row.entity_name,
                "cin": row.cin,
                "entity_type": row.entity_type,
                "violation_count": row.violation_count,
                "total_penalty_inr": float(row.total_penalty_inr) if row.total_penalty_inr else 0,
                "first_violation": row.first_violation.isoformat() if row.first_violation else None,
                "latest_violation": row.latest_violation.isoformat() if row.latest_violation else None,
            }
            for row in rows
        ],
    }


def _serialize_violation(v: Violation) -> dict:
    return {
        "id": v.id,
        "order_date": v.order_date.isoformat() if v.order_date else None,
        "violation_date": v.violation_date.isoformat() if v.violation_date else None,
        "violation_category": v.violation_category,
        "violation_subtype": v.violation_subtype,
        "severity": v.severity,
        "summary": v.summary,
        "extraction_confidence": v.extraction_confidence,
        "review_status": v.review_status,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "entity": {
            "id": v.entity.id,
            "name": v.entity.entity_name,
            "cin": v.entity.cin,
            "type": v.entity.entity_type,
        } if v.entity else None,
        "penalties": [
            {
                "id": p.id,
                "type": p.penalty_type,
                "amount_inr": float(p.amount_inr) if p.amount_inr else None,
                "raw_text": p.amount_raw_text,
                "duration_days": p.duration_days,
            }
            for p in v.penalties
        ] if v.penalties else [],
    }
