"""Canvas file I/O: parse and serialize Obsidian .canvas JSON."""

import json
import uuid

from some_vault_some_mcp.models import CanvasData, CanvasEdge, CanvasNode

_COLS = 4
_GAP_X = 50
_GAP_Y = 40


def generate_canvas_id() -> str:
    return uuid.uuid4().hex[:16]


def parse_canvas(raw: str) -> CanvasData:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed canvas JSON: {e}")

    if not isinstance(data, dict):
        raise ValueError("Canvas JSON root must be an object")

    nodes_raw = data.pop("nodes", [])
    edges_raw = data.pop("edges", [])

    nodes = [CanvasNode(**n) for n in nodes_raw]
    edges = [CanvasEdge(**e) for e in edges_raw]

    return CanvasData(nodes=nodes, edges=edges, extra=data)


def serialize_canvas(canvas: CanvasData) -> str:
    out = dict(canvas.extra)
    out["nodes"] = [n.model_dump(exclude_none=True) for n in canvas.nodes]
    out["edges"] = [e.model_dump(exclude_none=True) for e in canvas.edges]
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"


def find_node(canvas: CanvasData, node_id: str) -> CanvasNode | None:
    for n in canvas.nodes:
        if n.id == node_id:
            return n
    return None


def find_edge(canvas: CanvasData, edge_id: str) -> CanvasEdge | None:
    for e in canvas.edges:
        if e.id == edge_id:
            return e
    return None


def remove_dangling_edges(canvas: CanvasData, removed_node_ids: set[str]) -> list[str]:
    """Remove edges referencing any removed node. Mutates canvas.edges. Returns removed edge IDs."""
    removed_edge_ids = []
    surviving = []
    for e in canvas.edges:
        if e.fromNode in removed_node_ids or e.toNode in removed_node_ids:
            removed_edge_ids.append(e.id)
        else:
            surviving.append(e)
    canvas.edges = surviving
    return removed_edge_ids


def auto_position(canvas: CanvasData, width: int, height: int) -> tuple[int, int]:
    """Grid-based auto-placement for new nodes. 4-column grid, adapts cell size to largest node."""
    if not canvas.nodes:
        return (0, 0)

    cell_w = max(n.width for n in canvas.nodes) + _GAP_X
    cell_h = max(n.height for n in canvas.nodes) + _GAP_Y
    cell_w = max(cell_w, width + _GAP_X)
    cell_h = max(cell_h, height + _GAP_Y)

    origin_x = min(n.x for n in canvas.nodes)
    origin_y = min(n.y for n in canvas.nodes)

    occupied: set[tuple[int, int]] = set()
    for n in canvas.nodes:
        col = round((n.x - origin_x) / cell_w)
        row = round((n.y - origin_y) / cell_h)
        occupied.add((col, row))

    row = 0
    while True:
        for col in range(_COLS):
            if (col, row) not in occupied:
                return (origin_x + col * cell_w, origin_y + row * cell_h)
        row += 1
