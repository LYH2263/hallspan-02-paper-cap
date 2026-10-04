from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Candidate, PaperSet
router = APIRouter(prefix="/candidates", tags=["candidates"])

@router.get("")
def list_candidates(db: Session = Depends(get_db)):
    papers = {p.id: p for p in db.scalars(select(PaperSet)).all()}
    rows = []
    for r in db.scalars(select(Candidate).order_by(Candidate.id)).all():
        p = papers.get(r.paper_id)
        rows.append({
            "id": r.id,
            "hall_id": r.hall_id,
            "name": r.name,
            "ticket_no": r.ticket_no,
            "paper_id": r.paper_id,
            "paper_code": p.code if p else "",
            "is_primary": bool(p.is_primary) if p else False,
        })
    return rows
