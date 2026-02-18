from src.models import Repo


def test_init_creates_main_branch_and_head():
    repo = Repo()
    repo.init()

    assert 'main' in repo.branches
    assert repo.head is not None
    assert repo.head.name == 'main'
    assert repo.head.commit is None  # после init нет ни одного коммита