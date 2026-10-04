import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Candidate, Hall, PaperSet, SeatPlan
from app.services.seat_engine import (
    PaperLimit,
    REASON_PRIMARY_FLOOR,
    build_paper_breakdown,
    find_violations,
    place_candidates,
    plan_to_dict,
    primary_floor_failures,
)
router = APIRouter(prefix="/seating", tags=["seating"])


def _load_limits(db: Session) -> dict[int, PaperLimit]:
    limits: dict[int, PaperLimit] = {}
    for p in db.scalars(select(PaperSet).order_by(PaperSet.id)).all():
        limits[p.id] = PaperLimit(
            paper_id=p.id, code=p.code, title=p.title,
            max_count=p.max_count or 0, min_count=p.min_count or 0,
            is_primary=bool(p.is_primary),
        )
    return limits


def _snapshot(limits: dict[int, PaperLimit]) -> list[dict]:
    return [
        {"paper_id": l.paper_id, "max_count": l.max_count,
         "min_count": l.min_count, "is_primary": l.is_primary}
        for l in sorted(limits.values(), key=lambda l: l.paper_id)
    ]


def _compute(db: Session, hall: Hall) -> tuple[dict, list[dict]]:
    """Compute the single seating result shared by map / stats / violations / roster."""
    cands = [{"id": c.id, "name": c.name, "ticket_no": c.ticket_no, "paper_id": c.paper_id}
             for c in db.scalars(select(Candidate).where(Candidate.hall_id == hall.id)
                                 .order_by(Candidate.id)).all()]
    limits = _load_limits(db)
    assigns, unplaced = place_candidates(hall.rows, hall.cols, hall.min_manhattan, cands, limits)
    floor_failures = primary_floor_failures(assigns, limits)
    viols = find_violations(hall.rows, hall.cols, hall.min_manhattan, assigns)
    breakdown = build_paper_breakdown(cands, assigns, unplaced, limits)
    result = plan_to_dict(assigns, unplaced, viols, hall.rows, hall.cols,
                          paper_breakdown=breakdown, limits_snapshot=_snapshot(limits))
    result["hall"] = {"id": hall.id, "name": hall.name, "min_manhattan": hall.min_manhattan}
    result["floor_failures"] = floor_failures
    return result, floor_failures


def _failure_envelope(result: dict, floor_failures: list[dict]) -> dict:
    """Whole-run failure view: no grid, no stored plan, one floor-only message.

    The per-set breakdown of the attempt is kept diagnostic so every view
    reports identical numbers, but assignments are deliberately empty —
    auxiliary sets never get presented as filling the hall.
    """
    return {
        "ok": False,
        "message": REASON_PRIMARY_FLOOR,
        "floor_failures": floor_failures,
        "rows": result["rows"],
        "cols": result["cols"],
        "assignments": [],
        "unplaced": result["unplaced"],
        "violations": [],
        "paper_breakdown": result["paper_breakdown"],
        "limits_snapshot": result["limits_snapshot"],
        "stats": result["stats"],
        "hall": result["hall"],
    }


@router.post("/run")
def run_seating(hall_id: int = 1, db: Session = Depends(get_db)):
    hall = db.get(Hall, hall_id)
    if not hall: raise HTTPException(404, "考室不存在")
    result, floor_failures = _compute(db, hall)
    if floor_failures:
        # Primary floor cannot be held: the whole run fails and NO plan is stored.
        db.rollback()
        raise HTTPException(422, {"message": REASON_PRIMARY_FLOOR, "failures": floor_failures})
    plan = SeatPlan(hall_id=hall_id, created_at=datetime.utcnow(),
                    result_json=json.dumps(result, ensure_ascii=False))
    db.add(plan); db.commit(); db.refresh(plan)
    return {"id": plan.id, "ok": True, **result}


@router.get("/latest")
def latest(hall_id: int = 1, db: Session = Depends(get_db)):
    hall = db.get(Hall, hall_id)
    if not hall: raise HTTPException(404, "考室不存在")
    limits = _load_limits(db)
    plan = db.scalars(select(SeatPlan).where(SeatPlan.hall_id == hall_id)
                      .order_by(SeatPlan.id.desc())).first()
    if plan is not None:
        data = json.loads(plan.result_json)
        # Charts produced under superseded limits are never served.
        if data.get("limits_snapshot") == _snapshot(limits):
            return {"id": plan.id, "ok": True, **data}
    # No usable chart: recompute against current limits. A floor failure is a
    # state every view must agree on, so it is returned (never persisted).
    result, floor_failures = _compute(db, hall)
    if floor_failures:
        return _failure_envelope(result, floor_failures)
    return run_seating(hall_id=hall_id, db=db)


@router.get("/violations")
def violations(hall_id: int = 1, db: Session = Depends(get_db)):
    data = latest(hall_id=hall_id, db=db)
    return {"hall_id": hall_id, "ok": data.get("ok", True),
            "message": data.get("message"),
            "violations": data.get("violations", []),
            "unplaced": data.get("unplaced", [])}


@router.get("/stats")
def stats(hall_id: int = 1, db: Session = Depends(get_db)):
    data = latest(hall_id=hall_id, db=db)
    # Seated/unplaced and the per-set breakdown come from the same stored plan
    # (or the same failed attempt) as the map — no endpoint recomputes numbers.
    return {
        "hall_id": hall_id,
        "ok": data.get("ok", True),
        "message": data.get("message"),
        "floor_failures": data.get("floor_failures", []),
        **data.get("stats", {}),
        "unplaced_list": data.get("unplaced", []),
        "paper_breakdown": data.get("paper_breakdown", []),
    }
