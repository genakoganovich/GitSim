from src.models import Repo
from src.visualizer import GraphVisualizer


def run_demo():
    """
    Демо с таймлайном:
    - сценарий задаётся списком команд с параметрами;
    - после каждой команды сохраняем состояние графа (nodes, edges);
    - в одном окне PyVista стрелками вправо/влево ходим по этим состояниям.
    """
    repo = Repo()
    vis = GraphVisualizer(manage_window=False)  # окном управляем сами

    snapshots: list[tuple[list, list]] = []

    def snapshot():
        snapshots.append(repo.to_graph())

    # --- сценарий демо в виде списка команд ---
    # имя_метода Repo, параметры (как именованные аргументы)
    commands: list[tuple[str, dict]] = [
        ("init", {}),
        ("commit", {"message": "c1 on main"}),
        ("commit", {"message": "c2 on main"}),
        ("branch", {"name": "feature"}),
        ("checkout", {"name": "feature"}),
        ("commit", {"message": "c3 on feature"}),
        ("checkout", {"name": "main"}),
        ("merge", {"branch_name": "feature", "message": "Merge feature into main"}),
    ]

    # выполняем сценарий и собираем снимки
    for name, params in commands:
        method = getattr(repo, name)
        method(**params)
        snapshot()

    # --- навигация по таймлайну ---
    index = 0

    def show_current():
        nodes, edges = snapshots[index]
        vis.draw(nodes, edges, show=False)

    show_current()

    plotter = vis.plotter

    def on_right():
        nonlocal index
        if index < len(snapshots) - 1:
            index += 1
            show_current()
            print(f"Шаг вперёд: {index + 1}/{len(snapshots)}")

    def on_left():
        nonlocal index
        if index > 0:
            index -= 1
            show_current()
            print(f"Шаг назад: {index + 1}/{len(snapshots)}")

    plotter.add_key_event("Right", on_right)
    plotter.add_key_event("Left", on_left)

    print("Окно PyVista откроется. Управление историей:")
    print("  →  (Right Arrow)  — следующий шаг")
    print("  ←  (Left Arrow)   — предыдущий шаг")
    print("Закрой окно, чтобы завершить программу.")

    plotter.show()


if __name__ == "__main__":
    run_demo()