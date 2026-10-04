"""Exam seating: min Manhattan distance; same paper_id cannot be 4-neighbor adjacent.

Per-paper-set rules:
- max_count: hard cap on seated count of one paper set. 0 means no cap.
  Once a set hits its cap, its remaining candidates are unplaced with reason
  "同卷人数已满" even if empty seats exist — caps are mutually exclusive with
  "fill every empty seat".
- min_count on the primary paper set: seated floor. 0 switches the floor off.
  When the primary set seats fewer than its floor the whole run must fail;
  auxiliary sets must never be used to paper over empty seats.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

# Unplaced / failure reasons. Kept as exact constants: capped unplaced only
# ever carries the cap message, floor failure only ever carries the floor one.
REASON_CAP_FULL = "同卷人数已满"
REASON_NO_SEAT = "无可用座位"
REASON_PRIMARY_FLOOR = "主卷人数不足"

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

@dataclass
class PaperLimit:
    paper_id: int
    code: str = ""
    title: str = ""
    max_count: int = 0   # 0 = no cap
    min_count: int = 0   # 0 = floor off
    is_primary: bool = False

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
                     limits: dict[int, PaperLimit] | None = None
                     ) -> tuple[list[SeatAssign], list[dict]]:
    """Greedy: try seats row-major; accept if manhattan >= min_dist to all placed AND no same paper 4-neigh.

    A paper set whose max_count (>0) has been reached never gets another seat,
    regardless of empty capacity; such candidates are unplaced with the cap
    reason only.
    """
    limits = limits or {}
    occupied: dict[tuple[int, int], SeatAssign] = {}
    seated_per_paper: dict[int, int] = {}
    unplaced: list[dict] = []
    for cand in candidates:
        pid = cand["paper_id"]
        limit = limits.get(pid)
        if limit is not None and limit.max_count > 0 and seated_per_paper.get(pid, 0) >= limit.max_count:
            # Hard cap reached: do not even scan for empty seats.
            unplaced.append({**cand, "reason": REASON_CAP_FULL})
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
                    if other.paper_id == pid and (r, c) in neighbors4(pos[0], pos[1], rows, cols):
                        ok = False
                        break
                if not ok:
                    continue
                # also check 4-neigh same paper against current neighbors
                for nr, nc in neighbors4(r, c, rows, cols):
                    if (nr, nc) in occupied and occupied[(nr, nc)].paper_id == pid:
                        ok = False
                        break
                if not ok:
                    continue
                assign = SeatAssign(cand["id"], cand["name"], cand["ticket_no"], pid, r, c)
                occupied[(r, c)] = assign
                seated_per_paper[pid] = seated_per_paper.get(pid, 0) + 1
                placed = True
                break
            if placed:
                break
        if not placed:
            unplaced.append({**cand, "reason": REASON_NO_SEAT})
    return list(occupied.values()), unplaced

def primary_floor_failures(assigns: list[SeatAssign], limits: dict[int, PaperLimit]) -> list[dict]:
    """Primary paper sets whose seated count is below min_count (min_count > 0 only)."""
    seated_per_paper: dict[int, int] = {}
    for a in assigns:
        seated_per_paper[a.paper_id] = seated_per_paper.get(a.paper_id, 0) + 1
    failures: list[dict] = []
    for limit in limits.values():
        if not limit.is_primary or limit.min_count <= 0:
            continue
        seated = seated_per_paper.get(limit.paper_id, 0)
        if seated < limit.min_count:
            failures.append({
                "paper_id": limit.paper_id,
                "code": limit.code,
                "seated": seated,
                "min_count": limit.min_count,
                "reason": REASON_PRIMARY_FLOOR,
            })
    return failures

def build_paper_breakdown(candidates: list[dict], assigns: list[SeatAssign],
                          unplaced: list[dict], limits: dict[int, PaperLimit]) -> list[dict]:
    """Single source of truth for per-set totals shared by roster / map / stats."""
    total_per_paper: dict[int, int] = {}
    for cand in candidates:
        total_per_paper[cand["paper_id"]] = total_per_paper.get(cand["paper_id"], 0) + 1
    seated_per_paper: dict[int, int] = {}
    for a in assigns:
        seated_per_paper[a.paper_id] = seated_per_paper.get(a.paper_id, 0) + 1
    unplaced_per_paper: dict[int, int] = {}
    for u in unplaced:
        unplaced_per_paper[u["paper_id"]] = unplaced_per_paper.get(u["paper_id"], 0) + 1
    pids = sorted(total_per_paper.keys() | {l.paper_id for l in limits.values()})
    out: list[dict] = []
    for pid in pids:
        limit = limits.get(pid)
        total = total_per_paper.get(pid, 0)
        seated = seated_per_paper.get(pid, 0)
        out.append({
            "paper_id": pid,
            "code": limit.code if limit else "",
            "title": limit.title if limit else "",
            "is_primary": bool(limit.is_primary) if limit else False,
            "max_count": limit.max_count if limit else 0,
            "min_count": limit.min_count if limit else 0,
            "total": total,
            "seated": seated,
            "unplaced": unplaced_per_paper.get(pid, 0),
        })
    return out

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

def plan_to_dict(assigns: list[SeatAssign], unplaced: list[dict], viols: list[Violation],
                 rows: int, cols: int, paper_breakdown: list[dict] | None = None,
                 limits_snapshot: list[dict] | None = None) -> dict:
    return {
        "rows": rows,
        "cols": cols,
        "assignments": [asdict(a) for a in assigns],
        "unplaced": unplaced,
        "violations": [asdict(v) for v in viols],
        "paper_breakdown": paper_breakdown or [],
        "limits_snapshot": limits_snapshot or [],
        "stats": {
            "seated": len(assigns),
            "unplaced": len(unplaced),
            "violations": len(viols),
            "capacity": rows * cols,
        },
    }
