from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Candidate, PaperSet, SeatPlan
router = APIRouter(prefix="/papers", tags=["papers"])


class PaperLimitsIn(BaseModel):
    # 0 = 不截断 / 关闭保底；负值在路由内显式拒绝
    max_count: int | None = None
    min_count: int | None = None
    is_primary: bool | None = None


def _serialize(r: PaperSet, candidate_count: int = 0) -> dict:
    return {
        "id": r.id,
        "code": r.code,
        "title": r.title,
        "max_count": r.max_count or 0,
        "min_count": r.min_count or 0,
        "is_primary": bool(r.is_primary),
        "candidate_count": candidate_count,
    }


@router.get("")
def list_papers(db: Session = Depends(get_db)):
    counts = dict(db.execute(
        select(Candidate.paper_id, func.count(Candidate.id)).group_by(Candidate.paper_id)
    ).all())
    return [_serialize(r, counts.get(r.id, 0))
            for r in db.scalars(select(PaperSet).order_by(PaperSet.id)).all()]


@router.put("/{paper_id}")
def update_paper(paper_id: int, body: PaperLimitsIn, db: Session = Depends(get_db)):
    paper = db.get(PaperSet, paper_id)
    if not paper:
        raise HTTPException(404, "试卷套不存在")
    # Negatives are rejected outright: no field is saved and existing charts stay put.
    if (body.max_count is not None and body.max_count < 0) or \
       (body.min_count is not None and body.min_count < 0):
        db.rollback()
        raise HTTPException(400, "上下限不能为负值")
    if body.max_count is not None:
        paper.max_count = body.max_count
    if body.min_count is not None:
        paper.min_count = body.min_count
    if body.is_primary is not None:
        paper.is_primary = body.is_primary
    # Limits changed: supersede every stored chart so map/stats/roster never
    # read a chart produced under the old limits.
    db.execute(delete(SeatPlan))
    db.commit()
    db.refresh(paper)
    count = db.scalar(select(func.count(Candidate.id)).where(Candidate.paper_id == paper_id)) or 0
    return _serialize(paper, count)
