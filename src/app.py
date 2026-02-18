from typing import Protocol

from .models import Repo, GraphNode, GraphEdge
from .visualizer import GraphVisualizer


class VisualizerProto(Protocol):
    def draw(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        show: bool = True,
    ) -> None: ...


class GitSimApp:
    """
    Обёртка над Repo + визуализатор.
    После каждой операции обновляет граф.
    """

    def __init__(self, visualizer: VisualizerProto | None = None):
        self.repo = Repo()
        self.visualizer: VisualizerProto = visualizer or GraphVisualizer()

    def _refresh(self, show: bool = False) -> None:
        nodes, edges = self.repo.to_graph()
        self.visualizer.draw(nodes, edges, show=show)

    def init(self, show: bool = False) -> None:
        self.repo.init()
        self._refresh(show=show)

    def commit(self, message: str, show: bool = False):
        result = self.repo.commit(message)
        self._refresh(show=show)
        return result

    def branch(self, name: str, show: bool = False):
        result = self.repo.branch(name)
        self._refresh(show=show)
        return result

    def checkout(self, name: str, show: bool = False) -> None:
        self.repo.checkout(name)
        self._refresh(show=show)

    def merge(self, branch_name: str, message: str = "Merge commit", show: bool = False):
        result = self.repo.merge(branch_name, message=message)
        self._refresh(show=show)
        return result