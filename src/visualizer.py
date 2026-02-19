from typing import List, Dict, Tuple
import pyvista as pv
from .models import GraphNode, GraphEdge


class GraphVisualizer:
    def __init__(self, manage_window: bool = True):
        self.plotter = pv.Plotter()
        self._node_coords: Dict[str, Tuple[float, float, float]] = {}
        self._shown: bool = False

        # id узла -> (sphere_actor, label_actor)
        self._node_actors: Dict[str, Tuple[object, object]] = {}
        # (src, dst, kind) -> line_actor
        self._edge_actors: Dict[Tuple[str, str, str], object] = {}

        # актор вертикальной оси веток (через main)
        self._branch_axis_actor: object | None = None

        self.manage_window = manage_window

    def compute_layout(
            self, nodes: List[GraphNode], edges: List[GraphEdge]
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        Рассчитывает координаты узлов: коммиты (Z=0), ветки (вертикальный столб), HEAD (Z=0).
        """
        # 1. Группируем ID узлов по типам для удобства
        node_ids = {
            kind: [n.id for n in nodes if n.kind == kind]
            for kind in ["commit", "branch", "head"]
        }

        coords: Dict[str, Tuple[float, float, float]] = {}

        # 2. Размещаем коммиты (определяют базовую сетку по X)
        max_commit_x = self._layout_commits(node_ids["commit"], coords)

        # Задаем константы смещения колонок
        branch_x = max_commit_x + 1.5
        head_x = branch_x + 1.0

        # 3. Размещаем ветки (вертикальный столб с выравниванием по активной)
        active_id = self._find_active_branch(node_ids["branch"], node_ids["head"], edges)
        self._layout_branches(node_ids["branch"], branch_x, active_id, coords)

        # 4. Размещаем HEAD (всегда справа и на уровне Z=0)
        for hid in node_ids["head"]:
            coords[hid] = (head_x, 0.0, 0.0)

        self._node_coords = coords
        return coords

    # --- Вспомогательные методы (Private helpers) ---

    def _layout_commits(self, commit_ids: List[str], coords: Dict) -> float:
        """Размещает коммиты по горизонтали и возвращает крайнюю координату X."""
        for i, cid in enumerate(sorted(commit_ids, key=lambda x: int(x))):
            coords[cid] = (float(i), 0.0, 0.0)

        return max((coords[cid][0] for cid in commit_ids), default=0.0)

    def _find_active_branch(self, branch_ids: List[str], head_ids: List[str], edges: List[GraphEdge]) -> str:
        """Определяет ID активной ветки на основе связей HEAD."""
        if not head_ids:
            return ""

        # Ищем через ребро points_to
        for e in edges:
            if e.kind == "points_to" and e.source == head_ids[0] and e.target in branch_ids:
                return e.target

        # Fallback логика
        if "main" in branch_ids:
            return "main"
        return sorted(branch_ids)[0] if branch_ids else ""

    def _layout_branches(self, branch_ids: List[str], x: float, active_id: str, coords: Dict):
        """Логика формирования вертикального столба веток с сохранением истории."""
        branch_z_step = 0.6
        temp_z: Dict[str, float] = {}

        # Собираем существующие координаты Z из истории
        old_z_map = {
            bid: self._node_coords[bid][2]
            for bid in branch_ids if bid in self._node_coords
        }

        # Определяем начальную точку для новых веток (ниже всех существующих)
        new_z_cursor = min(old_z_map.values(), default=0.0 + branch_z_step)

        # Назначаем предварительные Z
        for bid in sorted(branch_ids):
            if bid in old_z_map:
                temp_z[bid] = old_z_map[bid]
            else:
                new_z_cursor -= branch_z_step
                temp_z[bid] = new_z_cursor

        # Сдвигаем весь столб так, чтобы активная ветка оказалась на Z = 0
        shift = -temp_z.get(active_id, 0.0)
        for bid in branch_ids:
            coords[bid] = (x, 0.0, temp_z[bid] + shift)

    def draw(
            self, nodes: List[GraphNode], edges: List[GraphEdge], show: bool = True
    ) -> None:
        """
        Инкрементальная перерисовка:
        - удаляем узлы/рёбра, которых больше нет;
        - обновляем позиции узлов, у которых изменились координаты;
        - добавляем новые узлы/рёбра.
        HEAD – крупный, ветки – средние, коммиты – маленькие полупрозрачные.
        """
        # сохраняем старые координаты до пересчёта layout
        old_coords = dict(self._node_coords)

        coords = self.compute_layout(nodes, edges)

        radii = {"commit": 0.08, "branch": 0.12, "head": 0.16}
        colors = {"commit": "skyblue", "branch": "orange", "head": "red"}

        new_node_ids = {n.id for n in nodes}
        old_node_ids = set(self._node_actors.keys())
        nodes_by_id = {n.id: n for n in nodes}

        # ---------- узлы: удаляем те, которых больше нет ----------
        for node_id in old_node_ids - new_node_ids:
            sphere_actor, label_actor = self._node_actors[node_id]
            self.plotter.remove_actor(sphere_actor)
            self.plotter.remove_actor(label_actor)
            del self._node_actors[node_id]

        # ---------- узлы: переcоздаём те, у кого изменились координаты ----------
        to_create = set()

        for node_id in new_node_ids & old_node_ids:
            old_pos = old_coords.get(node_id)
            new_pos = coords.get(node_id)
            if old_pos != new_pos:
                sphere_actor, label_actor = self._node_actors[node_id]
                self.plotter.remove_actor(sphere_actor)
                self.plotter.remove_actor(label_actor)
                del self._node_actors[node_id]
                to_create.add(node_id)

        # ---------- узлы: помечаем совсем новые к созданию ----------
        to_create |= (new_node_ids - old_node_ids)

        def create_node_actor(node_id: str) -> None:
            node = nodes_by_id[node_id]
            x, y, z = coords[node.id]
            radius = radii[node.kind]
            color = colors[node.kind]

            sphere = pv.Sphere(radius=radius, center=(x, y, z))
            opacity = 0.3 if node.kind == "commit" else 1.0
            sphere_actor = self.plotter.add_mesh(sphere, color=color, opacity=opacity)

            label_pos = (x, y, z) if node.kind == "commit" else (x, y + radius * 2.0, z)
            label_actor = self.plotter.add_point_labels(
                [label_pos],
                [node.label],
                font_size=10,
                point_size=0,
                text_color="black",
            )

            self._node_actors[node_id] = (sphere_actor, label_actor)

        for node_id in to_create:
            create_node_actor(node_id)

        # ---------- рёбра: для простоты пересоздаём все ----------
        for actor in list(self._edge_actors.values()):
            self.plotter.remove_actor(actor)
        self._edge_actors.clear()

        for e in edges:
            if e.source not in coords or e.target not in coords:
                continue
            x1, y1, z1 = coords[e.source]
            x2, y2, z2 = coords[e.target]

            line = pv.Line((x1, y1, z1), (x2, y2, z2))
            color = "gray" if e.kind == "parent" else "green"
            actor = self.plotter.add_mesh(line, color=color, line_width=2)
            key = (e.source, e.target, e.kind)
            self._edge_actors[key] = actor

            # ---------- вертикальная ось веток (через main) ----------
            # удаляем старую ось, если была
            if self._branch_axis_actor is not None:
                self.plotter.remove_actor(self._branch_axis_actor)
                self._branch_axis_actor = None

            # ищем узел main среди веток
            branch_nodes = [n for n in nodes if n.kind == "branch"]
            main_node = next((n for n in branch_nodes if n.id == "main"), None)

            if main_node is not None and main_node.id in coords:
                x_main, y_main, z_main = coords[main_node.id]

                # определяем диапазон z по всем веткам
                branch_z_values = [
                    coords[n.id][2]
                    for n in branch_nodes
                    if n.id in coords
                ]
                if branch_z_values:
                    z_min = min(branch_z_values)
                    z_max = max(branch_z_values)
                else:
                    z_min = z_max = z_main

                margin = 0.4  # небольшой отступ сверху/снизу
                z1 = z_min - margin
                z2 = z_max + margin

                axis_line = pv.Line((x_main, y_main, z1), (x_main, y_main, z2))
                self._branch_axis_actor = self.plotter.add_mesh(
                    axis_line,
                    color="black",
                    line_width=1,
                )

        # камера на все объекты
        self.plotter.reset_camera()

        # показ / обновление окна
        if self.manage_window:
            # старое поведение — сам управляет окном
            if not self._shown and show:
                self.plotter.show(auto_close=False, interactive_update=True)
                self._shown = True
            elif self._shown:
                self.plotter.render()
        else:
            # окном управляет внешний код (demo): просто перерендерим
            self.plotter.render()