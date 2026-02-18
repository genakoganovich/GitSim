from src.app import GitSimApp


def run_demo():
    """
    Демонстрация работы GitSimApp + PyVista.
    Окно визуализации одно, просто обновляется после каждой операции.
    """
    app = GitSimApp()

    # первый вызов с show=True откроет окно
    app.init(show=True)

    # дальше show можно не указывать — окно уже открыто, будет просто обновление
    app.commit("c1 on main")
    app.commit("c2 on main")

    app.branch("feature")
    app.checkout("feature")
    app.commit("c3 on feature")

    app.checkout("main")
    app.merge("feature", message="Merge feature into main")

    print("Демо завершено. Окно визуализации остаётся открытым.")


if __name__ == "__main__":
    run_demo()
