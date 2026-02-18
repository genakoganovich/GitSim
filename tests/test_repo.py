from src.models import Repo
import pytest

def test_init_creates_main_branch_and_head():
    repo = Repo()
    repo.init()

    assert 'main' in repo.branches
    assert repo.head is not None
    assert repo.head.name == 'main'
    assert repo.head.commit is None


def test_first_commit_on_main_has_no_parents():
    repo = Repo()
    repo.init()

    commit = repo.commit("initial commit")

    assert repo.head is not None
    assert repo.head.commit is commit
    assert commit.message == "initial commit"
    assert commit.parents == []
    assert commit.hash in repo.commits
    assert repo.commits[commit.hash] is commit


def test_second_commit_has_previous_as_parent():
    repo = Repo()
    repo.init()

    c1 = repo.commit("first")
    c2 = repo.commit("second")

    assert repo.head.commit is c2
    assert c2.parents == [c1]

def test_branch_creates_new_branch_at_current_commit():
    repo = Repo()
    repo.init()
    c1 = repo.commit("first")

    dev = repo.branch("dev")

    assert "dev" in repo.branches
    assert dev is repo.branches["dev"]
    assert dev.commit is c1
    # HEAD остаётся на main
    assert repo.head.name == "main"
    assert repo.head.commit is c1


def test_branch_cannot_override_existing():
    repo = Repo()
    repo.init()

    # main уже существует после init
    with pytest.raises(ValueError):
        repo.branch("main")


def test_checkout_switches_head_to_branch():
    repo = Repo()
    repo.init()
    repo.commit("first")
    repo.branch("dev")

    repo.checkout("dev")

    assert repo.head is repo.branches["dev"]
    assert repo.head.name == "dev"


def test_checkout_unknown_branch_raises():
    repo = Repo()
    repo.init()

    with pytest.raises(ValueError):
        repo.checkout("feature")

def test_graph_after_init():
    repo = Repo()
    repo.init()

    nodes, edges = repo.to_graph()

    node_ids = {n.id for n in nodes}
    assert "HEAD" in node_ids
    assert "main" in node_ids
    # коммитов нет
    assert all(n.kind != "commit" for n in nodes)

    # одно ребро: HEAD -> main
    assert len(edges) == 1
    e = edges[0]
    assert e.source == "HEAD"
    assert e.target == "main"
    assert e.kind == "points_to"


def test_graph_with_commits_and_branch():
    repo = Repo()
    repo.init()
    c1 = repo.commit("first")
    c2 = repo.commit("second")
    repo.branch("dev")
    repo.checkout("dev")
    c3 = repo.commit("third on dev")

    nodes, edges = repo.to_graph()
    node_ids = {n.id for n in nodes}

    # узлы
    assert {"HEAD", "main", "dev", c1.hash, c2.hash, c3.hash}.issubset(node_ids)

    # HEAD указывает на dev
    head_edges = [e for e in edges if e.source == "HEAD"]
    assert len(head_edges) == 1
    assert head_edges[0].target == "dev"

    # ветка main -> c2, dev -> c3
    branch_edges = {(e.source, e.target) for e in edges if e.kind == "points_to" and e.source != "HEAD"}
    assert ("main", c2.hash) in branch_edges
    assert ("dev", c3.hash) in branch_edges

    # связи родительства коммитов
    parent_edges = {(e.source, e.target) for e in edges if e.kind == "parent"}
    assert (c2.hash, c1.hash) in parent_edges
    assert (c3.hash, c2.hash) in parent_edges


def test_merge_fast_forward():
    """Слияние, когда текущая ветка отстаёт (target — прямой потомок)."""
    repo = Repo()
    repo.init()

    # main: c1 -> c2
    c1 = repo.commit("c1")
    c2 = repo.commit("c2")

    # создаём ветку feature от c1 и делаем в ней коммит
    repo.branch("feature")
    repo.checkout("feature")
    c3 = repo.commit("c3 on feature")

    # возвращаемся в main и сливаем feature
    repo.checkout("main")
    repo.merge("feature")

    # main должен указывать на c3 (fast-forward)
    assert repo.head.commit.hash == c3.hash
    assert "main" in repo.branches
    assert repo.branches["main"].commit.hash == c3.hash


def test_merge_creates_merge_commit():
    """Слияние с расхождением истории (нужен merge-коммит)."""
    repo = Repo()
    repo.init()

    # main: c1 -> c2
    c1 = repo.commit("c1")
    c2 = repo.commit("c2")

    # feature ответвляется от c1, делает свой коммит
    repo.branch("feature")
    repo.checkout("feature")
    c3 = repo.commit("c3 on feature")

    # main делает ещё коммит после ответвления
    repo.checkout("main")
    c4 = repo.commit("c4 on main")

    # merge feature в main
    merge_commit = repo.merge("feature", message="Merge feature into main")

    # Проверяем merge-коммит
    assert merge_commit.parents == [c4, c3]
    assert repo.head.commit == merge_commit
    assert merge_commit.hash in repo.commits


def test_merge_without_commits_raises():
    """Попытка слить ветку, у которой нет ни одного коммита (commit is None)."""
    repo = Repo()
    repo.init()

    # создаём ветку, пока в репо нет коммитов -> ветка пустая
    repo.branch("empty")

    # теперь делаем коммит на main
    repo.commit("c1")

    # ветка "empty" по-прежнему указывает на None
    with pytest.raises(ValueError):
        repo.merge("empty")


def test_merge_into_empty_current_branch():
    """Слияние, когда текущая ветка пустая (не было коммитов)."""
    repo = Repo()
    repo.init()

    # создаём ветку с коммитом
    repo.branch("feature")
    repo.checkout("feature")
    c1 = repo.commit("c1 on feature")

    # main пустой, сливаем feature
    repo.checkout("main")
    repo.merge("feature")

    assert repo.head.commit == c1
    assert repo.branches["main"].commit == c1


def test_merge_same_branch_does_nothing():
    """Слияние ветки самой с собой."""
    repo = Repo()
    repo.init()
    c1 = repo.commit("c1")

    # main сливаем в main
    repo.merge("main")

    assert repo.head.commit == c1  # остался тот же коммит
    # Количество коммитов не увеличилось
    assert len(repo.commits) == 1

from typing import List

from src.app import GitSimApp
from src.models import GraphNode, GraphEdge


class FakeVisualizer:
    def __init__(self):
        self.calls: List[tuple[list[GraphNode], list[GraphEdge], bool]] = []

    def draw(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        show: bool = True,
    ) -> None:
        self.calls.append((nodes, edges, show))


def test_app_init_triggers_visualization():
    vis = FakeVisualizer()
    app = GitSimApp(visualizer=vis)

    app.init()

    assert len(vis.calls) == 1
    nodes, edges, show = vis.calls[0]
    ids = {n.id for n in nodes}
    assert "HEAD" in ids
    assert "main" in ids
    # должно быть хотя бы одно ребро HEAD -> main
    assert any(e.source == "HEAD" and e.target == "main" for e in edges)


def test_app_commit_updates_visualization():
    vis = FakeVisualizer()
    app = GitSimApp(visualizer=vis)

    app.init()
    vis.calls.clear()

    app.commit("first")

    assert len(vis.calls) == 1
    nodes, edges, _ = vis.calls[0]
    # должен появиться хотя бы один commit-узел
    assert any(n.kind == "commit" for n in nodes)


def test_app_branch_and_checkout_update_visualization():
    vis = FakeVisualizer()
    app = GitSimApp(visualizer=vis)

    app.init()
    app.commit("c1")
    vis.calls.clear()

    app.branch("dev")
    app.checkout("dev")

    # было два вызова визуализатора
    assert len(vis.calls) == 2
    # во втором вызове HEAD должен указывать на dev
    nodes, edges, _ = vis.calls[-1]
    assert any(e.source == "HEAD" and e.target == "dev" for e in edges)


def test_app_merge_updates_visualization():
    vis = FakeVisualizer()
    app = GitSimApp(visualizer=vis)

    app.init()
    c1 = app.commit("c1")
    app.branch("feature")
    app.checkout("feature")
    c2 = app.commit("c2 on feature")
    app.checkout("main")
    vis.calls.clear()

    app.merge("feature")

    assert len(vis.calls) == 1
    nodes, edges, _ = vis.calls[0]
    ids = {n.id for n in nodes}
    # хотя бы коммиты присутствуют
    assert c1.hash in ids
    assert c2.hash in ids