import subprocess
from pathlib import Path

import pytest
from tools.check_source_integrity import main

REAL_SOURCE = "def score(a, b):\n    return len(set(a) & set(b))\n" * 10


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, content: str, message: str = "change") -> None:
    (repo / "mod.py").write_text(content, encoding="utf-8")
    _git(repo, "add", "mod.py")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-m", message)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _git(tmp_path, "init", "-q")
    _commit(tmp_path, REAL_SOURCE, "init")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_normal_edit_passes(repo: Path) -> None:
    _commit(repo, REAL_SOURCE + "# more\n")
    assert main([]) == 0


@pytest.mark.parametrize("content", ["PLACEHOLDER\n", "PLACEHOLDER_WILL_REPLACE", "TODO"])
def test_placeholder_fails(repo: Path, content: str) -> None:
    _commit(repo, content)
    assert main([]) == 1


def test_large_shrink_fails(repo: Path) -> None:
    _commit(repo, REAL_SOURCE[:40])
    assert main([]) == 1


def test_trailer_allows_intentional_shrink_but_not_placeholder(repo: Path) -> None:
    _commit(repo, REAL_SOURCE[:40], "shrink\n\nSource-Integrity-Allow: mod.py")
    assert main([]) == 0
    _commit(repo, "PLACEHOLDER", "stub\n\nSource-Integrity-Allow: mod.py")
    assert main([]) == 1
