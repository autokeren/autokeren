"""Visual diagram renderer — gambar flowchart & sequence di terminal.

Pakai Unicode box-drawing chars: ┌─┐│└┘└┘▼╭╮╰╯
Flowchart: kotak per node, panah antar level, branch/merge.
Sequence: lifelines vertikal, panah horizontal antar participant.
"""
from __future__ import annotations

import re
from collections import defaultdict, deque

from rich.console import Console

_BOX_PAD = 2
_COL_GAP = 4
_LINE_H = 7  # box(3) + arrow/branch(4)


class Canvas:
    """2D character buffer untuk gambar diagram."""

    def __init__(self, width: int, height: int) -> None:
        self.w = width
        self.h = height
        self.grid: list[list[str]] = [[" "] * width for _ in range(height)]

    def put(self, x: int, y: int, text: str) -> None:
        for i, c in enumerate(text):
            if 0 <= y < self.h and 0 <= x + i < self.w:
                if c != " " or self.grid[y][x + i] == " ":
                    self.grid[y][x + i] = c

    def render(self) -> str:
        return "\n".join("".join(row).rstrip() for row in self.grid)


def _box_w(label: str) -> int:
    return max(len(label) + _BOX_PAD * 2, 6)


def _draw_box(cv: Canvas, cx: int, y: int, label: str, shape: str) -> int:
    """Gambar box center di cx. Return width."""
    w = _box_w(label)
    x = cx - w // 2
    inner = w - 2
    pad = (inner - len(label)) // 2
    lp = " " * pad + label + " " * (inner - pad - len(label))

    tl, tr, bl, br = "┌┐└┘"
    if shape == "{}":
        tl, tr, bl, br = "╭╮╰╯"
    cv.put(x, y, f"{tl}{'─' * inner}{tr}")
    cv.put(x, y + 1, f"│{lp}│")
    cv.put(x, y + 2, f"{bl}{'─' * inner}{br}")
    return w


def _draw_arrow_v(cv: Canvas, x: int, y: int, label: str = "") -> int:
    """Panah vertikal ke bawah (2 baris). Return rows used."""
    cv.put(x, y, "│")
    if label:
        cv.put(x + 2, y, label)
    cv.put(x, y + 1, "▼")
    return 2


def _draw_branch(cv: Canvas, cx: int, y: int, targets: list[tuple[int, str]]) -> int:
    """Branch dari cx ke beberapa target (x, label). Return rows used."""
    if len(targets) == 1:
        tx, tlbl = targets[0]
        if tx == cx:
            cv.put(cx, y, "│")
            if tlbl:
                cv.put(cx + 1, y, f" {tlbl}")
            cv.put(cx, y + 1, "▼")
            return 2
        cv.put(cx, y, "│")
        cv.put(cx, y + 1, "┐" if tx < cx else "┌")
        cv.put(tx, y + 1, "┌" if tx < cx else "┐")
        for x in range(min(cx, tx) + 1, max(cx, tx)):
            cv.put(x, y + 1, "─")
        if tlbl:
            mid = (cx + tx) // 2
            cv.put(mid - len(tlbl) // 2, y + 1, tlbl[:8])
        cv.put(tx, y + 2, "│")
        cv.put(tx, y + 3, "▼")
        return 4

    xs = [t[0] for t in targets] + [cx]
    min_x, max_x = min(xs), max(xs)

    cv.put(cx, y, "│")
    cv.put(cx, y + 1, "┬")
    for x in range(min_x, max_x + 1):
        if x != cx:
            cv.put(x, y + 1, "─")
    for tx, tlbl in targets:
        if tx < cx:
            cv.put(tx, y + 1, "┌")
        elif tx > cx:
            cv.put(tx, y + 1, "┐")
        if tlbl:
            if tx == cx:
                cv.put(tx + 1, y + 2, tlbl[:8])
            else:
                mid = (cx + tx) // 2
                if mid != cx and mid != tx:
                    cv.put(mid - len(tlbl) // 2, y + 1, tlbl[:8])
        cv.put(tx, y + 2, "│")
        cv.put(tx, y + 3, "▼")
    return 4


def _draw_merge(cv: Canvas, sources: list[int], cx: int, y: int) -> int:
    """Merge dari beberapa source ke cx. Return rows used."""
    if len(sources) == 1:
        sx = sources[0]
        if sx == cx:
            cv.put(cx, y, "│")
            cv.put(cx, y + 1, "▼")
        else:
            cv.put(sx, y, "│")
            cv.put(sx, y + 1, "┘" if sx < cx else "└")
            for x in range(min(sx, cx) + 1, max(sx, cx)):
                cv.put(x, y + 1, "─")
            cv.put(cx, y + 1, "┴")
            cv.put(cx, y + 2, "│")
            cv.put(cx, y + 3, "▼")
        return 2 if sx == cx else 4

    min_x, max_x = min(sources), max(sources)
    for sx in sources:
        cv.put(sx, y, "│")
    for x in range(min_x, max_x + 1):
        cv.put(x, y + 1, "─")
    for sx in sources:
        if sx == min_x:
            cv.put(sx, y + 1, "└")
        elif sx == max_x:
            cv.put(sx, y + 1, "┘")
    cv.put(cx, y + 1, "┴")
    cv.put(cx, y + 2, "│")
    cv.put(cx, y + 3, "▼")
    return 4


# ------------------------------------------------------------------ #
# Flowchart
# ------------------------------------------------------------------ #

_NODE_SHAPE = r"(?:\[([^\]]*)\]|\(([^)]*)\)|\{([^}]*)\}|\(\(([^)]*)\)\))?"
_EDGE_RE = re.compile(
    rf"(\w+){_NODE_SHAPE}\s*(-->|->|==>|-\.->|--x)\s*(?:\|([^|]*)\|\s*)?(\w+){_NODE_SHAPE}"
)


def render_flowchart_visual(lines: list[str], console: Console) -> bool:
    """Render flowchart sebagai visual boxes. Return False kalau gagal."""
    nodes: dict[str, tuple[str, str]] = {}
    edges: list[tuple[str, str, str]] = []

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("graph", "flowchart")):
            continue
        parts0 = line.split()
        if parts0 and parts0[0] in ("TD", "LR", "TB", "RL", "BT"):
            line = line.split(None, 1)[1] if len(parts0) > 1 else ""

        for m in _EDGE_RE.finditer(line):
            sid = m.group(1)
            slabel = m.group(2) or m.group(3) or m.group(4) or m.group(5) or sid
            sshape = "[]" if m.group(2) else "{}" if m.group(4) else "()"
            elabel = m.group(7) or ""
            did = m.group(8)
            dlabel = m.group(9) or m.group(10) or m.group(11) or m.group(12) or did
            dshape = "[]" if m.group(9) else "{}" if m.group(11) else "()"

            if slabel != sid or sid not in nodes:
                nodes[sid] = (slabel, sshape)
            if dlabel != did or did not in nodes:
                nodes[did] = (dlabel, dshape)
            edges.append((sid, did, elabel))

    if not nodes or not edges:
        return False

    levels = _compute_levels(nodes, edges)
    if not levels:
        return False

    positions = _layout(nodes, edges, levels)
    _draw_flowchart(nodes, edges, levels, positions, console)
    return True


def _compute_levels(
    nodes: dict[str, tuple[str, str]], edges: list[tuple[str, str, str]]
) -> dict[str, int]:
    """Assign level (row) ke setiap node via BFS dari roots (shortest path)."""
    incoming: dict[str, list[str]] = defaultdict(list)
    outgoing: dict[str, list[str]] = defaultdict(list)
    for s, d, _ in edges:
        outgoing[s].append(d)
        incoming[d].append(s)

    roots = [n for n in nodes if not incoming[n]]
    if not roots:
        roots = list(nodes)[:1]

    levels: dict[str, int] = {}
    q: deque[str] = deque()
    for r in roots:
        levels[r] = 0
        q.append(r)

    while q:
        n = q.popleft()
        for child in outgoing[n]:
            if child not in levels:
                levels[child] = levels[n] + 1
                q.append(child)

    for nid in nodes:
        if nid not in levels:
            levels[nid] = 0

    return levels


def _layout(
    nodes: dict[str, tuple[str, str]],
    edges: list[tuple[str, str, str]],
    levels: dict[str, int],
) -> dict[str, int]:
    """Assign column (x) ke setiap node. Return {node_id: col_x}."""
    by_level: dict[int, list[str]] = defaultdict(list)
    for nid, lvl in levels.items():
        by_level[lvl].append(nid)

    positions: dict[str, int] = {}
    col = 0
    for nid in by_level.get(0, []):
        positions[nid] = col
        col += 1

    for lvl in range(1, max(by_level) + 1):
        level_nodes = by_level.get(lvl, [])
        incoming: dict[str, list[str]] = defaultdict(list)
        for s, d, _ in edges:
            if d in level_nodes and s in positions:
                incoming[d].append(s)

        used_cols: set[int] = set()
        for nid in level_nodes:
            parents = incoming[nid]
            if parents:
                avg = sum(positions[p] for p in parents) // len(parents)
            else:
                avg = 0

            while avg in used_cols:
                avg += 1
            positions[nid] = avg
            used_cols.add(avg)

    return positions


def _draw_flowchart(
    nodes: dict[str, tuple[str, str]],
    edges: list[tuple[str, str, str]],
    levels: dict[str, int],
    positions: dict[str, int],
    console: Console,
) -> None:
    by_level: dict[int, list[str]] = defaultdict(list)
    for nid, lvl in levels.items():
        by_level[lvl].append(nid)

    max_lvl = max(by_level) if by_level else 0
    col_w = max(_box_w(label) for label, _ in nodes.values()) + _COL_GAP
    max_cols = max(len(v) for v in by_level.values()) if by_level else 1
    cv_w = col_w * max_cols + 4

    rows = (max_lvl + 1) * _LINE_H + 4
    cv = Canvas(cv_w, rows)

    incoming: dict[str, list[str]] = defaultdict(list)
    outgoing: dict[str, list[str]] = defaultdict(list)
    edge_labels: dict[tuple[str, str], str] = {}
    for s, d, lbl in edges:
        outgoing[s].append(d)
        incoming[d].append(s)
        if lbl:
            edge_labels[(s, d)] = lbl

    for lvl in range(max_lvl + 1):
        y = lvl * _LINE_H + 1
        for nid in by_level[lvl]:
            label, shape = nodes[nid]
            cx = positions[nid] * col_w + col_w // 2 + 2
            _draw_box(cv, cx, y, label, shape)

        if lvl < max_lvl:
            next_nodes = by_level[lvl + 1]
            ay = y + 3

            for nid in by_level[lvl]:
                children = [c for c in outgoing[nid] if c in next_nodes]
                if not children:
                    continue
                cx = positions[nid] * col_w + col_w // 2 + 2
                targets = [
                    (positions[c] * col_w + col_w // 2 + 2, edge_labels.get((nid, c), ""))
                    for c in children
                ]
                _draw_branch(cv, cx, ay, targets)

            for nid in next_nodes:
                parents = [p for p in incoming[nid] if p in by_level[lvl]]
                if len(parents) > 1:
                    cx = positions[nid] * col_w + col_w // 2 + 2
                    srcs = [positions[p] * col_w + col_w // 2 + 2 for p in parents]
                    gap = ay + 4
                    _draw_merge(cv, srcs, cx, gap)

    for line in cv.render().splitlines():
        if line.strip():
            console.print(f"  [dim]{line}[/dim]")


# ------------------------------------------------------------------ #
# Sequence Diagram
# ------------------------------------------------------------------ #


def render_sequence_visual(lines: list[str], console: Console) -> bool:
    """Render sequence diagram dengan lifelines & arrows."""
    participants: dict[str, str] = {}
    events: list[dict] = []
    indent_stack: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("autonumber", "sequenceDiagram")):
            continue

        if line.startswith(("participant ", "actor ")):
            parts = line.split(None, 2)
            key = parts[1] if len(parts) > 1 else ""
            alias = key
            if len(parts) > 2 and parts[2].startswith("as "):
                alias = parts[2][3:].strip().strip('"')
            elif len(parts) > 2:
                alias = parts[2].strip().strip('"')
            participants[key] = alias
            continue

        if line.startswith("Note "):
            events.append({"type": "note", "text": line.split(":", 1)[1].strip() if ":" in line else ""})
            continue
        if line.startswith("loop "):
            indent_stack.append("loop")
            events.append({"type": "loop_start", "text": line[5:].strip()})
            continue
        if line.startswith("alt "):
            indent_stack.append("alt")
            events.append({"type": "alt_start", "text": line[4:].strip()})
            continue
        if line.startswith("else "):
            events.append({"type": "else", "text": line[5:].strip()})
            continue
        if line == "end" and indent_stack:
            indent_stack.pop()
            events.append({"type": "block_end"})
            continue

        m = re.match(r"(\w+)\s*(-->>|-->|->>|->|-\)|--x|-x|>>>)\s*(\w+)(?::\s*(.*))?", line)
        if m:
            src, arrow, dst, msg = m.groups()
            if src not in participants:
                participants[src] = src
            if dst not in participants:
                participants[dst] = dst
            events.append({"type": "msg", "src": src, "dst": dst, "arrow": arrow, "text": msg or ""})

    if not participants or not events:
        return False

    _draw_sequence(participants, events, console)
    return True


def _draw_sequence(participants: dict[str, str], events: list[dict], console: Console) -> None:
    names = list(participants.values())
    n = len(names)
    col_w = max(max(len(name) for name in names) + 6, 20)
    cv_w = col_w * n + 4

    row_h = 2
    cv_h = 6 + len(events) * row_h
    cv = Canvas(cv_w, cv_h)

    xs = [i * col_w + col_w // 2 + 2 for i in range(n)]
    name_to_x = {name: xs[i] for i, name in enumerate(names)}
    pid_to_name = {k: v for k, v in participants.items()}

    # Header boxes
    y = 0
    for i, name in enumerate(names):
        _draw_box(cv, xs[i], y, name, "[]")
    y += 3

    # Messages (calculate actual height first)
    cur_y = y + 1
    msg_rows: list[tuple[int, dict]] = []
    for ev in events:
        if ev["type"] in ("loop_start", "alt_start", "else", "block_end", "note"):
            msg_rows.append((cur_y, ev))
            cur_y += 1
        elif ev["type"] == "msg":
            msg_rows.append((cur_y, ev))
            cur_y += 1

    end_y = cur_y + 1

    # Lifelines (only up to last event)
    for line_y in range(y, end_y):
        for x in xs:
            cv.put(x, line_y, "│")

    # Draw messages
    for row_y, ev in msg_rows:
        if ev["type"] == "loop_start":
            cv.put(2, row_y, f"↻ {ev['text']}")
        elif ev["type"] == "alt_start":
            cv.put(2, row_y, f"◆ IF: {ev['text']}")
        elif ev["type"] == "else":
            cv.put(2, row_y, f"◆ ELSE: {ev['text']}")
        elif ev["type"] == "note":
            cv.put(4, row_y, f"📝 {ev['text']}")
        elif ev["type"] == "msg":
            src_name = pid_to_name.get(ev["src"] or "", ev["src"] or "")
            dst_name = pid_to_name.get(ev["dst"] or "", ev["dst"] or "")
            sx = name_to_x.get(src_name, xs[0])
            dx = name_to_x.get(dst_name, xs[-1])
            text = ev["text"]

            if sx == dx:
                cv.put(sx + 1, row_y, f"↓ {text}")
            elif sx < dx:
                length = dx - sx - 1
                line = "─" * length
                if text:
                    mid = length // 2 - len(text) // 2
                    line = line[:mid] + text + line[mid + len(text):]
                cv.put(sx + 1, row_y, f"{line}→")
            else:
                length = sx - dx - 1
                line = "─" * length
                if text:
                    mid = length // 2 - len(text) // 2
                    line = line[:mid] + text + line[mid + len(text):]
                cv.put(dx + 1, row_y, f"←{line}")

    for line in cv.render().splitlines():
        if line.strip():
            console.print(f"  [dim]{line}[/dim]")
