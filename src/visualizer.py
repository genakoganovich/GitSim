from typing import List, Dict, Tuple

import pyvista as pv

from .models import GraphNode, GraphEdge


class GraphVisualizer:
    """
    Простая 3D-визуализация графа репозитория в PyVista.
    """

    def __init__(self):
        self.plotter = pv.Plotter()
        self._node_coords: Dict[str, Tuple[float, float, float]] = {}
        self._shown: bool = False  # окно уже показано или нет

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
        Перерисовать граф в текущем Plotter'е.
        Первый вызов с show=True открывает окно (неблокирующее),
        последующие вызовы только обновляют содержимое в том же окне.
        Камера каждый раз сбрасывается так, чтобы граф был целиком в кадре.
        """
        self.plotter.clear()
        coords = self.compute_layout(nodes, edges)

        # Узлы
        for node in nodes:
            x, y, z = coords[node.id]
            color = {
                "commit": "skyblue",
                "branch": "orange",
                "head": "red",
            }[node.kind]

            sphere = pv.Sphere(radius=0.1, center=(x, y, z))
            self.plotter.add_mesh(sphere, color=color)

            self.plotter.add_point_labels(
                [[x, y, z]],
                [node.label],
                font_size=10,
                point_size=0,
                text_color="black",
            )

        # Рёбра
        for edge in edges:
            if edge.source not in coords or edge.target not in coords:
                continue
            x1, y1, z1 = coords[edge.source]
            x2, y2, z2 = coords[edge.target]

            line = pv.Line((x1, y1, z1), (x2, y2, z2))
            color = "gray" if edge.kind == "parent" else "green"
            self.plotter.add_mesh(line, color=color, line_width=2)

        # Подгоняем камеру так, чтобы все акторы были в кадре
        self.plotter.reset_camera()

        # Показ / обновление окна
        if not self._shown and show:
            self.plotter.show(auto_close=False, interactive_update=True)
            self._shown = True
        elif self._shown:
            self.plotter.render()