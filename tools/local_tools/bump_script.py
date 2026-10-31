"""Version bump and verification based on the latest git tag (ADR 0006)."""

import logging
import subprocess
from enum import StrEnum
from pathlib import Path

import click
from click import ClickException
from dunamai import Pattern, Style, Version
from packaging.version import InvalidVersion
from packaging.version import Version as PackagingVersion

_logger = logging.getLogger(__name__)

TAG_BRANCH = "origin/master"
_DEV_FORMAT = ".dev{timestamp}"


class VersionEnum(StrEnum):
    """Enum for versioning components."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"

    def to_index(self) -> int:
        """Return the index corresponding to the version component."""
        match self:
            case VersionEnum.MAJOR:
                return 0
            case VersionEnum.MINOR:
                return 1
            case VersionEnum.PATCH:
                return 2


def _latest_tag_version() -> Version:
    """Return the latest tag reachable from `TAG_BRANCH` as a version.

    Raises:
        ClickException: if there is no matching tag or the history is incomplete.
    """
    try:
        return Version.from_git(
            pattern=Pattern.DefaultUnprefixed,
            latest_tag=True,
            tag_branch=TAG_BRANCH,
            strict=True,
        )
    except (RuntimeError, ValueError) as error:
        raise ClickException(
            f"Cannot determine the latest tag on {TAG_BRANCH}: {error}. "
            "Run `git fetch --tags origin master` (full history needed) "
            "and make sure a tag like 0.0.0 exists on master."
        ) from error


def _generate_version(
    version: VersionEnum, development_release: bool, latest: Version | None = None
) -> str:
    """Generate the next version from the latest tag reachable from `TAG_BRANCH`.

    The major, minor or patch number of the latest tag is incremented by 1. For a
    development release, a PEP 440 `.dev<timestamp>` suffix is added, which is the
    form `uv version` stores. Basing the version on the latest tag makes the result
    reproducible. Pass `latest` to reuse an already determined tag version.
    """
    version_format = "{base}"
    if development_release:
        version_format += _DEV_FORMAT

    base = latest if latest is not None else _latest_tag_version()
    return base.bump(index=version.to_index()).serialize(style=Style.Pep440, format=version_format)


def is_version_valid(current_version: str, release: bool = False) -> bool:
    """Check that `current_version` is acceptable relative to the latest tag.

    Valid are the next major, minor or patch version, optionally as PEP 440 development
    release (`X.Y.Z.dev<suffix>`), and, unless `release` is set, the latest tag itself.
    A release requires a real successor: no dev version and not equal to the tag.
    The base is compared exactly, so `0.0.10` is not a successor of `0.0.0`. Other
    pre-, post- or local markers (`rc1`, `.post1`, `+x`) are rejected.
    """
    latest_tag = _latest_tag_version()  # one git lookup for all candidates
    successors = [
        _generate_version(version, development_release=False, latest=latest_tag)
        for version in VersionEnum
    ]
    latest = latest_tag.serialize(style=Style.Pep440, format="{base}")
    possibilities = successors if release else [latest, *successors]

    try:
        parsed = PackagingVersion(current_version)
    except InvalidVersion:
        is_valid = False
    else:
        plain = parsed.pre is None and parsed.post is None and parsed.local is None
        is_dev = parsed.dev is not None
        base = parsed.base_version
        is_valid = (
            plain
            and parsed.epoch == 0
            and base in possibilities
            and not (is_dev and (release or base == latest))
        )

    if not is_valid:
        _logger.error(
            "Invalid version: %s\nPossibilities: %s. Please execute the bump script.",
            current_version,
            possibilities,
        )

    return is_valid


def _fetch_tags() -> None:
    """Refresh `origin/master` and the tags, warn and continue if that fails."""
    try:
        result = subprocess.run(
            ["git", "fetch", "--tags", "origin", "master"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        click.echo(f"Warning: git fetch failed ({error}), using local tags.", err=True)
        return
    if result.returncode != 0:
        click.echo(
            f"Warning: git fetch failed ({result.stderr.strip()}), using local tags.",
            err=True,
        )


@click.group("cli")
def cli() -> None:
    """Version tooling."""


@cli.command("version")
@click.argument("version", type=click.Choice(list(VersionEnum)), default=VersionEnum.PATCH)
@click.option("-d", "--devrelease", type=bool, is_flag=True, default=False)
def main(version: VersionEnum, devrelease: bool) -> None:
    """Set the next app version.

    Args:
        version: increment the major, minor, or patch number.
        devrelease: if True, the version will have a ".dev..." suffix
    """
    root = Path()
    project_file = root / "pyproject.toml"
    if not project_file.is_file():
        raise ClickException(
            f"pyproject.toml not found in {root.absolute()}. "
            "Execute this script from the project root."
        )

    _fetch_tags()
    version_string = _generate_version(version=version, development_release=devrelease)

    subprocess.run(["uv", "version", version_string], check=True)
    subprocess.run(["uv", "sync", "--all-groups", "--all-packages"], check=True)


@cli.command("verify-version")
@click.argument("current_version", type=str)
@click.option(
    "--release",
    is_flag=True,
    default=False,
    help="Require a real successor of the latest tag (no dev version, not equal to the tag).",
)
def verify_version(current_version: str, release: bool) -> None:
    """Verify that the provided version is valid, based on the latest git tag.

    Args:
        current_version: The application's current version
        release: require a real successor instead of also allowing the latest tag
    """
    if is_version_valid(current_version=current_version, release=release):
        click.echo(f"Version valid: {current_version}")
    else:
        raise ClickException("Invalid Version")


if __name__ == "__main__":
    cli()
