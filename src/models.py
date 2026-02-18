from dataclasses import dataclass
from typing import Optional, Dict, List, Literal, Tuple
from datetime import datetime


@dataclass
class Commit:
    hash: str
    message: str
    parents: List['Commit']
    timestamp: datetime


class Branch:
    def __init__(self, name: str, commit: Optional[Commit] = None):
        self.name = name
        self.commit = commit


@dataclass
class GraphNode:
    id: str  # уникальный ID узла (hash коммита, имя ветки, "HEAD")
    kind: Literal["commit", "branch", "head"]
    label: str  # то, что будем показывать в визе (обычно = id)


@dataclass
class GraphEdge:
    source: str  # id узла-источника
    target: str  # id узла-назначения
    kind: Literal["parent", "points_to"]  # parent: связи коммитов; points_to: HEAD/ветки



class Repo:
    def __init__(self):
        self.commits: Dict[str, Commit] = {}
        self.branches: Dict[str, Branch] = {}
        self.head: Optional[Branch] = None
        self._next_id: int = 1  # простой счётчик для hash'ей

    def init(self) -> None:
        if self.head is not None or self.branches:
            return

        main_branch = Branch(name="main", commit=None)
        self.branches["main"] = main_branch
        self.head = main_branch

    def commit(self, message: str) -> Commit:
        """Создать новый коммит в текущей ветке и передвинуть HEAD."""
        if self.head is None:
            raise RuntimeError("Repo is not initialized")

        parent_commit = self.head.commit
        parents = [parent_commit] if parent_commit is not None else []

        commit_hash = str(self._next_id)
        self._next_id += 1

        new_commit = Commit(
            hash=commit_hash,
            message=message,
            parents=parents,
            timestamp=datetime.now(),
        )
        self.commits[commit_hash] = new_commit
        self.head.commit = new_commit

        return new_commit

    def branch(self, name: str) -> Branch:
        """Создать новую ветку от текущего коммита HEAD (не переключаясь на неё)."""
        if self.head is None:
            raise RuntimeError("Repo is not initialized")

        if name in self.branches:
            raise ValueError(f"Branch '{name}' already exists")

        new_branch = Branch(name=name, commit=self.head.commit)
        self.branches[name] = new_branch
        return new_branch

    def checkout(self, name: str) -> None:
        """Переключить HEAD на указанную ветку."""
        if name not in self.branches:
            raise ValueError(f"Branch '{name}' does not exist")

        self.head = self.branches[name]

    def to_graph(self) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Построить граф: узлы (HEAD, ветки, коммиты) и рёбра.
        parent: коммит -> родительский коммит
        points_to: HEAD -> ветка, ветка -> коммит
        """
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []

        # Узел HEAD
        if self.head is not None:
            nodes.append(GraphNode(id="HEAD", kind="head", label="HEAD"))
            edges.append(GraphEdge(source="HEAD", target=self.head.name, kind="points_to"))

        # Узлы веток
        for name, branch in self.branches.items():
            nodes.append(GraphNode(id=name, kind="branch", label=name))
            if branch.commit is not None:
                edges.append(
                    GraphEdge(source=name, target=branch.commit.hash, kind="points_to")
                )

        # Узлы коммитов и связи родительства
        for commit in self.commits.values():
            nodes.append(GraphNode(id=commit.hash, kind="commit", label=commit.hash))
            for parent in commit.parents:
                edges.append(
                    GraphEdge(source=commit.hash, target=parent.hash, kind="parent")
                )

        return nodes, edges

    def merge(self, branch_name: str, message: str = "Merge commit") -> Commit:
        """Слить указанную ветку в текущую (HEAD)."""
        if self.head is None:
            raise RuntimeError("Repo is not initialized")

        if branch_name not in self.branches:
            raise ValueError(f"Branch '{branch_name}' does not exist")

        target_branch = self.branches[branch_name]
        current_commit = self.head.commit
        target_commit = target_branch.commit

        if target_commit is None:
            raise ValueError(f"Cannot merge: branch '{branch_name}' has no commits")

        # Если текущая ветка пустая — fast-forward без создания коммита
        if current_commit is None:
            self.head.commit = target_commit
            return target_commit

        # Если уже на том же коммите — ничего не делаем
        if current_commit.hash == target_commit.hash:
            return current_commit

        # Проверяем fast-forward: target_commit является потомком current_commit?
        # Простой способ: проходим по родителям target_commit в глубину/ширину
        def is_ancestor(commit: Commit, potential_ancestor: Commit) -> bool:
            # BFS по графу коммитов
            visited = set()
            queue = [commit]
            while queue:
                c = queue.pop()
                if c.hash in visited:
                    continue
                visited.add(c.hash)
                if c.hash == potential_ancestor.hash:
                    return True
                queue.extend(c.parents)
            return False

        # Если current_commit является предком target_commit — fast-forward
        if is_ancestor(target_commit, current_commit):
            self.head.commit = target_commit
            return target_commit

        # Иначе создаём merge-коммит с двумя родителями
        merge_commit_hash = str(self._next_id)
        self._next_id += 1

        merge_commit = Commit(
            hash=merge_commit_hash,
            message=message,
            parents=[current_commit, target_commit],
            timestamp=datetime.now(),
        )

        self.commits[merge_commit_hash] = merge_commit
        self.head.commit = merge_commit

        return merge_commit