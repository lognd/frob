"""DEPLOY001: committed `deploy/{install,status,uninstall}.sh` must match
regeneration from the CURRENT design model (T-0257, the tmLanguage
drift-lock precedent -- see `docs/guides/agent-playbook.md` -- applied to
deploy scripts).

Opt-in, same posture `frob.gates.sys_gate`/`decisions_gate` already use:
a repo with no `deploy/` directory sees nothing. When `deploy/` exists,
every one of the three generated filenames that is ALSO present on disk
must be byte-identical to what `frob.deploy.generate_all` would produce
right now from the repo's `.strata` design models -- a mismatch (stale
hand-edit, or a design change the operator forgot to regenerate for)
fails closed with the exact filename named.

This module is deliberately NOT wired into `frob.gates`'s pluggable job
table (`src/frob/gates/**` is out of this ticket's scope) -- instead
`frob.app.check_runner` (in scope) calls `deploy_drift_violations`
directly and folds the result into `frob check`'s `CheckResult`, the same
"extra stage beyond the gate table" shape `_dispatch_check_python`
already uses for ruff/ty/arch/cycle/dup/bind/exports.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

if TYPE_CHECKING:
    from frob.strata import KernelModel

_log = get_logger(__name__)

#: The exact filenames `generate_all` produces -- the ONE list this
#: module and `frob.deploy.generate_all` must agree on (no duplication).
_GENERATED_FILENAMES = ("install.sh", "status.sh", "uninstall.sh")


# frob:doc docs/strata/host.md#the-deploy-generator
class DeployDriftViolation(BaseModel):
    """One `deploy/<file>` that no longer matches regeneration from the
    current model (DEPLOY001) -- reported with the file so the fix
    (`frob deploy generate`) is unambiguous about what to re-run."""

    model_config = ConfigDict(frozen=True)

    file: str
    message: str


def _design_dir(root: Path) -> str:
    """`[strata].design_dir` from `frob.toml`, defaulting like every other
    strata-consuming CLI entry point (duplicated two-line read, same
    precedent `frob.app.sys_runner._design_dir` and `frob.gates._design_
    dir` already set independently -- a two-line frob.toml read is not
    worth a cross-package import, per those modules' own docstrings)."""
    import tomllib

    from frob.strata import DEFAULT_DESIGN_DIR

    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return DEFAULT_DESIGN_DIR
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("deploy drift: frob.toml unreadable: %s", exc)
        return DEFAULT_DESIGN_DIR
    return data.get("strata", {}).get("design_dir", DEFAULT_DESIGN_DIR)


def _load_current_model(root: Path) -> "KernelModel | None":
    """Load and merge every `.strata` design file under the repo's design
    dir into one `KernelModel`, or `None` (with a logged error) if no
    design model loads at all. Shared by DEPLOY001 (`_current_model_
    output` below) and DEPLOY002/DEPLOY003 (`_conform.py`) so the design-
    dir read + merge happen in exactly ONE place, never duplicated
    per-gate."""
    from frob.strata import load_design_ids
    from frob.strata._sysdoc import merge_models

    design_dir = _design_dir(root)
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        for error in ids.errors:
            _log.error("deploy drift: %s failed to load: %s", error.path, error.error)
        return None
    if not ids.models:
        _log.debug("deploy drift: no design models under %s/%s", root, design_dir)
        return None
    return merge_models(ids.models)


def _current_model_output(root: Path) -> dict[str, str] | None:
    """Regenerate `{filename: content}` from the current design model
    (`_load_current_model`), or `None` if no model loads -- a `deploy/`
    dir with no design behind it cannot be checked against anything, so
    DEPLOY001 has nothing to say."""
    from ._generate import generate_all

    model = _load_current_model(root)
    if model is None:
        return None
    return generate_all(model)


# frob:doc docs/strata/host.md#the-deploy-generator
# frob:tests tests/unit/deploy/test_drift.py::TestDrift.test_no_dir kind="unit"
# frob:tests tests/unit/deploy/test_drift.py::TestDrift.test_clean kind="unit"
# frob:tests tests/unit/deploy/test_drift.py::TestDrift.test_stale kind="unit"
def deploy_drift_violations(root: Path) -> tuple[DeployDriftViolation, ...]:
    """DEPLOY001: every committed `deploy/<file>` that differs from
    regenerating `frob.deploy.generate_all` from the CURRENT model
    (module docstring). Opt-in on `deploy/` existing; returns `()`
    (clean) when the directory is absent, when no design model loads, or
    when every present generated file matches its fresh regeneration."""
    deploy_dir = root / "deploy"
    if not deploy_dir.is_dir():
        _log.debug("deploy drift: no deploy/ directory, skipping")
        return ()

    fresh = _current_model_output(root)
    if fresh is None:
        return ()

    violations = _drift_for_files(deploy_dir, fresh)
    _log.info(
        "deploy drift: checked %d generated file(s), %d violation(s)",
        len(_GENERATED_FILENAMES),
        len(violations),
    )
    return tuple(violations)


def _drift_for_files(
    deploy_dir: Path, fresh: dict[str, str]
) -> list[DeployDriftViolation]:
    """DEPLOY001 violations across every committed generated file under
    `deploy_dir`, skipping any not present."""
    violations: list[DeployDriftViolation] = []
    for filename in _GENERATED_FILENAMES:
        committed_path = deploy_dir / filename
        if not committed_path.exists():
            _log.debug("deploy drift: %s not committed, skipping", filename)
            continue
        committed_text = committed_path.read_text(encoding="utf-8")
        if committed_text != fresh[filename]:
            _log.error(
                "deploy drift: deploy/%s does not match regeneration from the "
                "current model -- run `frob deploy generate`",
                filename,
            )
            violations.append(
                DeployDriftViolation(
                    file=f"deploy/{filename}",
                    message=(
                        f"deploy/{filename} does not match regeneration from "
                        f"the current design model; run `frob deploy generate`"
                    ),
                )
            )
    return violations


__all__ = [
    "DeployDriftViolation",
    "deploy_drift_violations",
]
