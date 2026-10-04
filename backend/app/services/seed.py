from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.models import Candidate, Hall, PaperSet

def seed_if_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(Hall)) or 0) > 0:
        return
    hall = Hall(code="H101", name="一号考室", rows=5, cols=6, min_manhattan=2)
    db.add(hall); db.flush()
    # code, title, max_count(0 不截断), min_count(0 关闭保底), is_primary
    papers = [
        ("P-A", "语文 A 卷", 2, 1, True),
        ("P-B", "语文 B 卷", 0, 0, False),
        ("P-C", "语文 C 卷", 0, 0, False),
    ]
    paper_ids = []
    for code, title, max_count, min_count, is_primary in papers:
        p = PaperSet(code=code, title=title,
                     max_count=max_count, min_count=min_count, is_primary=is_primary)
        db.add(p); db.flush()
        paper_ids.append(p.id)
    names = ["陈一", "李二", "张三", "赵四", "钱五", "孙六", "周七", "吴八", "郑九", "王十", "冯十一", "陈十二"]
    for i, name in enumerate(names):
        db.add(Candidate(hall_id=hall.id, name=name, ticket_no=f"T{2026001+i}",
                         paper_id=paper_ids[i % len(paper_ids)]))
    db.commit()
