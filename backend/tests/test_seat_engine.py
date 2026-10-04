from app.services.seat_engine import (
    PaperLimit,
    REASON_CAP_FULL,
    REASON_NO_SEAT,
    REASON_PRIMARY_FLOOR,
    build_paper_breakdown,
    find_violations,
    manhattan,
    place_candidates,
    primary_floor_failures,
    SeatAssign,
)

def _cand(i: int, pid: int) -> dict:
    return {"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": pid}

def test_manhattan():
    assert manhattan((0, 0), (2, 1)) == 3

def test_min_distance_placement():
    cands = [_cand(i, 1 + (i % 2)) for i in range(4)]
    assigns, unplaced = place_candidates(4, 4, 2, cands)
    assert len(assigns) + len(unplaced) == 4
    for i, a in enumerate(assigns):
        for b in assigns[i+1:]:
            assert manhattan((a.row, a.col), (b.row, b.col)) >= 2

def test_same_paper_not_adjacent_in_result():
    cands = [_cand(1, 1), _cand(2, 1), _cand(3, 2)]
    assigns, _ = place_candidates(3, 3, 1, cands)
    viols = find_violations(3, 3, 1, assigns)
    assert not any(v.kind == "same_paper_adjacent" for v in viols)

def test_violation_detection():
    assigns = [
        SeatAssign(1, "A", "T1", 1, 0, 0),
        SeatAssign(2, "B", "T2", 1, 0, 1),
    ]
    viols = find_violations(2, 2, 2, assigns)
    kinds = {v.kind for v in viols}
    assert "distance" in kinds
    assert "same_paper_adjacent" in kinds

def test_cap_stops_same_paper_even_with_empty_seats():
    # 4 candidates all on set 1, hall has 9 free seats, cap = 2:
    # exactly 2 seated and the other 2 are unplaced for the cap reason only.
    cands = [_cand(i, 1) for i in range(1, 5)]
    limits = {1: PaperLimit(paper_id=1, code="P-A", max_count=2, min_count=0, is_primary=True)}
    assigns, unplaced = place_candidates(3, 3, 1, cands, limits)
    assert len(assigns) == 2
    assert all(a.paper_id == 1 for a in assigns)
    assert len(unplaced) == 2
    assert [u["reason"] for u in unplaced] == [REASON_CAP_FULL, REASON_CAP_FULL]

def test_cap_zero_means_no_truncation():
    cands = [_cand(i, 1) for i in range(1, 5)]
    limits = {1: PaperLimit(paper_id=1, max_count=0)}
    assigns, unplaced = place_candidates(3, 3, 1, cands, limits)
    assert len(assigns) == 4
    assert unplaced == []

def test_cap_never_reported_as_no_seat():
    # Even when the hall is genuinely tight, a cap-blocked candidate keeps
    # only the cap message; the two reasons must never merge.
    cands = [_cand(i, 1) for i in range(1, 7)]
    limits = {1: PaperLimit(paper_id=1, max_count=2)}
    _, unplaced = place_candidates(2, 2, 1, cands, limits)
    assert sum(u["reason"] == REASON_CAP_FULL for u in unplaced) == 4
    assert all(REASON_NO_SEAT not in u["reason"] for u in unplaced)

def test_primary_floor_failure():
    assigns = [SeatAssign(1, "A", "T1", 1, 0, 0)]
    limits = {1: PaperLimit(paper_id=1, code="P-A", min_count=3, is_primary=True)}
    failures = primary_floor_failures(assigns, limits)
    assert len(failures) == 1
    assert failures[0]["seated"] == 1
    assert failures[0]["min_count"] == 3
    assert failures[0]["reason"] == REASON_PRIMARY_FLOOR

def test_floor_zero_disables_floor_and_non_primary_ignored():
    assigns = [SeatAssign(1, "A", "T1", 1, 0, 0)]
    limits = {
        1: PaperLimit(paper_id=1, min_count=0, is_primary=True),
        2: PaperLimit(paper_id=2, code="P-B", min_count=5, is_primary=False),
    }
    assert primary_floor_failures(assigns, limits) == []

def test_breakdown_totals_align():
    cands = [_cand(1, 1), _cand(2, 1), _cand(3, 1), _cand(4, 2)]
    limits = {
        1: PaperLimit(paper_id=1, code="P-A", max_count=2, min_count=1, is_primary=True),
        2: PaperLimit(paper_id=2, code="P-B"),
    }
    assigns, unplaced = place_candidates(3, 3, 1, cands, limits)
    breakdown = build_paper_breakdown(cands, assigns, unplaced, limits)
    by_pid = {b["paper_id"]: b for b in breakdown}
    assert by_pid[1]["total"] == 3
    assert by_pid[1]["seated"] == 2
    assert by_pid[1]["unplaced"] == 1
    assert by_pid[2]["total"] == by_pid[2]["seated"] == 1
    # Identity every view relies on: total == seated + unplaced.
    for b in breakdown:
        assert b["total"] == b["seated"] + b["unplaced"]
    # Floor holds in this attempt.
    assert primary_floor_failures(assigns, limits) == []
