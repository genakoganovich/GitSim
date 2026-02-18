from typing import Protocol

from .models import Repo, GraphNode, GraphEdge
from .visualizer import GraphVisualizer
import functools


def log_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"--- Вызывается метод: '{func.__name__}' с аргументами {args} и {kwargs}")
        return func(*args, **kwargs)

    return wrapper


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
        """
        Перестроить граф и обновить визуализацию.
        После обновления ждём ввода от пользователя.
        Параметр show здесь трактуем как «сделать паузу» (используется в демо).
        """
        nodes, edges = self.repo.to_graph()
        # Всегда передаём show=True в визуализатор:
        # - при первом вызове он откроет окно,
        # - далее просто будет делать render() в том же окне.
        self.visualizer.draw(nodes, edges, show=True)

        # Пошаговый режим: ждём, пока пользователь нажмёт Enter.
        # Можно ввести пробел и нажать Enter, как ты предлагал.
        # input("Нажмите Enter для продолжения...")

    @log_call
    def init(self, show: bool = False) -> None:
        self.repo.init()
        print()
        self._refresh(show=show)

    @log_call
    def commit(self, message: str, show: bool = False):
        result = self.repo.commit(message)
        self._refresh(show=show)
        return result

    @log_call
    def branch(self, name: str, show: bool = False):
        result = self.repo.branch(name)
        self._refresh(show=show)
        return result

    @log_call
    def checkout(self, name: str, show: bool = False) -> None:
        self.repo.checkout(name)
        self._refresh(show=show)

    @log_call
    def merge(self, branch_name: str, message: str = "Merge commit", show: bool = False):
        result = self.repo.merge(branch_name, message=message)
        self._refresh(show=show)
        return result
