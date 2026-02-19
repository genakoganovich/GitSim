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
        Layout:
        - оси X,Y — горизонтальная плоскость, Z — вертикаль;
        - все коммиты и HEAD — всегда в плоскости z = 0;
        - ветки образуют вертикальный столб по Z в точке x = branch_x:
            * относительный порядок и расстояния между ветками сохраняются
              из предыдущих вызовов (берём self._node_coords);
            * при появлении новой ветки она добавляется внизу столба;
            * затем весь столб сдвигается вверх/вниз так, чтобы
              АКТИВНАЯ ветка (HEAD --points_to--> branch) оказалась в z = 0.
        """
        coords: Dict[str, Tuple[float, float, float]] = {}

        commit_ids = [n.id for n in nodes if n.kind == "commit"]
        branch_ids = [n.id for n in nodes if n.kind == "branch"]
        head_ids = [n.id for n in nodes if n.kind == "head"]

        # --- коммиты: по оси X, в плоскости z = 0 ---
        for i, cid in enumerate(sorted(commit_ids, key=lambda x: int(x))):
            coords[cid] = (float(i), 0.0, 0.0)  # (x, y, z)

        # базовая точка справа от последнего коммита
        if commit_ids:
            max_commit_x = max(coords[cid][0] for cid in commit_ids)
        else:
            max_commit_x = 0.0

        branch_x = max_commit_x + 1.5  # колонка веток
        head_x = branch_x + 1.0  # колонка HEAD

        # --- восстанавливаем старые z веток (для сохранения столба) ---
        old_branch_z: Dict[str, float] = {}
        for bid in branch_ids:
            if bid in self._node_coords:
                _, _, z = self._node_coords[bid]
                old_branch_z[bid] = z

        branch_z_step = 0.6

        # базовый z для НОВЫХ веток (если раньше их не было):
        # кладём их ещё ниже существующих
        if old_branch_z:
            min_old_z = min(old_branch_z.values())
            new_z_next = min_old_z - branch_z_step
        else:
            new_z_next = 0.0  # первая ветка пойдёт в z = 0

        # назначаем z всем веткам: старые сохраняем, новые добавляем ниже
        for bid in sorted(branch_ids):  # порядок по имени, но z берём из истории
            if bid in old_branch_z:
                z = old_branch_z[bid]
            else:
                z = new_z_next
                new_z_next -= branch_z_step
            coords[bid] = (branch_x, 0.0, z)

        # --- определяем активную ветку по ребру HEAD --points_to--> branch ---
        active_branch_id = None
        if head_ids:
            head_id = head_ids[0]  # у нас один HEAD
            for e in edges:
                if (
                        e.kind == "points_to"
                        and e.source == head_id
                        and e.target in branch_ids
                ):
                    active_branch_id = e.target
                    break

        # fallback, если по какой-то причине нет такого ребра
        if active_branch_id is None:
            if "main" in branch_ids:
                active_branch_id = "main"
            elif branch_ids:
                active_branch_id = sorted(branch_ids)[0]

        # --- сдвигаем ВЕСЬ столб веток так, чтобы активная ветка стала в z = 0 ---
        if active_branch_id is not None and active_branch_id in coords:
            _, _, active_z = coords[active_branch_id]
            shift = -active_z  # на сколько надо поднять/опустить столб
            for bid in branch_ids:
                x, y, z = coords[bid]
                coords[bid] = (x, y, z + shift)

        # --- HEAD: всегда в плоскости коммитов z = 0, правее веток ---
        for hid in head_ids:
            coords[hid] = (head_x, 0.0, 0.0)

        self._node_coords = coords
        return coords

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