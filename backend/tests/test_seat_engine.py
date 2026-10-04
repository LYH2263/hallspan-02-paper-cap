from app.services.seat_engine import (find_violations, main_minimum_met, manhattan,
                                      place_candidates, plan_to_dict, SeatAssign)

def test_manhattan():
    assert manhattan((0, 0), (2, 1)) == 3

def test_min_distance_placement():
    cands = [{"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": 1 + (i % 2)} for i in range(4)]
    assigns, unplaced = place_candidates(4, 4, 2, cands)
    assert len(assigns) + len(unplaced) == 4
    for i, a in enumerate(assigns):
        for b in assigns[i+1:]:
            assert manhattan((a.row, a.col), (b.row, b.col)) >= 2

def test_same_paper_not_adjacent_in_result():
    # Force two same paper — engine should avoid 4-neigh
    cands = [
        {"id": 1, "name": "A", "ticket_no": "T1", "paper_id": 1},
        {"id": 2, "name": "B", "ticket_no": "T2", "paper_id": 1},
        {"id": 3, "name": "C", "ticket_no": "T3", "paper_id": 2},
    ]
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

def test_paper_cap_blocks_even_with_free_seats():
    # 5x6 大量空格, 但同套上限 2: 第 3、4 人不得再塞同套
    cands = [{"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": 1} for i in range(4)]
    assigns, unplaced = place_candidates(5, 6, 2, cands, caps={1: 2})
    assert len(assigns) == 2
    assert len(unplaced) == 2
    assert all(u["reason"] == "同卷人数已满" for u in unplaced)

def test_cap_zero_means_no_truncation():
    cands = [{"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": 1} for i in range(4)]
    assigns, unplaced = place_candidates(5, 6, 2, cands, caps={1: 0})
    assert len(assigns) == 4
    assert not unplaced

def test_main_minimum_met():
    assigns = [SeatAssign(1, "A", "T1", 1, 0, 0), SeatAssign(2, "B", "T2", 2, 0, 2)]
    assert main_minimum_met(assigns, 1, 1)
    assert not main_minimum_met(assigns, 1, 2)
    assert main_minimum_met(assigns, 1, 0)       # 下限 0 关闭保底
    assert main_minimum_met(assigns, None, 5)    # 无主卷不校验
    assert not main_minimum_met(assigns, 2, 2)   # 辅卷人数不计入主卷保底

def test_per_paper_stats_alignment():
    assigns = [SeatAssign(1, "A", "T1", 1, 0, 0)]
    unplaced = [
        {"id": 2, "name": "B", "ticket_no": "T2", "paper_id": 1, "reason": "同卷人数已满"},
        {"id": 3, "name": "C", "ticket_no": "T3", "paper_id": 2, "reason": "无满足间距的空位"},
    ]
    d = plan_to_dict(assigns, unplaced, [], 2, 2)
    assert d["stats"]["per_paper"][1] == {"seated": 1, "unplaced": 1}
    assert d["stats"]["per_paper"][2] == {"seated": 0, "unplaced": 1}
    assert d["stats"]["seated"] == 1
    assert d["stats"]["unplaced"] == 2
