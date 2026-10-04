import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.models import PaperSet, SeatPlan
from app.services.seed import seed_if_empty


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
        # 每个用例前复位规则与方案, 互不影响
        for p in db.scalars(select(PaperSet)).all():
            p.is_main = p.code == "P-A"
            p.max_seated = 2 if p.code == "P-A" else 0
            p.min_seated = 1 if p.code == "P-A" else 0
        db.query(SeatPlan).delete()
        db.commit()
    finally:
        db.close()
    with TestClient(app) as c:
        yield c


def paper_id_of(code: str) -> int:
    db = SessionLocal()
    try:
        return db.scalar(select(PaperSet.id).where(PaperSet.code == code))
    finally:
        db.close()


def plan_count() -> int:
    db = SessionLocal()
    try:
        return db.scalar(select(func.count()).select_from(SeatPlan)) or 0
    finally:
        db.close()


def test_seed_rules(client):
    papers = {p["code"]: p for p in client.get("/api/papers").json()}
    a = papers["P-A"]
    assert a["is_main"] is True and a["max_seated"] == 2 and a["min_seated"] == 1
    for code in ("P-B", "P-C"):
        assert papers[code]["is_main"] is False
        assert papers[code]["max_seated"] == 0
        assert papers[code]["min_seated"] == 0


def test_run_applies_cap_and_min(client):
    res = client.post("/api/seating/run?hall_id=1")
    assert res.status_code == 200
    data = res.json()
    a_id = paper_id_of("P-A")
    seated_a = [x for x in data["assignments"] if x["paper_id"] == a_id]
    # 主卷上限 2 / 下限 1: 图上 A 卷只能是 1 或 2 人
    assert 1 <= len(seated_a) <= 2
    unplaced_a = [u for u in data["unplaced"] if u["paper_id"] == a_id]
    assert len(seated_a) + len(unplaced_a) == 4  # 名册共 4 个 A 卷
    # 触顶未排只写同卷人数已满
    assert all(u["reason"] == "同卷人数已满" for u in unplaced_a)
    assert all(u["reason"] != "主卷人数不足" for u in data["unplaced"])


def test_min_failure_rejects_whole_run_without_new_plan(client):
    ok = client.post("/api/seating/run?hall_id=1")
    assert ok.status_code == 200
    before = plan_count()
    a_id = paper_id_of("P-A")
    # 下限 3 > 上限 2, 主卷保底必然保不住
    res = client.put(f"/api/papers/{a_id}", json={"min_seated": 3})
    assert res.status_code == 200
    fail = client.post("/api/seating/run?hall_id=1")
    assert fail.status_code == 422
    # 下限失败只写主卷人数不足, 两句不得并
    assert fail.json()["detail"] == "主卷人数不足"
    assert "同卷人数已满" not in fail.text
    assert plan_count() == before  # 不增方案
    # 旧图规则已过期, 禁止吃超发旧图: latest 重排仍失败
    latest = client.get("/api/seating/latest?hall_id=1")
    assert latest.status_code == 422
    assert latest.json()["detail"] == "主卷人数不足"
    assert plan_count() == before


def test_negative_rules_rejected_and_nothing_changes(client):
    a_id = paper_id_of("P-A")
    before_rules = client.get("/api/papers").json()
    before_latest = client.get("/api/seating/latest?hall_id=1").json()
    before_count = plan_count()
    for body in ({"max_seated": -1}, {"min_seated": -2}, {"max_seated": 3, "min_seated": -1}):
        res = client.put(f"/api/papers/{a_id}", json=body)
        assert res.status_code == 422, body
        assert "负" in res.json()["detail"]
    # 三处不动: 规则未变, 旧图仍有效, 不增方案
    assert client.get("/api/papers").json() == before_rules
    assert client.get("/api/seating/latest?hall_id=1").json()["id"] == before_latest["id"]
    assert plan_count() == before_count


def test_rules_change_invalidates_old_plan(client):
    first = client.post("/api/seating/run?hall_id=1").json()
    a_id = paper_id_of("P-A")
    res = client.put(f"/api/papers/{a_id}", json={"max_seated": 1})
    assert res.status_code == 200
    latest = client.get("/api/seating/latest?hall_id=1")
    assert latest.status_code == 200
    data = latest.json()
    assert data["id"] != first["id"]  # 按新值出新图, 不吃旧图
    assert data["stats"]["per_paper"][str(a_id)]["seated"] == 1


def test_cap_zero_disables_truncation(client):
    a_id = paper_id_of("P-A")
    assert client.put(f"/api/papers/{a_id}", json={"max_seated": 0}).status_code == 200
    data = client.post("/api/seating/run?hall_id=1").json()
    assert data["stats"]["per_paper"][str(a_id)]["seated"] == 4
    assert data["unplaced"] == []


def test_roster_chart_stats_aligned(client):
    data = client.post("/api/seating/run?hall_id=1").json()
    stats = client.get("/api/seating/stats?hall_id=1").json()
    viol = client.get("/api/seating/violations?hall_id=1").json()
    roster = client.get("/api/candidates").json()
    # 排座图与统计同源: per_paper 与 assignments/unplaced 逐项一致
    for pid, pp in stats["per_paper"].items():
        pid = int(pid)
        assert pp["seated"] == sum(1 for a in data["assignments"] if a["paper_id"] == pid)
        assert pp["unplaced"] == sum(1 for u in viol["unplaced"] if u["paper_id"] == pid)
        # 名单各套人数 = 已座 + 未排
        assert sum(1 for c in roster if c["paper_id"] == pid) == pp["seated"] + pp["unplaced"]
    assert stats["seated"] == len(data["assignments"])
    assert stats["unplaced"] == len(data["unplaced"])
