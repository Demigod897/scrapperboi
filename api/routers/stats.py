from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from storage.db import Entity, Penalty, Regulator, ScrapeRun, Violation

router = APIRouter()


@router.get("/stats/overview")
async def overview_stats(db: AsyncSession = Depends(get_db)):
    """Get platform-wide statistics."""
    total_violations = (await db.execute(select(func.count(Violation.id)))).scalar() or 0
    total_entities = (await db.execute(select(func.count(Entity.id)))).scalar() or 0
    total_penalties = (
        await db.execute(select(func.sum(Penalty.amount_inr).filter(Penalty.amount_inr.isnot(None))))
    ).scalar() or 0

    return {
        "total_violations": total_violations,
        "total_entities": total_entities,
        "total_penalties_inr": float(total_penalties),
    }


@router.get("/stats/regulators")
async def regulator_stats(db: AsyncSession = Depends(get_db)):
    """Get violation and penalty stats grouped by regulator."""
    query = (
        select(
            Regulator.code,
            Regulator.full_name,
            func.count(Violation.id).label("violation_count"),
            func.sum(Penalty.amount_inr).label("total_penalty_inr"),
            func.min(Violation.order_date).label("earliest_order"),
            func.max(Violation.order_date).label("latest_order"),
        )
        .join(Violation, Violation.regulator_id == Regulator.id)
        .outerjoin(Penalty, Penalty.violation_id == Violation.id)
        .group_by(Regulator.code, Regulator.full_name)
        .order_by(func.count(Violation.id).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    return {
        "regulators": [
            {
                "code": row.code,
                "full_name": row.full_name,
                "violation_count": row.violation_count,
                "total_penalty_inr": float(row.total_penalty_inr) if row.total_penalty_inr else 0,
                "earliest_order": row.earliest_order.isoformat() if row.earliest_order else None,
                "latest_order": row.latest_order.isoformat() if row.latest_order else None,
            }
            for row in rows
        ],
    }


@router.get("/stats/violations-by-type")
async def violations_by_type(
    regulator: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get violation count grouped by violation category and subtype."""
    query = (
        select(
            Violation.violation_category,
            Violation.violation_subtype,
            func.count(Violation.id).label("count"),
            func.sum(Penalty.amount_inr).label("total_penalty_inr"),
        )
        .outerjoin(Penalty, Penalty.violation_id == Violation.id)
        .where(Violation.violation_category.isnot(None))
        .group_by(Violation.violation_category, Violation.violation_subtype)
        .order_by(func.count(Violation.id).desc())
    )

    if regulator:
        query = query.join(Regulator, Violation.regulator_id == Regulator.id).where(
            Regulator.code == regulator.upper()
        )

    result = await db.execute(query)
    rows = result.all()

    return {
        "violation_types": [
            {
                "category": row.violation_category,
                "subtype": row.violation_subtype,
                "count": row.count,
                "total_penalty_inr": float(row.total_penalty_inr) if row.total_penalty_inr else 0,
            }
            for row in rows
        ],
    }


@router.get("/stats/penalties-by-quarter")
async def penalties_by_quarter(
    regulator: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get penalty amounts aggregated by quarter."""
    query = (
        select(
            func.date_trunc("quarter", Violation.order_date).label("quarter"),
            func.count(Violation.id).label("violation_count"),
            func.sum(Penalty.amount_inr).label("total_penalty_inr"),
            func.avg(Penalty.amount_inr).label("avg_penalty_inr"),
        )
        .join(Penalty, Penalty.violation_id == Violation.id)
        .where(Violation.order_date.isnot(None))
        .group_by(func.date_trunc("quarter", Violation.order_date))
        .order_by(func.date_trunc("quarter", Violation.order_date).desc())
    )

    if regulator:
        query = query.join(Regulator, Violation.regulator_id == Regulator.id).where(
            Regulator.code == regulator.upper()
        )

    result = await db.execute(query)
    rows = result.all()

    return {
        "quarters": [
            {
                "quarter": row.quarter.isoformat() if row.quarter else None,
                "violation_count": row.violation_count,
                "total_penalty_inr": float(row.total_penalty_inr) if row.total_penalty_inr else 0,
                "avg_penalty_inr": float(row.avg_penalty_inr) if row.avg_penalty_inr else 0,
            }
            for row in rows
        ],
    }


@router.get("/stats/scrape-runs")
async def scrape_run_stats(
    regulator: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get recent scrape run history."""
    query = (
        select(ScrapeRun)
        .order_by(ScrapeRun.started_at.desc())
        .limit(limit)
    )

    if regulator:
        query = query.join(Regulator).where(Regulator.code == regulator.upper())

    result = await db.execute(query)
    runs = result.scalars().all()

    return {
        "runs": [
            {
                "id": r.id,
                "regulator_id": r.regulator_id,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "status": r.status,
                "documents_found": r.documents_found,
                "documents_new": r.documents_new,
                "documents_failed": r.documents_failed,
                "error_message": r.error_message,
            }
            for r in runs
        ],
    }
