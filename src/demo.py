from typing import Optional

from src.command import load_default_commands, load_commands_from_yaml
from src.models import Repo
from src.time_line import build_timeline, TimelineViewer
from src.visualizer import GraphVisualizer


def run_demo(yaml_path: Optional[str] = None) -> None:
    repo = Repo()
    vis = GraphVisualizer(manage_window=False)

    if yaml_path:
        commands = load_commands_from_yaml(yaml_path)
    else:
        commands = load_default_commands()

    timeline = build_timeline(repo, commands)
    viewer = TimelineViewer(timeline, vis)
    viewer.run()


if __name__ == "__main__":
    # можно вызывать так:
    # run_demo()                          # встроенный сценарий
    run_demo("scenario.yaml")           # сценарий из YAML
    # run_demo("new_branch_scenario.yaml")           # сценарий из YAML
    # run_demo()
