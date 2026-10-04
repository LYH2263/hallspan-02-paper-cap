from sqlalchemy import func, select

from app.models.models import PaperSet, SeatPlan


def test_seed_limits(client):
    rows = client.get("/api/papers").json()
    a = next(r for r in rows if r["code"] == "P-A")
    assert a["max_count"] == 2
    assert a["min_count"] == 1
    assert a["is_primary"] is True
    # 12 seeded candidates cycle over 3 sets -> 4 each.
    assert a["candidate_count"] == 4


def test_run_seats_paper_a_between_one_and_two(client, db_session):
    res = client.post("/api/seating/run?hall_id=1")
    assert res.status_code == 200, res.text
    data = res.json()
    a = _paper_a_id(db_session)
    seated_a = sum(1 for x in data["assignments"] if x["paper_id"] == a)
    assert seated_a in (1, 2)
    bd = {b["paper_id"]: b for b in data["paper_breakdown"]}
    assert bd[a]["seated"] == seated_a
    assert bd[a]["unplaced"] == 4 - seated_a
    # Capped unplaced carry only the cap message.
    for u in data["unplaced"]:
        if u["paper_id"] == a:
            assert u["reason"] == "同卷人数已满"
    assert client.get("/api/seating/stats?hall_id=1").json()["unplaced"] == len(data["unplaced"])


def test_latest_serves_same_plan_not_recomputed(client, db_session):
    first = client.post("/api/seating/run?hall_id=1").json()
    again = client.get("/api/seating/latest?hall_id=1").json()
    assert again["id"] == first["id"]
    assert again["stats"]["seated"] == first["stats"]["seated"]


def test_negative_limits_rejected_and_nothing_moves(client, db_session):
    a = _paper_a_id(db_session)
    before = client.get("/api/papers").json()
    res = client.put(f"/api/papers/{a}", json={"max_count": -1})
    assert res.status_code == 400
    res2 = client.put(f"/api/papers/{a}", json={"min_count": -2})
    assert res2.status_code == 400
    after = client.get("/api/papers").json()
    assert before == after
    # Existing chart, if any, stays valid (three views untouched): create one first.
    client.post("/api/seating/run?hall_id=1")
    client.put(f"/api/papers/{a}", json={"max_count": -9})
    latest = client.get("/api/seating/latest?hall_id=1").json()
    assert latest.get("ok", True) is True
    assert "id" in latest


def test_changing_limits_invalidates_old_chart(client, db_session):
    first = client.post("/api/seating/run?hall_id=1").json()
    a = _paper_a_id(db_session)
    assert client.put(f"/api/papers/{a}", json={"max_count": 3}).status_code == 200
    # Old chart deleted...
    assert db_session.scalar(select(func.count()).select_from(SeatPlan)) == 0
    # ...and latest regenerates under the NEW limit rather than serving the old image.
    latest = client.get("/api/seating/latest?hall_id=1").json()
    snap = {s["paper_id"]: s for s in latest["limits_snapshot"]}
    assert snap[a]["max_count"] == 3
    seated_a = sum(1 for x in latest["assignments"] if x["paper_id"] == a)
    assert seated_a == 3
    # Old plan had A capped at 2: proving the new chart, not the stale one.
    assert {s["paper_id"]: s["max_count"] for s in first["limits_snapshot"]}[a] == 2


def test_floor_three_whole_run_fails_and_no_plan_stored(client, db_session):
    # Seed: 4 A candidates but min_manhattan=2 on a 5x6 grid lets at most...
    # floor 3 must hold or fail according to the engine; assert the contract:
    # on failure 422, message is floor-only, no plan row, no auxiliary filling.
    a = _paper_a_id(db_session)
    assert client.put(f"/api/papers/{a}", json={"min_count": 3}).status_code == 200
    res = client.post("/api/seating/run?hall_id=1")
    data = res.json()
    detail = data["detail"]
    assert res.status_code == 422
    assert detail["message"] == "主卷人数不足"
    assert detail["failures"][0]["paper_id"] == a
    assert detail["failures"][0]["min_count"] == 3
    assert detail["failures"][0]["seated"] < 3
    # Nothing stored: no new plan.
    assert db_session.scalar(select(func.count()).select_from(SeatPlan)) == 0

    # GET views agree on the failure without persisting anything.
    for path in ("/api/seating/latest?hall_id=1", "/api/seating/stats?hall_id=1"):
        body = client.get(path).json()
        assert body["ok"] is False, body
        assert body["message"] == "主卷人数不足"
        assert body["assignments"] == [] if "assignments" in body else True
    assert db_session.scalar(select(func.count()).select_from(SeatPlan)) == 0


def test_floor_failure_breakdown_does_not_pad_with_aux(client, db_session):
    a = _paper_a_id(db_session)
    client.put(f"/api/papers/{a}", json={"min_count": 3})
    body = client.get("/api/seating/stats?hall_id=1").json()
    assert body["ok"] is False
    bd = {b["paper_id"]: b for b in body["paper_breakdown"]}
    # The failed attempt is reported honestly: A is short, seated counts are
    # not inflated, and totals identity still holds across all sets.
    assert bd[a]["seated"] < 3
    for b in body["paper_breakdown"]:
        assert b["total"] == b["seated"] + b["unplaced"]


def test_three_views_share_one_result(client, db_session):
    run = client.post("/api/seating/run?hall_id=1").json()
    stats = client.get("/api/seating/stats?hall_id=1").json()
    viols = client.get("/api/seating/violations?hall_id=1").json()
    assert stats["seated"] == run["stats"]["seated"]
    assert stats["unplaced"] == run["stats"]["unplaced"]
    assert len(viols["unplaced"]) == run["stats"]["unplaced"]
    for b in stats["paper_breakdown"]:
        plan_b = next(x for x in run["paper_breakdown"] if x["paper_id"] == b["paper_id"])
        assert b["seated"] == plan_b["seated"]
        assert b["unplaced"] == plan_b["unplaced"]


def _paper_a_id(db_session) -> int:
    return db_session.scalar(select(PaperSet.id).where(PaperSet.code == "P-A"))
