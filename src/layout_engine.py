# layout_engine.py

from typing import Dict, List, Tuple, Optional
from .models import GraphNode, GraphEdge


class LayoutEngine:
    BRANCH_COLUMN_OFFSET = 1.5
    HEAD_COLUMN_OFFSET = 1.0
    BRANCH_Z_STEP = 0.6

    def __init__(self) -> None:
        self._node_coords: Dict[str, Tuple[float, float, float]] = {}

    def get_coords(self) -> Dict[str, Tuple[float, float, float]]:
        return dict(self._node_coords)

    def compute_layout(
            self,
            nodes: List["GraphNode"],
            edges: List["GraphEdge"],
    ) -> Dict[str, Tuple[float, float, float]]:

        commit_ids, branch_ids, head_ids = self._split_nodes(nodes)

        coords: Dict[str, Tuple[float, float, float]] = {}

        branch_x, head_x = self._layout_commits(commit_ids, coords)

        self._layout_branches(branch_ids, branch_x, coords)

        active_branch_id = self._detect_active_branch(
            branch_ids, head_ids, edges
        )

        self._normalize_branch_column(
            branch_ids, active_branch_id, coords
        )

        self._layout_heads(head_ids, head_x, coords)

        self._node_coords = coords
        return coords

    # =========================
    # Stage 1 — Split nodes
    # =========================

    def _split_nodes(
            self,
            nodes: List["GraphNode"],
    ) -> Tuple[List[str], List[str], List[str]]:

        commit_ids = [n.id for n in nodes if n.kind == "commit"]
        branch_ids = [n.id for n in nodes if n.kind == "branch"]
        head_ids = [n.id for n in nodes if n.kind == "head"]

        return commit_ids, branch_ids, head_ids

    # =========================
    # Stage 2 — Layout commits
    # =========================

    def _layout_commits(
            self,
            commit_ids: List[str],
            coords: Dict[str, Tuple[float, float, float]],
    ) -> Tuple[float, float]:

        for i, cid in enumerate(sorted(commit_ids, key=int)):
            coords[cid] = (float(i), 0.0, 0.0)

        if commit_ids:
            max_commit_x = max(coords[cid][0] for cid in commit_ids)
        else:
            max_commit_x = 0.0

        branch_x = max_commit_x + self.BRANCH_COLUMN_OFFSET
        head_x = branch_x + self.HEAD_COLUMN_OFFSET

        return branch_x, head_x

    # =========================
    # Stage 3 — Layout branches
    # =========================

    def _layout_branches(
            self,
            branch_ids: List[str],
            branch_x: float,
            coords: Dict[str, Tuple[float, float, float]],
    ) -> None:

        previous_branch_z = self._restore_previous_branch_z(branch_ids)

        if previous_branch_z:
            min_old_z = min(previous_branch_z.values())
            next_new_branch_z = min_old_z - self.BRANCH_Z_STEP
        else:
            next_new_branch_z = 0.0

        for bid in sorted(branch_ids):
            if bid in previous_branch_z:
                z = previous_branch_z[bid]
            else:
                z = next_new_branch_z
                next_new_branch_z -= self.BRANCH_Z_STEP

            coords[bid] = (branch_x, 0.0, z)

    def _restore_previous_branch_z(
            self,
            branch_ids: List[str],
    ) -> Dict[str, float]:

        result: Dict[str, float] = {}

        for bid in branch_ids:
            if bid in self._node_coords:
                _, _, z = self._node_coords[bid]
                result[bid] = z

        return result

    # =========================
    # Stage 4 — Detect active branch
    # =========================

    def _detect_active_branch(
            self,
            branch_ids: List[str],
            head_ids: List[str],
            edges: List["GraphEdge"],
    ) -> Optional[str]:

        if not head_ids:
            return self._fallback_branch(branch_ids)

        head_id = head_ids[0]

        for e in edges:
            if (
                    e.kind == "points_to"
                    and e.source == head_id
                    and e.target in branch_ids
            ):
                return e.target

        return self._fallback_branch(branch_ids)

    def _fallback_branch(
            self,
            branch_ids: List[str],
    ) -> Optional[str]:

        if "main" in branch_ids:
            return "main"

        if branch_ids:
            return sorted(branch_ids)[0]

        return None

    # =========================
    # Stage 5 — Normalize branch column
    # =========================

    def _normalize_branch_column(
            self,
            branch_ids: List[str],
            active_branch_id: Optional[str],
            coords: Dict[str, Tuple[float, float, float]],
    ) -> None:

        if not active_branch_id:
            return

        if active_branch_id not in coords:
            return

        _, _, active_z = coords[active_branch_id]
        z_shift = -active_z

        for bid in branch_ids:
            x, y, z = coords[bid]
            coords[bid] = (x, y, z + z_shift)

    # =========================
    # Stage 6 — Layout heads
    # =========================

    def _layout_heads(
            self,
            head_ids: List[str],
            head_x: float,
            coords: Dict[str, Tuple[float, float, float]],
    ) -> None:

        for hid in head_ids:
            coords[hid] = (head_x, 0.0, 0.0)
