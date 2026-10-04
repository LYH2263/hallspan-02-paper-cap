from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import PaperSet
router = APIRouter(prefix="/papers", tags=["papers"])

def paper_dict(r: PaperSet) -> dict:
    return {"id": r.id, "code": r.code, "title": r.title,
            "is_main": r.is_main, "max_seated": r.max_seated, "min_seated": r.min_seated}

@router.get("")
def list_papers(db: Session = Depends(get_db)):
    return [paper_dict(r) for r in db.scalars(select(PaperSet).order_by(PaperSet.id)).all()]

class PaperRulesIn(BaseModel):
    is_main: bool | None = None
    max_seated: int | None = None
    min_seated: int | None = None

@router.put("/{paper_id}")
def update_paper(paper_id: int, body: PaperRulesIn, db: Session = Depends(get_db)):
    p = db.get(PaperSet, paper_id)
    if not p:
        raise HTTPException(404, "试卷套不存在")
    # 负值拒绝保存: 先校验再落库, 不合格则整套规则不动
    if (body.max_seated is not None and body.max_seated < 0) or \
       (body.min_seated is not None and body.min_seated < 0):
        raise HTTPException(422, "人数上下限不能为负")
    if body.is_main is not None:
        if body.is_main:
            for q in db.scalars(select(PaperSet)).all():
                q.is_main = False
        p.is_main = body.is_main
    if body.max_seated is not None:
        p.max_seated = body.max_seated
    if body.min_seated is not None:
        p.min_seated = body.min_seated
    db.commit(); db.refresh(p)
    return paper_dict(p)
