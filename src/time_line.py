from dataclasses import dataclass
from typing import Tuple, List

from src.command import Command, format_command
from src.models import Repo
from src.visualizer import GraphVisualizer

Snapshot = Tuple[List, List]


@dataclass
class Timeline:
    snapshots: List[Snapshot]
    commands: List[Command]
    command_texts: List[str]


def build_timeline(repo: Repo, commands: List[Command]) -> Timeline:
    snapshots: List[Snapshot] = []
    command_texts: List[str] = []

    for cmd in commands:
        method = getattr(repo, cmd.name)
        method(**cmd.params)
        snapshots.append(repo.to_graph())
        command_texts.append(format_command(cmd))

    return Timeline(snapshots=snapshots, commands=commands, command_texts=command_texts)


class TimelineViewer:
    def __init__(self, timeline: Timeline, vis: GraphVisualizer):
        self.timeline = timeline
        self.vis = vis
        self.index = 0

    @property
    def total_steps(self) -> int:
        return len(self.timeline.snapshots)

    def show_current(self) -> None:
        nodes, edges = self.timeline.snapshots[self.index]
        self.vis.draw(nodes, edges, show=False)

    def print_status(self, prefix: str) -> None:
        cmd_text = self.timeline.command_texts[self.index]
        print(f"{prefix} {self.index + 1}/{self.total_steps} | Команда: {cmd_text}")

    # коллбеки для PyVista
    def on_right(self) -> None:
        if self.index >= self.total_steps - 1:
            return
        self.index += 1
        self.show_current()
        self.print_status("Шаг вперёд →")

    def on_left(self) -> None:
        if self.index <= 0:
            return
        self.index -= 1
        self.show_current()
        self.print_status("Шаг назад ←")

    def run(self) -> None:
        self.show_current()
        plotter = self.vis.plotter

        plotter.add_key_event("Right", self.on_right)
        plotter.add_key_event("Left", self.on_left)

        print("Окно PyVista откроется. Управление историей:")
        print("  →  (Right Arrow)  — следующий шаг")
        print("  ←  (Left Arrow)   — предыдущий шаг")
        print("Закрой окно, чтобы завершить программу.")
        self.print_status("Начальное состояние:")

        plotter.show()
