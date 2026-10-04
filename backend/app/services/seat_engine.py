"""Exam seating: min Manhattan distance; same paper_id cannot be 4-neighbor adjacent.

Per-paper-set rules:
- max_seated (上限): a set at its cap takes no more candidates, even with seats free.
  Cap 0 means no truncation. Cap-blocked candidates are unplaced with reason 同卷人数已满.
- min_seated (下限) on the main set (主卷): if the main set seats fewer than the
  minimum, the whole run must be rejected (主卷人数不足) — aux sets never count toward it.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

REASON_PAPER_FULL = "同卷人数已满"
REASON_NO_SEAT = "无满足间距的空位"
REASON_MAIN_SHORT = "主卷人数不足"

@dataclass
class SeatAssign:
    candidate_id: int
    name: str
    ticket_no: str
    paper_id: int
    row: int
    col: int

@dataclass
class Violation:
    kind: str
    a_id: int
    b_id: int
    detail: str

def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def neighbors4(r: int, c: int, rows: int, cols: int) -> list[tuple[int, int]]:
    out = []
    for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            out.append((nr, nc))
    return out

def place_candidates(rows: int, cols: int, min_dist: int, candidates: list[dict],
                     caps: dict[int, int] | None = None) -> tuple[list[SeatAssign], list[dict]]:
    """Greedy: try seats row-major; accept if manhattan >= min_dist to all placed AND no same paper 4-neigh.

    caps: {paper_id: max seated}; 0 or missing means no cap. A set at its cap rejects
    further candidates of that set (reason 同卷人数已满) regardless of free seats.
    """
    caps = caps or {}
    seated_per_paper: dict[int, int] = {}
    occupied: dict[tuple[int, int], SeatAssign] = {}
    unplaced: list[dict] = []
    for cand in candidates:
        cap = caps.get(cand["paper_id"], 0)
        if cap > 0 and seated_per_paper.get(cand["paper_id"], 0) >= cap:
            unplaced.append({**cand, "reason": REASON_PAPER_FULL})
            continue
        placed = False
        for r in range(rows):
            for c in range(cols):
                if (r, c) in occupied:
                    continue
                ok = True
                for pos, other in occupied.items():
                    if manhattan((r, c), pos) < min_dist:
                        ok = False
                        break
                    if other.paper_id == cand["paper_id"] and (r, c) in neighbors4(pos[0], pos[1], rows, cols):
                        ok = False
                        break
                if not ok:
                    continue
                # also check 4-neigh same paper against current neighbors
                for nr, nc in neighbors4(r, c, rows, cols):
                    if (nr, nc) in occupied and occupied[(nr, nc)].paper_id == cand["paper_id"]:
                        ok = False
                        break
                if not ok:
                    continue
                assign = SeatAssign(cand["id"], cand["name"], cand["ticket_no"], cand["paper_id"], r, c)
                occupied[(r, c)] = assign
                seated_per_paper[cand["paper_id"]] = seated_per_paper.get(cand["paper_id"], 0) + 1
                placed = True
                break
            if placed:
                break
        if not placed:
            unplaced.append({**cand, "reason": REASON_NO_SEAT})
    return list(occupied.values()), unplaced

def main_minimum_met(assigns: list[SeatAssign], main_paper_id: int | None, min_seated: int) -> bool:
    """主卷保底: main set seated count must reach min_seated; min 0 (or no main set) disables it.
    Only the main set's own seats count — aux papers can never fill the quota."""
    if not main_paper_id or min_seated <= 0:
        return True
    return sum(1 for a in assigns if a.paper_id == main_paper_id) >= min_seated

def find_violations(rows: int, cols: int, min_dist: int, assigns: list[SeatAssign]) -> list[Violation]:
    viols: list[Violation] = []
    by_pos = {(a.row, a.col): a for a in assigns}
    for i, a in enumerate(assigns):
        for b in assigns[i + 1:]:
            d = manhattan((a.row, a.col), (b.row, b.col))
            if d < min_dist:
                viols.append(Violation("distance", a.candidate_id, b.candidate_id,
                                       f"曼哈顿距离 {d} < 最小要求 {min_dist}"))
            if a.paper_id == b.paper_id and (b.row, b.col) in neighbors4(a.row, a.col, rows, cols):
                viols.append(Violation("same_paper_adjacent", a.candidate_id, b.candidate_id,
                                       f"同试卷套 {a.paper_id} 四邻相邻"))
    return viols

def plan_to_dict(assigns: list[SeatAssign], unplaced: list[dict], viols: list[Violation], rows: int, cols: int) -> dict:
    per_paper: dict[int, dict] = {}
    for a in assigns:
        per_paper.setdefault(a.paper_id, {"seated": 0, "unplaced": 0})["seated"] += 1
    for u in unplaced:
        per_paper.setdefault(u["paper_id"], {"seated": 0, "unplaced": 0})["unplaced"] += 1
    return {
        "rows": rows,
        "cols": cols,
        "assignments": [asdict(a) for a in assigns],
        "unplaced": unplaced,
        "violations": [asdict(v) for v in viols],
        "stats": {
            "seated": len(assigns),
            "unplaced": len(unplaced),
            "violations": len(viols),
            "capacity": rows * cols,
            "per_paper": per_paper,
        },
    }
