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

    # вспомогательная функция для красивого вывода команды
    def format_command(name: str, params: dict) -> str:
        """commit(message='c1 on main')"""
        if not params:
            return f"{name}()"
        params_str = ", ".join(f"{k}={v!r}" for k, v in params.items())
        return f"{name}({params_str})"

    # список команд в том же порядке, что и snapshots
    command_info = [format_command(name, params) for name, params in commands]

    # выполняем сценарий и собираем снимки
    for name, params in commands:
        method = getattr(repo, name)
        method(**params)
        snapshots.append(repo.to_graph())

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
            cmd = command_info[index]
            print(f"Шаг вперёд → {index + 1}/{len(snapshots)} | Команда: {cmd}")

    def on_left():
        nonlocal index
        if index > 0:
            index -= 1
            show_current()
            cmd = command_info[index]
            print(f"Шаг назад ← {index + 1}/{len(snapshots)} | Команда: {cmd}")

    plotter.add_key_event("Right", on_right)
    plotter.add_key_event("Left", on_left)

    print("Окно PyVista откроется. Управление историей:")
    print("  →  (Right Arrow)  — следующий шаг")
    print("  ←  (Left Arrow)   — предыдущий шаг")
    print("Закрой окно, чтобы завершить программу.")

    # сразу показываем, какая команда привела к начальному состоянию
    print(f"Начальное состояние: 1/{len(snapshots)} | Команда: {command_info[0]}")

    plotter.show()


if __name__ == "__main__":
    run_demo()