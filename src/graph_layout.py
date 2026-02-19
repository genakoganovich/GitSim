from typing import List, Dict, Tuple
from .models import GraphNode, GraphEdge



class GraphLayout:
    def compute_layout(
            self, nodes: List[GraphNode], edges: List[GraphEdge]
    ) -> Dict[str, Tuple[float, float, float]]:

        # 1. Подготовка данных
        node_groups = self._group_nodes_by_kind(nodes)
        coords: Dict[str, Tuple[float, float, float]] = {}

        # 2. Располагаем коммиты (определяют базовый X)
        max_commit_x = self._layout_commits(node_groups["commit"], coords)

        branch_x = max_commit_x + 1.5
        head_x = branch_x + 1.0

        # 3. Располагаем ветки и выравниваем их по активной
        active_id = self._find_active_branch(node_groups["branch"], nodes, edges)
        self._layout_branches(node_groups["branch"], branch_x, active_id, coords)

        # 4. Располагаем HEAD
        for hid in node_groups["head"]:
            coords[hid] = (head_x, 0.0, 0.0)

        self._node_coords = coords
        return coords

    def _group_nodes_by_kind(self, nodes: List[GraphNode]) -> Dict[str, List[str]]:
        groups = {"commit": [], "branch": [], "head": []}
        for n in nodes:
            if n.kind in groups:
                groups[n.kind].append(n.id)
        return groups

    def _layout_commits(self, commit_ids: List[str], coords: Dict) -> float:
        """Размещает коммиты по X и возвращает максимальный X."""
        for i, cid in enumerate(sorted(commit_ids, key=lambda x: int(x))):
            coords[cid] = (float(i), 0.0, 0.0)
        return max([coords[cid][0] for cid in commit_ids], default=0.0)

    def _find_active_branch(self, branch_ids: List[str], nodes: List[GraphNode], edges: List[GraphEdge]) -> str:
        """Определяет, на какую ветку указывает HEAD."""
        head_ids = [n.id for n in nodes if n.kind == "head"]
        if not head_ids:
            return ""

        head_id = head_ids[0]
        for e in edges:
            if e.kind == "points_to" and e.source == head_id and e.target in branch_ids:
                return e.target

        # Fallback
        if "main" in branch_ids: return "main"
        return sorted(branch_ids)[0] if branch_ids else ""

    def _layout_branches(self, branch_ids: List[str], x: float, active_id: str, coords: Dict):
        """Логика вертикального столба веток с сохранением истории Z."""
        step = 0.6
        temp_z = {}

        # Восстанавливаем старые или создаем новые Z
        last_z = min([c[2] for c in self._node_coords.values() if c[2] < 0], default=0.0 + step)

        for bid in sorted(branch_ids):
            if bid in self._node_coords:
                temp_z[bid] = self._node_coords[bid][2]
            else:
                last_z -= step
                temp_z[bid] = last_z

        # Сдвиг, чтобы активная ветка была в Z=0
        shift = -temp_z.get(active_id, 0.0)
        for bid in branch_ids:
            coords[bid] = (x, 0.0, temp_z[bid] + shift)