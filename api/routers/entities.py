from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.dependencies import get_db
from storage.db import Entity, Penalty, Violation

router = APIRouter()


@router.get("/entities")
async def list_entities(
    entity_type: str | None = Query(None, description="COMPANY, BANK, NBFC, INDIVIDUAL"),
    name: str | None = Query(None, description="Partial name match"),
    cin: str | None = Query(None, description="Exact CIN match"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List entities with optional filtering."""
    query = select(Entity).order_by(Entity.entity_name)

    if entity_type:
        query = query.where(Entity.entity_type == entity_type.upper())
    if name:
        query = query.where(Entity.entity_name.ilike(f"%{name}%"))
    if cin:
        query = query.where(Entity.cin == cin)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    entities = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "data": [
            {
                "id": e.id,
                "entity_name": e.entity_name,
                "cin": e.cin,
                "entity_type": e.entity_type,
                "mca_status": e.mca_status,
                "aliases": e.aliases or [],
            }
            for e in entities
        ],
    }


@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get entity profile with all violations and penalty summary."""
    result = await db.execute(
        select(Entity).where(Entity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Get all violations for this entity
    violations_result = await db.execute(
        select(Violation)
        .options(selectinload(Violation.penalties), selectinload(Violation.regulator))
        .where(Violation.entity_id == entity_id)
        .order_by(Violation.order_date.desc().nullslast())
    )
    violations = violations_result.scalars().unique().all()

    # Compute summary stats
    total_penalty = sum(
        float(p.amount_inr)
        for v in violations
        for p in v.penalties
        if p.amount_inr
    )
    violation_categories = list(set(
        v.violation_category for v in violations if v.violation_category
    ))

    return {
        "id": entity.id,
        "entity_name": entity.entity_name,
        "cin": entity.cin,
        "entity_type": entity.entity_type,
        "pan": entity.pan,
        "mca_status": entity.mca_status,
        "aliases": entity.aliases or [],
        "summary": {
            "total_violations": len(violations),
            "total_penalty_inr": total_penalty,
            "violation_categories": violation_categories,
            "first_violation": violations[-1].order_date.isoformat() if violations and violations[-1].order_date else None,
            "latest_violation": violations[0].order_date.isoformat() if violations and violations[0].order_date else None,
        },
        "violations": [
            {
                "id": v.id,
                "order_date": v.order_date.isoformat() if v.order_date else None,
                "violation_category": v.violation_category,
                "violation_subtype": v.violation_subtype,
                "severity": v.severity,
                "summary": v.summary,
                "regulator": v.regulator.code if v.regulator else None,
                "penalties": [
                    {
                        "type": p.penalty_type,
                        "amount_inr": float(p.amount_inr) if p.amount_inr else None,
                    }
                    for p in v.penalties
                ],
            }
            for v in violations
        ],
    }


@router.get("/entities/{entity_id}/timeline")
async def get_entity_timeline(
    entity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get chronological violation timeline for an entity."""
    result = await db.execute(
        select(Entity).where(Entity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    violations_result = await db.execute(
        select(Violation)
        .options(selectinload(Violation.penalties), selectinload(Violation.regulator))
        .where(Violation.entity_id == entity_id)
        .order_by(Violation.order_date.asc().nullslast())
    )
    violations = violations_result.scalars().unique().all()

    return {
        "entity_id": entity.id,
        "entity_name": entity.entity_name,
        "cin": entity.cin,
        "timeline": [
            {
                "date": v.order_date.isoformat() if v.order_date else None,
                "violation_id": v.id,
                "regulator": v.regulator.code if v.regulator else None,
                "category": v.violation_category,
                "subtype": v.violation_subtype,
                "severity": v.severity,
                "summary": v.summary,
                "penalty_inr": sum(
                    float(p.amount_inr) for p in v.penalties if p.amount_inr
                ),
            }
            for v in violations
        ],
    }
