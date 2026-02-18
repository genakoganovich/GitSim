from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime


@dataclass
class Commit:
    hash: str
    message: str
    parent: Optional['Commit']
    timestamp: datetime


class Branch:
    def __init__(self, name: str, commit: Optional[Commit] = None):
        self.name = name
        self.commit = commit


class Repo:
    def __init__(self):
        # все коммиты по hash
        self.commits: Dict[str, Commit] = {}
        # все ветки по имени
        self.branches: Dict[str, Branch] = {}
        # текущая ветка (HEAD указывает на ветку)
        self.head: Optional[Branch] = None

    def init(self) -> None:
        """Инициализация репозитория с веткой main и HEAD -> main"""
        # если уже инициализирован – пока просто игнорируем
        if self.head is not None or self.branches:
            return

        main_branch = Branch(name="main", commit=None)
        self.branches["main"] = main_branch
        self.head = main_branch