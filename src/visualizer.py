from typing import List, Dict, Tuple

import pyvista as pv

from .models import GraphNode, GraphEdge


class GraphVisualizer:
    """
    Простая 3D-визуализация графа репозитория в PyVista.
    HEAD – крупный, ветки – средние, коммиты – маленькие полупрозрачные.
    Перерисовка инкрементальная: добавляем/удаляем только изменившиеся узлы/рёбра.
    """

    def __init__(self):
        self.plotter = pv.Plotter()
        self._node_coords: Dict[str, Tuple[float, float, float]] = {}
        self._shown: bool = False

        # id узла -> (sphere_actor, label_actor)
        self._node_actors: Dict[str, Tuple[object, object]] = {}
        # (src, dst, kind) -> line_actor
        self._edge_actors: Dict[Tuple[str, str, str], object] = {}

    def compute_layout(
        self, nodes: List[GraphNode], edges: List[GraphEdge]
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        Простейший layout:
        - коммиты по оси X на линии y=0
        - ветки на линии y=1
        - HEAD на линии y=2
        """
        coords: Dict[str, Tuple[float, float, float]] = {}

        commit_ids = [n.id for n in nodes if n.kind == "commit"]
        branch_ids = [n.id for n in nodes if n.kind == "branch"]
        head_ids = [n.id for n in nodes if n.kind == "head"]

        # Коммиты: сортируем по числовому hash'у (у нас 1,2,3,...)
        for i, cid in enumerate(sorted(commit_ids, key=lambda x: int(x))):
            coords[cid] = (float(i), 0.0, 0.0)

        # Ветки
        for i, bid in enumerate(sorted(branch_ids)):
            coords[bid] = (float(i), 1.0, 0.0)

        # HEAD
        for i, hid in enumerate(sorted(head_ids)):
            coords[hid] = (float(i), 2.0, 0.0)

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
                # координаты изменились -> удаляем старый актор и создаём заново
                sphere_actor, label_actor = self._node_actors[node_id]
                self.plotter.remove_actor(sphere_actor)
                self.plotter.remove_actor(label_actor)
                del self._node_actors[node_id]
                to_create.add(node_id)

        # ---------- узлы: помечаем совсем новые к созданию ----------
        to_create |= (new_node_ids - old_node_ids)

        # вспомогательная функция создания актора для узла
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

        # создаём все новые / перемещённые узлы
        for node_id in to_create:
            create_node_actor(node_id)

        # ---------- рёбра: для простоты пересоздаём все ----------
        # удаляем все старые рёбра
        for actor in list(self._edge_actors.values()):
            self.plotter.remove_actor(actor)
        self._edge_actors.clear()

        # создаём новые рёбра
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

        # камера на все объекты
        self.plotter.reset_camera()

        # показ / обновление окна
        if not self._shown and show:
            self.plotter.show(auto_close=False, interactive_update=True)
            self._shown = True
        elif self._shown:
            self.plotter.render()