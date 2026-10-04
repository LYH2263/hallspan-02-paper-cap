import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Candidate, Hall, PaperSet, SeatPlan
from app.services.seat_engine import (REASON_MAIN_SHORT, find_violations,
                                      main_minimum_met, place_candidates, plan_to_dict)
router = APIRouter(prefix="/seating", tags=["seating"])

def _current_rules(db: Session) -> list[dict]:
    """当前各套上下限快照, 随方案一起落库; 规则一变旧图即失效。"""
    return [{"id": p.id, "code": p.code, "is_main": p.is_main,
             "max_seated": p.max_seated, "min_seated": p.min_seated}
            for p in db.scalars(select(PaperSet).order_by(PaperSet.id)).all()]

def _run(db: Session, hall: Hall) -> dict:
    papers = db.scalars(select(PaperSet).order_by(PaperSet.id)).all()
    caps = {p.id: p.max_seated for p in papers if p.max_seated > 0}
    cands = [{"id": c.id, "name": c.name, "ticket_no": c.ticket_no, "paper_id": c.paper_id}
             for c in db.scalars(select(Candidate).where(Candidate.hall_id == hall.id)).all()]
    assigns, unplaced = place_candidates(hall.rows, hall.cols, hall.min_manhattan, cands, caps)
    main = next((p for p in papers if p.is_main), None)
    if not main_minimum_met(assigns, main.id if main else None, main.min_seated if main else 0):
        # 主卷保底失败: 整场排座失败且不增方案, 辅卷人数不计入保底
        raise HTTPException(422, REASON_MAIN_SHORT)
    viols = find_violations(hall.rows, hall.cols, hall.min_manhattan, assigns)
    result = plan_to_dict(assigns, unplaced, viols, hall.rows, hall.cols)
    result["hall"] = {"id": hall.id, "name": hall.name, "min_manhattan": hall.min_manhattan}
    result["paper_rules"] = _current_rules(db)
    plan = SeatPlan(hall_id=hall.id, created_at=datetime.utcnow(), result_json=json.dumps(result, ensure_ascii=False))
    db.add(plan); db.commit(); db.refresh(plan)
    return {"id": plan.id, **result}

@router.post("/run")
def run_seating(hall_id: int = 1, db: Session = Depends(get_db)):
    hall = db.get(Hall, hall_id)
    if not hall: raise HTTPException(404, "考室不存在")
    return _run(db, hall)

@router.get("/latest")
def latest(hall_id: int = 1, db: Session = Depends(get_db)):
    hall = db.get(Hall, hall_id)
    if not hall: raise HTTPException(404, "考室不存在")
    plan = db.scalars(select(SeatPlan).where(SeatPlan.hall_id == hall_id).order_by(SeatPlan.id.desc())).first()
    if plan:
        data = json.loads(plan.result_json)
        if data.get("paper_rules") == _current_rules(db):
            return {"id": plan.id, **data}
        # 上下限已改: 旧图可能超发, 按新规则重排, 禁止吃旧图
    return _run(db, hall)

@router.get("/violations")
def violations(hall_id: int = 1, db: Session = Depends(get_db)):
    data = latest(hall_id=hall_id, db=db)
    return {"hall_id": hall_id, "violations": data.get("violations", []), "unplaced": data.get("unplaced", [])}

@router.get("/stats")
def stats(hall_id: int = 1, db: Session = Depends(get_db)):
    data = latest(hall_id=hall_id, db=db)
    return {"hall_id": hall_id, **data.get("stats", {})}
