"""WEBSEC318-325: CI/supply-chain hardening (docs/modules/webapp-websec-
supply-chain.md, T-5331, the T-5140 web-app epic's CI/supply-chain leaf).

Same posture as `_websec_headers_log.py`/`_websec_bounds.py`: framework-
gated (short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
reports no web framework, T-5302's own contract), and folded into
`frob.gates._taint_gate.taint_gate` via the `websec_findings(root,
frameworks)` pkgutil-discovery hook (T-5308) rather than a second gate
registration.

Unlike the other WEBSEC families this leaf reads workflow YAML,
Dockerfiles and dependency manifests/lockfiles rather than application
source -- so its scan is TEXT-REGEX plus a best-effort `yaml.safe_load`
parse of `.github/workflows/*.y*ml` (mirroring `frob.vet._supplychain`'s
own `yaml.safe_load`-over-line-regex posture for the one rule, WEBSEC319,
that needs real YAML structure), not an AST walk.

EIGHT RULE IDS (T-5301's reserved `WEBSEC318`-`WEBSEC325` block):

- WEBSEC318: CI log secret exposure -- a workflow step echoes/prints a
  `${{ secrets.* }}` expansion directly, with no `::add-mask::` guard
  first (un-masked env echo, CWE-532-shaped).
- WEBSEC319: `pull_request_target` misuse -- a workflow triggered on
  `pull_request_target` that both checks out the fork's PR head commit
  (`actions/checkout` with a `ref:` derived from
  `github.event.pull_request.head`) AND references `secrets.` anywhere
  in the same workflow (the classic secret-exfiltration-via-fork-PR
  shape).
- WEBSEC320: a Dockerfile with no `USER` instruction before its final
  `ENTRYPOINT`/`CMD` -- the container runs as root.
- WEBSEC321: a Dockerfile `FROM` line pinned to the `:latest` tag (or no
  tag at all, which resolves to `:latest`) instead of a fixed version.
- WEBSEC322: a dependency manifest (`package.json`/`pyproject.toml`/
  `Gemfile`/`go.mod`/`Cargo.toml`) present with no matching lockfile.
- WEBSEC323: a lockfile present alongside its manifest, but at least one
  manifest-declared dependency name is not found anywhere in the
  lockfile text -- best-effort drift detection, not a real dependency
  resolver (same disclosed-gap posture every text-regex WEBSEC family
  carries).
- WEBSEC324: typosquat edit-distance -- a manifest dependency name
  within Levenshtein distance 1-2 of a bundled popular-package name for
  that ecosystem, but not an exact match -- a small, best-effort,
  NOT-exhaustive top-package list (see `_POPULAR_PACKAGES` below), the
  same "best-effort not exhaustive" posture the ticket body specifies.
- WEBSEC325: a GitHub Actions workflow granting `permissions: write-all`
  at the workflow level -- overly broad `GITHUB_TOKEN` scope (CWE-250-
  adjacent, OWASP CI/CD Security Top 10 CICD-SEC-2-shaped).

WEBSEC319/318/325's sibling check "a `uses:` ref pinned to a mutable tag
rather than a 40-hex commit SHA" is deliberately NOT implemented here --
that is T-3923's `frob vet` scope (extending the already-landed VET009
SHA-pin rule in `frob.vet._supplychain._unpinned_ci_action_violations`),
a different subsystem with its own established check; this leaf
cross-references it rather than duplicating it.

Each is WARN-tier at first turn-on, the T-0688/T-0973 promotion posture
every WEBSEC family in this epic follows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

from frob.findings import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind, detect_frameworks

_log = get_logger(__name__)

__all__ = [
    "WebsecSupplyChainFinding",
    "websec_findings",
    "websec_supply_chain_findings",
]


# frob:doc docs/modules/webapp-websec-supply-chain.md#public-api
@dataclass(frozen=True)
class WebsecSupplyChainFinding:
    """One WEBSEC318-325 finding: a CI/supply-chain hardening gap in a
    workflow file, Dockerfile, or dependency manifest/lockfile pair.

    frob:ticket T-5331
    """

    rule: str
    file: str
    line: int
    message: str


#: Small, deliberately NOT-exhaustive per-ecosystem popular-package list
#: WEBSEC324 diffs newly-seen manifest dependency names against --
#: bundled, best-effort, the ticket body's own stated posture, not a
#: live registry lookup.
_POPULAR_PACKAGES: dict[str, frozenset[str]] = {
    "npm": frozenset(
        {
            "react",
            "express",
            "lodash",
            "axios",
            "next",
            "vue",
            "webpack",
            "chalk",
            "request",
            "commander",
        }
    ),
    "pypi": frozenset(
        {
            "requests",
            "numpy",
            "flask",
            "django",
            "pandas",
            "boto3",
            "pytest",
            "pyyaml",
            "urllib3",
            "click",
        }
    ),
}

_SECRET_ECHO_RE = re.compile(
    r"(?:echo|print(?:f|ln)?|Write-Host)\b[^\n]*\$\{\{\s*secrets\.", re.IGNORECASE
)

_CHECKOUT_FORK_HEAD_RE = re.compile(
    r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head"
)

_DOCKER_USER_RE = re.compile(r"^\s*USER\s+\S+", re.IGNORECASE | re.MULTILINE)
_DOCKER_ENTRYPOINT_CMD_RE = re.compile(
    r"^\s*(ENTRYPOINT|CMD)\s+", re.IGNORECASE | re.MULTILINE
)
_DOCKER_FROM_RE = re.compile(
    r"^\s*FROM\s+([^\s]+?)(?:\s+AS\s+\S+)?\s*$", re.IGNORECASE | re.MULTILINE
)

_PERMISSIONS_WRITE_ALL_RE = re.compile(
    r"^\s*permissions:\s*write-all\s*$", re.MULTILINE
)

#: manifest filename -> (ecosystem key into `_POPULAR_PACKAGES`, tuple of
#: acceptable lockfile filenames).
_MANIFEST_LOCKFILES: dict[str, tuple[str, tuple[str, ...]]] = {
    "package.json": ("npm", ("package-lock.json", "yarn.lock", "pnpm-lock.yaml")),
    "pyproject.toml": ("pypi", ("uv.lock", "poetry.lock")),
    "Gemfile": ("gem", ("Gemfile.lock",)),
    "go.mod": ("go", ("go.sum",)),
    "Cargo.toml": ("cargo", ("Cargo.lock",)),
}

_NAME_TOKEN_RE = re.compile(r'"([A-Za-z0-9@_./-]{2,})"\s*:')


def _tracked_files(root: Path) -> tuple[str, ...]:
    """`git ls-files` under `root`, root-relative POSIX paths, `()` on any
    git failure -- mirrors `_websec_headers_log._tracked_files`'s own
    tracked-file-scan shape.

    frob:ticket T-5331
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_supply_chain: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_supply_chain: git ls-files exited %d", result.returncode)
        return ()
    return tuple(line for line in result.stdout.splitlines() if line.strip())


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5331
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5331
    """
    return text.count("\n", 0, offset) + 1


def _levenshtein(left: str, right: str) -> int:
    """Plain iterative Levenshtein edit distance -- no third-party
    dependency for WEBSEC324's small best-effort diff.

    frob:ticket T-5331
    """
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, lchar in enumerate(left, start=1):
        current = [i] + [0] * len(right)
        for j, rchar in enumerate(right, start=1):
            cost = 0 if lchar == rchar else 1
            current[j] = min(
                previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost
            )
        previous = current
    return previous[-1]


def _secret_echo_findings(text: str, rel_path: str) -> list[WebsecSupplyChainFinding]:
    """WEBSEC318: CI log secret exposure.

    frob:ticket T-5331
    """
    findings: list[WebsecSupplyChainFinding] = []
    for match in _SECRET_ECHO_RE.finditer(text):
        line = _line_of(text, match.start())
        findings.append(
            WebsecSupplyChainFinding(
                rule="WEBSEC318",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC318: {rel_path}:{line} a workflow step echoes "
                    f"a secrets.* expansion directly -- it will be "
                    f"printed to CI logs un-masked (CWE-532). Assign the "
                    f"secret to a masked env var first, or "
                    f'`frob:waive WEBSEC318 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _pull_request_target_findings(
    doc: object, text: str, rel_path: str
) -> list[WebsecSupplyChainFinding]:
    """WEBSEC319: `pull_request_target` combined with a fork-head checkout
    and secrets use.

    frob:ticket T-5331
    """
    if not isinstance(doc, dict):
        return []
    # PyYAML (YAML 1.1) parses a bare `on:` key as the boolean True, not
    # the string "on" -- doc's key type is not statically `str`, so index
    # via a plain object-keyed lookup rather than `dict.get` (ty/mypy
    # both otherwise infer a str-only key type from the "on" literal).
    doc_any = cast("dict[object, object]", doc)
    trigger = doc_any.get("on") or doc_any.get(True)
    triggers = trigger if isinstance(trigger, (dict, list)) else [trigger]
    trigger_names = set(triggers) if isinstance(triggers, list) else set(triggers)
    if "pull_request_target" not in trigger_names:
        return []
    checkout_match = _CHECKOUT_FORK_HEAD_RE.search(text)
    if checkout_match is None:
        return []
    if "secrets." not in text:
        return []
    line = _line_of(text, checkout_match.start())
    return [
        WebsecSupplyChainFinding(
            rule="WEBSEC319",
            file=rel_path,
            line=line,
            message=(
                f"WEBSEC319: {rel_path}:{line} a pull_request_target "
                f"workflow checks out the fork PR's head commit and also "
                f"references secrets. -- an attacker-controlled PR can "
                f"exfiltrate the secret. Drop the fork-head checkout or "
                f'the secrets use, or `frob:waive WEBSEC319 reason="..."` '
                f"with a real justification"
            ),
        )
    ]


def _permissions_write_all_findings(
    text: str, rel_path: str
) -> list[WebsecSupplyChainFinding]:
    """WEBSEC325: workflow-level `permissions: write-all`.

    frob:ticket T-5331
    """
    findings: list[WebsecSupplyChainFinding] = []
    for match in _PERMISSIONS_WRITE_ALL_RE.finditer(text):
        line = _line_of(text, match.start())
        findings.append(
            WebsecSupplyChainFinding(
                rule="WEBSEC325",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC325: {rel_path}:{line} the workflow grants "
                    f"permissions: write-all -- an overly broad "
                    f"GITHUB_TOKEN scope (CICD-SEC-2-shaped). Enumerate "
                    f"the minimum scopes needed, or `frob:waive WEBSEC325 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _workflow_findings(path: Path, root: Path) -> list[WebsecSupplyChainFinding]:
    """Every WEBSEC318/319/325 finding in one `.github/workflows/*.y*ml`
    file.

    frob:ticket T-5331
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    findings: list[WebsecSupplyChainFinding] = []
    findings.extend(_secret_echo_findings(text, rel_path))
    findings.extend(_permissions_write_all_findings(text, rel_path))
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        _log.warning("websec_supply_chain: %s is not valid YAML: %s", path, exc)
        doc = None
    findings.extend(_pull_request_target_findings(doc, text, rel_path))
    return findings


def _dockerfile_root_findings(
    text: str, rel_path: str
) -> list[WebsecSupplyChainFinding]:
    """WEBSEC320: no `USER` before the final `ENTRYPOINT`/`CMD`.

    frob:ticket T-5331
    """
    entrypoints = list(_DOCKER_ENTRYPOINT_CMD_RE.finditer(text))
    if not entrypoints:
        return []
    last_entrypoint = entrypoints[-1]
    users = list(_DOCKER_USER_RE.finditer(text))
    if any(u.start() < last_entrypoint.start() for u in users):
        return []
    line = _line_of(text, last_entrypoint.start())
    return [
        WebsecSupplyChainFinding(
            rule="WEBSEC320",
            file=rel_path,
            line=line,
            message=(
                f"WEBSEC320: {rel_path}:{line} no USER instruction "
                f"precedes the final ENTRYPOINT/CMD -- the container "
                f"runs as root. Add a USER instruction before the "
                f'entrypoint, or `frob:waive WEBSEC320 reason="..."` '
                f"with a real justification"
            ),
        )
    ]


def _dockerfile_latest_tag_findings(
    text: str, rel_path: str
) -> list[WebsecSupplyChainFinding]:
    """WEBSEC321: a `FROM` line pinned to `:latest` or no tag at all.

    frob:ticket T-5331
    """
    findings: list[WebsecSupplyChainFinding] = []
    for match in _DOCKER_FROM_RE.finditer(text):
        image = match.group(1)
        if image.lower() == "scratch":
            continue
        tag = image.rpartition(":")[2] if ":" in image else ""
        if tag and tag != "latest":
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecSupplyChainFinding(
                rule="WEBSEC321",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC321: {rel_path}:{line} FROM {image} is "
                    f"pinned to :latest (or no tag at all) -- non-"
                    f"reproducible, silently-drifting base image. Pin a "
                    f"fixed version tag, or `frob:waive WEBSEC321 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _dockerfile_findings(path: Path, root: Path) -> list[WebsecSupplyChainFinding]:
    """Every WEBSEC320/321 finding in one Dockerfile.

    frob:ticket T-5331
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    findings: list[WebsecSupplyChainFinding] = []
    findings.extend(_dockerfile_root_findings(text, rel_path))
    findings.extend(_dockerfile_latest_tag_findings(text, rel_path))
    return findings


def _manifest_dependency_names(text: str) -> frozenset[str]:
    """Best-effort dependency-name extraction from a `package.json`-shaped
    quoted-key manifest -- a text scan, not a real JSON/TOML parse
    (WEBSEC322/323/324 only need the name tokens).

    frob:ticket T-5331
    """
    return frozenset(
        name
        for name in _NAME_TOKEN_RE.findall(text)
        if name not in {"name", "version", "scripts", "dependencies", "devDependencies"}
    )


def _lockfile_candidate_rel(manifest_dir_rel: str, lockfile_name: str) -> str:
    """Root-relative lockfile path for `lockfile_name` sitting next to a
    manifest whose own root-relative parent dir is `manifest_dir_rel`.

    frob:ticket T-5331
    """
    if manifest_dir_rel == ".":
        return lockfile_name
    return f"{manifest_dir_rel}/{lockfile_name}"


def _find_tracked_lockfile(
    tracked: frozenset[str], manifest_dir_rel: str, lockfile_names: tuple[str, ...]
) -> str | None:
    """The first of `lockfile_names` tracked next to the manifest, or
    `None` if none of them are tracked.

    frob:ticket T-5331
    """
    for lockfile_name in lockfile_names:
        candidate_rel = _lockfile_candidate_rel(manifest_dir_rel, lockfile_name)
        if candidate_rel in tracked:
            return candidate_rel
    return None


def _missing_lockfile_finding(
    rel: str, lockfile_names: tuple[str, ...]
) -> WebsecSupplyChainFinding:
    """WEBSEC322: manifest present with no matching lockfile.

    frob:ticket T-5331
    """
    return WebsecSupplyChainFinding(
        rule="WEBSEC322",
        file=rel,
        line=1,
        message=(
            f"WEBSEC322: {rel}:1 a dependency manifest is tracked with "
            f"no matching lockfile ({'/'.join(lockfile_names)}) -- "
            f"unpinned transitive dependency resolution. Commit a "
            f'lockfile, or `frob:waive WEBSEC322 reason="..."` with a '
            f"real justification"
        ),
    )


def _lockfile_drift_finding(rel: str, missing: list[str]) -> WebsecSupplyChainFinding:
    """WEBSEC323: lockfile present but at least one manifest dependency is
    missing from it (best-effort drift check).

    frob:ticket T-5331
    """
    return WebsecSupplyChainFinding(
        rule="WEBSEC323",
        file=rel,
        line=1,
        message=(
            f"WEBSEC323: {rel}:1 manifest dependenc"
            f"{'y' if len(missing) == 1 else 'ies'} "
            f"{', '.join(missing)} not found in the lockfile -- possible "
            f"lockfile drift (best-effort, not a real resolver check). "
            f"Regenerate the lockfile, or "
            f'`frob:waive WEBSEC323 reason="..."` with a real '
            f"justification"
        ),
    )


def _lockfile_findings_for_manifest(
    rel: str, tracked: frozenset[str], root: Path
) -> list[WebsecSupplyChainFinding]:
    """Every WEBSEC322/323 finding for one manifest `rel` already known to
    have a recognized lockfile spec.

    frob:ticket T-5331
    """
    manifest_name = Path(rel).name
    _ecosystem, lockfile_names = _MANIFEST_LOCKFILES[manifest_name]
    manifest_dir_rel = Path(rel).parent.as_posix()
    lockfile_rel = _find_tracked_lockfile(tracked, manifest_dir_rel, lockfile_names)
    if lockfile_rel is None:
        return [_missing_lockfile_finding(rel, lockfile_names)]
    manifest_names = _manifest_dependency_names(_read_text(root / rel))
    lockfile_text = _read_text(root / lockfile_rel)
    missing = sorted(name for name in manifest_names if name not in lockfile_text)
    if not missing:
        return []
    return [_lockfile_drift_finding(rel, missing)]


def _lockfile_findings(
    tracked: frozenset[str], root: Path
) -> list[WebsecSupplyChainFinding]:
    """WEBSEC322: manifest present with no matching lockfile. WEBSEC323:
    lockfile present but at least one manifest dependency is missing from
    it (best-effort drift check).

    frob:ticket T-5331
    """
    findings: list[WebsecSupplyChainFinding] = []
    for rel in sorted(tracked):
        if Path(rel).name not in _MANIFEST_LOCKFILES:
            continue
        findings.extend(_lockfile_findings_for_manifest(rel, tracked, root))
    return findings


def _typosquat_findings(
    tracked: frozenset[str], root: Path
) -> list[WebsecSupplyChainFinding]:
    """WEBSEC324: a manifest dependency name within edit-distance 1-2 of a
    bundled popular-package name, but not an exact match.

    frob:ticket T-5331
    """
    findings: list[WebsecSupplyChainFinding] = []
    for rel in sorted(tracked):
        manifest_name = Path(rel).name
        spec = _MANIFEST_LOCKFILES.get(manifest_name)
        if spec is None:
            continue
        ecosystem, _lockfile_names = spec
        popular = _POPULAR_PACKAGES.get(ecosystem)
        if not popular:
            continue
        manifest_names = _manifest_dependency_names(_read_text(root / rel))
        for name in sorted(manifest_names):
            if name in popular:
                continue
            for known in popular:
                distance = _levenshtein(name.lower(), known.lower())
                if 0 < distance <= 2:
                    findings.append(
                        WebsecSupplyChainFinding(
                            rule="WEBSEC324",
                            file=rel,
                            line=1,
                            message=(
                                f"WEBSEC324: {rel}:1 dependency {name!r} "
                                f"is edit-distance {distance} from the "
                                f"popular package {known!r} -- possible "
                                f"typosquat (best-effort, bundled top-"
                                f"package list, not exhaustive). Verify "
                                f"the package name, or "
                                f'`frob:waive WEBSEC324 reason="..."` '
                                f"with a real justification"
                            ),
                        )
                    )
                    break
    return findings


# frob:doc docs/modules/webapp-websec-supply-chain.md#public-api
# frob:ticket T-5331
def websec_supply_chain_findings(root: Path) -> tuple[WebsecSupplyChainFinding, ...]:
    """WEBSEC318-325: every CI/supply-chain hardening finding under
    `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract, the same
    posture every WEBSEC family in this epic follows).

    frob:ticket T-5331
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug(
            "websec_supply_chain: no framework detected at %s, skipping scan", root
        )
        return ()

    tracked = frozenset(_tracked_files(root))
    findings: list[WebsecSupplyChainFinding] = []
    for rel in sorted(tracked):
        if rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml")):
            findings.extend(_workflow_findings(root / rel, root))
        elif Path(rel).name.startswith("Dockerfile"):
            findings.extend(_dockerfile_findings(root / rel, root))
    findings.extend(_lockfile_findings(tracked, root))
    findings.extend(_typosquat_findings(tracked, root))

    _log.info("websec_supply_chain: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-supply-chain.md#public-api
# frob:ticket T-5331
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """T-5308's `taint_gate` module-discovery hook: every
    `frob.webapp._websec_*` module exposing a module-level
    `websec_findings(root, frameworks) -> tuple[Violation, ...]` is
    auto-discovered and folded into `taint_gate`'s scan, so this new
    WEBSEC family never needs its own `gates/__init__.py`/`_taint_gate.py`
    edit. `frameworks` is the caller's own already-computed
    `detect_frameworks(root)` result (avoids a second detect call per
    discovered module) -- an empty set short-circuits to `()` exactly
    like `websec_supply_chain_findings`'s own direct-call contract.

    frob:ticket T-5331
    """
    if not frameworks:
        _log.debug(
            "websec_supply_chain: no framework detected at %s, skipping scan (hook)",
            root,
        )
        return ()
    return tuple(
        Violation(
            rule=finding.rule,
            severity=Severity.WARN,
            file=finding.file,
            line=finding.line,
            message=finding.message,
        )
        for finding in websec_supply_chain_findings(root)
    )
