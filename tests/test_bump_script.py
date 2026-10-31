"""Tests for the version validation against a real local git repo (no network)."""

import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from click import ClickException
from click.testing import CliRunner
from local_tools.bump_script import VersionEnum, _generate_version, cli, is_version_valid


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _make_repo(path: Path, tag: str | None) -> None:
    path.mkdir()
    _git(path, "init", "-b", "master")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "commit", "--allow-empty", "-m", "feat: first")
    if tag is not None:
        _git(path, "tag", tag)
    _git(path, "update-ref", "refs/remotes/origin/master", "HEAD")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Repo with tag 0.1.0 on master, which is also `origin/master`."""
    path = tmp_path / "repo"
    _make_repo(path, "0.1.0")
    monkeypatch.chdir(path)
    yield path


@pytest.mark.parametrize(
    "version",
    [
        "1.0.0",
        "0.2.0",
        "0.1.1",
        "0.1.0",  # equal to the latest tag is allowed outside of releases
        "0.2.0.dev20261101000000",  # PEP 440 form as written by `uv version`
        "0.2.0-dev20261101000000",
    ],
)
def test_valid_versions(repo: Path, version: str) -> None:
    assert is_version_valid(version)


@pytest.mark.parametrize(
    "version",
    [
        "0.0.5",
        "0.1.10",
        "0.2.1",
        "2.0.0",
        "0.1.0.dev1",  # dev of the tag itself is no successor
        "0.2.0rc1",
        "0.2.0.post1",
        "0.2.0+local",
        "1!0.2.0",
        "garbage",
    ],
)
def test_invalid_versions(repo: Path, version: str) -> None:
    assert not is_version_valid(version)


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0.dev20261101000000", "0.0.5"])
def test_release_rejects_tag_dev_and_non_successor(repo: Path, version: str) -> None:
    assert not is_version_valid(version, release=True)


@pytest.mark.parametrize("version", ["0.1.1", "0.2.0", "1.0.0"])
def test_release_accepts_real_successor(repo: Path, version: str) -> None:
    assert is_version_valid(version, release=True)


def test_generate_version_stages(repo: Path) -> None:
    assert _generate_version(VersionEnum.MAJOR, development_release=False) == "1.0.0"
    assert _generate_version(VersionEnum.MINOR, development_release=False) == "0.2.0"
    assert _generate_version(VersionEnum.PATCH, development_release=False) == "0.1.1"
    dev = _generate_version(VersionEnum.MINOR, development_release=True)
    assert dev.startswith("0.2.0.dev")
    assert is_version_valid(dev)


def test_ten_is_not_successor_of_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "zero"
    _make_repo(path, "0.0.0")
    monkeypatch.chdir(path)
    assert is_version_valid("0.0.1")
    assert not is_version_valid("0.0.10")


def test_missing_tag_gives_clean_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "untagged"
    _make_repo(path, None)
    monkeypatch.chdir(path)
    with pytest.raises(ClickException, match="latest tag"):
        is_version_valid("0.0.1")


def test_verify_version_command(repo: Path) -> None:
    runner = CliRunner()
    assert runner.invoke(cli, ["verify-version", "0.2.0"]).exit_code == 0
    assert runner.invoke(cli, ["verify-version", "0.1.0"]).exit_code == 0
    assert runner.invoke(cli, ["verify-version", "--release", "0.1.0"]).exit_code != 0
    assert runner.invoke(cli, ["verify-version", "0.0.5"]).exit_code != 0


def test_verify_version_without_tag_exits_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "untagged"
    _make_repo(path, None)
    monkeypatch.chdir(path)
    result = CliRunner().invoke(cli, ["verify-version", "0.0.1"])
    assert result.exit_code == 1
    assert "latest tag" in result.output
    assert not isinstance(result.exception, RuntimeError)
