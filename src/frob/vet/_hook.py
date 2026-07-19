"""Hook-mode parsing and checks for `frob vet --hook '<command>'` (docs/modules/vet.md
HOOK MODE): parse an install-shaped shell command, then run the
pre-install-relevant checks (quarantine + typosquat) against the named
packages directly, since they are not in a lockfile yet.
"""

# frob:waive TEST005 reason="module line coverage 84.7%, debt T-0160"

from __future__ import annotations

import re
import shlex
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from frob.logging import get_logger
from frob.vet import _registry, _typosquat
from frob.vet._allow import load_vet_config
from frob.vet._models import HookVerdict, VetConfig

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "vet.db"

# (tool, subcommand-or-None) -> ecosystem. `None` subcommand means the tool
# itself is the install verb (npx).
_INSTALL_FORMS: dict[tuple[str, str | None], str] = {
    ("uv", "add"): "pypi",
    ("uv", "pip"): "pypi",  # requires a further "install" token, handled below
    ("pip", "install"): "pypi",
    ("pip3", "install"): "pypi",
    ("npm", "install"): "npm",
    ("npm", "i"): "npm",
    ("pnpm", "add"): "npm",
    ("yarn", "add"): "npm",
    ("npx", None): "npm",
    ("cargo", "add"): "cargo",
}

_PYPI_SPEC_RE = re.compile(r"^([A-Za-z0-9_.-]+)")


def _strip_pypi_version(token: str) -> tuple[str, str]:
    """`"requests==2.31.0"` -> `("requests", "2.31.0")`; unpinned -> `""` version."""
    match = _PYPI_SPEC_RE.match(token)
    if match is None:
        return token, ""
    name = match.group(1)
    rest = token[len(name) :]
    version_match = re.search(r"[0-9][A-Za-z0-9_.]*", rest)
    return name, (version_match.group(0) if version_match else "")


def _strip_npm_version(token: str) -> tuple[str, str]:
    """`"lodash@4.17.21"` / `"@scope/pkg@1.0.0"` -> `(name, version)`."""
    if token.startswith("@"):
        rest = token[1:]
        if "@" in rest:
            name_part, version = rest.split("@", 1)
            return f"@{name_part}", version
        return token, ""
    if "@" in token:
        name, version = token.split("@", 1)
        return name, version
    return token, ""


def _strip_cargo_version(token: str) -> tuple[str, str]:
    """`"serde@1.0"` -> `("serde", "1.0")`."""
    if "@" in token:
        name, version = token.split("@", 1)
        return name, version
    return token, ""


_Strip = Callable[[str], tuple[str, str]]
_INSTALL_TOOLS = ("uv", "pip", "pip3", "npm", "pnpm", "yarn", "cargo")


def _skip_env_assignments(tokens: list[str]) -> int:
    """Index of the first token past leading `FOO=bar` env assignments."""
    idx = 0
    while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[idx]):
        idx += 1
    return idx


def _parse_npx_target(
    tokens: list[str], idx: int
) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    """npx runs exactly one target package: the first non-flag token."""
    for tok in tokens[idx:]:
        if tok.startswith("-"):
            continue
        name, version = _strip_npm_version(tok)
        _log.info("vet: hook: parsed npx target %s@%s", name, version or "*")
        return "npm", ((name, version),)
    return None


def _strip_for_ecosystem(ecosystem: str) -> _Strip:
    """The name/version splitter for `ecosystem`."""
    if ecosystem == "pypi":
        return _strip_pypi_version
    if ecosystem == "npm":
        return _strip_npm_version
    return _strip_cargo_version


def _resolve_install_form(
    tool: str, tokens: list[str], idx: int
) -> tuple[str, _Strip, int] | None:
    """`(ecosystem, strip_fn, next_idx)` for a recognized subcommand, else None."""
    if idx >= len(tokens):
        return None
    sub = tokens[idx]
    idx += 1
    if tool == "uv" and sub == "pip":
        if idx >= len(tokens) or tokens[idx] != "install":
            return None
        return "pypi", _strip_pypi_version, idx + 1
    if (tool, sub) in _INSTALL_FORMS:
        ecosystem = _INSTALL_FORMS[(tool, sub)]
        return ecosystem, _strip_for_ecosystem(ecosystem), idx
    return None


def _collect_packages(pkg_tokens: list[str], strip: _Strip) -> list[tuple[str, str]]:
    """Split each non-flag token into `(name, version)`, dropping empty names."""
    packages: list[tuple[str, str]] = []
    for tok in pkg_tokens:
        if tok.startswith("-"):
            continue
        name, version = strip(tok)
        if not name:
            continue
        packages.append((name, version))
    return packages


# frob:doc docs/modules/vet.md#public-api
# frob:waive TEST005 reason="parse_hook_command 75.0% branch cover, debt T-0160"
def parse_hook_command(command: str) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    """Parse a shell command string for install-shaped invocations.
    Returns `(ecosystem, ((name, version_or_empty), ...))`, or `None` if the
    command is not a recognized package-install form."""
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        _log.warning("vet: hook: could not tokenize command: %s", exc)
        return None
    if not tokens:
        return None

    idx = _skip_env_assignments(tokens)
    if idx >= len(tokens):
        return None
    tool = Path(tokens[idx]).name  # strip any path prefix
    idx += 1

    if tool == "npx":
        return _parse_npx_target(tokens, idx)
    if tool not in _INSTALL_TOOLS:
        return None

    return _parse_install_tokens(tool, tokens, idx)


def _parse_install_tokens(
    tool: str, tokens: list[str], idx: int
) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    """Resolve `tool`'s install form and collect its package tokens."""
    resolved = _resolve_install_form(tool, tokens, idx)
    if resolved is None:
        return None
    ecosystem, strip, idx = resolved

    packages = _collect_packages(tokens[idx:], strip)
    if not packages:
        return None
    _log.info("vet: hook: parsed %s install of %s", ecosystem, packages)
    return ecosystem, tuple(packages)


def _unverified_lookup_verdict(
    ecosystem: str, name: str, lookup: _registry.RegistryResult
) -> HookVerdict | None:
    """An `unverified` `HookVerdict` if the publish-date lookup failed or
    found nothing, else None (caller proceeds to the age check)."""
    if not lookup.ok:
        msg = f"{name}: could not verify publish date"
        _log.warning("vet: hook: %s", msg)
        return HookVerdict(
            package=name,
            ecosystem=ecosystem,
            verdict="unverified",
            message=msg,
            blocked=False,
        )
    if lookup.published_at is None:
        msg = f"{name}: not found on registry"
        _log.warning("vet: hook: %s", msg)
        return HookVerdict(
            package=name,
            ecosystem=ecosystem,
            verdict="unverified",
            message=msg,
            blocked=False,
        )
    return None


def _quarantine_verdict(
    ecosystem: str, name: str, version: str, cfg: VetConfig, cache_path: Path
) -> HookVerdict:
    """Registry publish-date verdict: unverified / not-found / quarantine / ok."""
    lookup_version = version or _registry.LATEST_VERSION
    lookup = _registry.fetch_publish_date(
        ecosystem,
        name,
        lookup_version,
        cache_path=cache_path,
        base_url=cfg.registry_base_url,
    )
    unverified = _unverified_lookup_verdict(ecosystem, name, lookup)
    if unverified is not None:
        return unverified

    # Narrowing: _unverified_lookup_verdict already returned None-verdict for
    # a None published_at, so this is always set here.
    assert lookup.published_at is not None  # noqa: S101
    age_days = (datetime.now(UTC) - lookup.published_at.astimezone(UTC)).days
    return _age_based_verdict(ecosystem, name, lookup, age_days, cfg.quarantine_days)


def _age_based_verdict(
    ecosystem: str,
    name: str,
    lookup: _registry.RegistryResult,
    age_days: int,
    quarantine_days: int,
) -> HookVerdict:
    """quarantine vs ok, once a real publish age is known."""
    if age_days < quarantine_days:
        msg = (
            f"{name}@{lookup.resolved_version}: quarantined: published "
            f"{age_days} day(s) ago; add to [vet.allow] after review"
        )
        _log.warning("vet: hook: BLOCK %s", msg)
        return HookVerdict(
            package=name,
            ecosystem=ecosystem,
            verdict="quarantine",
            message=msg,
            blocked=True,
        )

    msg = f"{name}@{lookup.resolved_version}: ok (published {age_days} day(s) ago)"
    _log.info("vet: hook: %s", msg)
    return HookVerdict(
        package=name, ecosystem=ecosystem, verdict="ok", message=msg, blocked=False
    )


# frob:doc docs/modules/vet.md#public-api
# frob:waive TEST005 reason="check_package 62.5% branch cover, debt T-0160"
def check_package(
    ecosystem: str, name: str, version: str, *, root: Path
) -> HookVerdict:
    """Quarantine + typosquat check for one not-yet-installed package."""
    cfg = load_vet_config(root)
    cache_path = root / _CACHE_REL

    typosquat_of = _typosquat.find_typosquat(ecosystem, name)
    if typosquat_of is not None:
        msg = f"{name}: possible typosquat of {typosquat_of}"
        _log.warning("vet: hook: BLOCK %s", msg)
        return HookVerdict(
            package=name,
            ecosystem=ecosystem,
            verdict="typosquat",
            message=msg,
            blocked=True,
        )

    return _quarantine_verdict(ecosystem, name, version, cfg, cache_path)


__all__ = ["check_package", "parse_hook_command"]
