"""CLI wiring for `frob deploy` -- compile `std.host` `HostManifest` facts
into Linux/systemd install/status/uninstall bash (T-0257), plus the
empirical VirtualBox snapshot-diff audit (`audit`, T-0259, deploy epic
T-0254 child 5).

`generate`: loads every `.strata` design file under the repo's design dir
(same `load_design_ids`/`merge_models` pattern `frob.app.sys_runner`
already uses for `plan`/`doc`/`audit`), renders the three scripts via
`frob.deploy.generate_all`, and writes them to `cfg.deploy_out_dir`
(default `deploy/`) -- printing a dry-run diff summary instead when
`--check` is passed, so CI can verify the committed scripts are current
without mutating the tree (the same check the DEPLOY001 drift gate
performs during `frob check`, exposed here as a standalone command for a
pre-commit hook or manual verification).

`audit --vm <name>`: NOT run by `make check` (expensive, requires a real
VirtualBox guest). Loads the same merged design model, derives the
expected mutation surface from it (`frob.deploy.expected_mutation_surface`,
T-0258 -- never re-derived here), and drives
`frob.deploy.run_vm_audit`'s sequence spec (`frob.deploy._audit`'s module
docstring: restore snapshot -> CHECK C0 -> install -> CHECK C1 -> install
again -> CHECK C1' -> uninstall -> CHECK C2). Writes the resulting
`AuditAttestation` as JSON to `cfg.deploy_audit_output` (default
`deploy-audit-attestation.json`) and exits 0 (all proofs held), 1 (ran,
at least one proof or status assertion failed), or 2 (`VBoxManage` not
on `PATH` -- SKIPPED, never a fabricated pass, module docstring's
graceful-degrade requirement) so `--evidence-cmd` (T-0215) can never
record a skip as a pass.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from frob.app.config import AppConfig
from frob.deploy import (
    AuditRunResult,
    VmAuditConfig,
    expected_mutation_surface,
    generate_all,
    run_vm_audit,
    sorted_manifest_entries,
)
from frob.logging import get_logger
from frob.strata import DEFAULT_DESIGN_DIR, KernelModel, load_design_ids
from frob.strata._sysdoc import merge_models

_log = get_logger(__name__)

#: `run` (below) dispatches on `cfg.deploy_command`; every recognized verb
#: is listed here so the usage message (module-level fallback) never
#: silently drifts from what `run` actually accepts.
_USAGE = (
    "usage: frob deploy generate [--check] [path]\n"
    "       frob deploy audit --vm <name> [--ssh-host H] [--ssh-user U] "
    "--ssh-key KEY [--base-snapshot NAME] [--output PATH] [path]"
)


def _design_dir(root: Path) -> str:
    """`[strata].design_dir` from `frob.toml`, defaulting like every other
    strata-consuming runner (`frob.app.sys_runner._design_dir` precedent;
    a two-line frob.toml read is not worth a cross-module import, per
    that module's own docstring)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return DEFAULT_DESIGN_DIR
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("deploy generate: frob.toml unreadable: %s", exc)
        return DEFAULT_DESIGN_DIR
    return data.get("strata", {}).get("design_dir", DEFAULT_DESIGN_DIR)


def _load_model(root: Path) -> KernelModel | None:
    """Load+merge every `.strata` design file under the repo's design dir
    into one `KernelModel`, or `None` (error already logged) on any load
    failure or an empty design set."""
    design_dir = _design_dir(root)
    ids = load_design_ids(root, design_dir)
    if ids.errors:
        for error in ids.errors:
            _log.error(
                "deploy generate: %s failed to load: %s", error.path, error.error
            )
        return None
    if not ids.models:
        _log.info("deploy generate: no design models under %s/%s", root, design_dir)
        return None
    return merge_models(ids.models)


def _mismatched_generated_files(out_dir: Path, rendered: dict[str, str]) -> list[str]:
    """Filenames in `rendered` that are missing from `out_dir` or whose
    on-disk content no longer matches (drives `--check`'s exit-1 report)."""
    mismatched: list[str] = []
    for filename, content in sorted(rendered.items()):
        path = out_dir / filename
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            mismatched.append(filename)
    return mismatched


def _run_generate_check(out_dir: Path, rendered: dict[str, str]) -> None:
    """`frob deploy generate --check`: verify the committed scripts already
    match `rendered`, exiting 1 (no writes) on any mismatch."""
    mismatched = _mismatched_generated_files(out_dir, rendered)
    if mismatched:
        for filename in mismatched:
            _log.error(
                "deploy generate --check: %s missing or stale -- run "
                "`frob deploy generate` to regenerate",
                filename,
            )
        sys.exit(1)
    _log.info("deploy generate --check: all %d file(s) current", len(rendered))


def _write_generated_files(out_dir: Path, rendered: dict[str, str]) -> None:
    """Write every rendered script to `out_dir`, executable, creating the
    directory as needed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in sorted(rendered.items()):
        path = out_dir / filename
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)
        _log.info("deploy generate: wrote %s", path)


def _run_generate(cfg: AppConfig) -> None:
    """`frob deploy generate [--check] [path]`: write `install.sh`/
    `status.sh`/`uninstall.sh` to `deploy/` (or `--check` to verify the
    committed scripts already match, exit 1 on any mismatch, no writes)."""
    root = (cfg.deploy_path or Path(".")).resolve()
    model = _load_model(root)
    if model is None:
        sys.exit(1)

    rendered = generate_all(model)
    out_dir = root / (cfg.deploy_out_dir or Path("deploy"))

    if cfg.deploy_check:
        _run_generate_check(out_dir, rendered)
        return

    _write_generated_files(out_dir, rendered)


def _require_audit_flags(cfg: AppConfig) -> None:
    """Exit 1 (with a logged reason) unless every flag `frob deploy audit`
    requires (`--vm`, `--ssh-host`, `--ssh-key`) is present."""
    if not cfg.deploy_vm:
        _log.error("deploy audit: --vm <name> is required")
        sys.exit(1)
    if not cfg.deploy_ssh_host:
        _log.error("deploy audit: --ssh-host is required")
        sys.exit(1)
    if not cfg.deploy_ssh_key:
        _log.error("deploy audit: --ssh-key is required")
        sys.exit(1)


def _build_vm_audit_config(
    cfg: AppConfig, root: Path, model: KernelModel
) -> VmAuditConfig:
    """Derive the expected mutation surface from `model` and assemble the
    `VmAuditConfig` `run_vm_audit` drives the VM snapshot-diff harness with."""
    # Narrows for the type checker; caller (`_run_audit`) already enforced
    # via `_require_audit_flags` that these are all present.
    assert cfg.deploy_vm is not None
    assert cfg.deploy_ssh_host is not None
    assert cfg.deploy_ssh_key is not None
    entries = sorted_manifest_entries(model)
    expected_targets = expected_mutation_surface(entries)
    expected_paths = tuple(sorted({o.path for e in entries for o in e.manifest.owns}))
    expected_units = tuple(
        sorted(t.target for t in expected_targets if t.kind == "unit")
    )
    deploy_dir = root / (cfg.deploy_out_dir or Path("deploy"))
    return VmAuditConfig(
        vm_name=cfg.deploy_vm,
        base_snapshot=cfg.deploy_base_snapshot,
        ssh_host=cfg.deploy_ssh_host,
        ssh_user=cfg.deploy_ssh_user,
        ssh_key_path=cfg.deploy_ssh_key,
        deploy_dir=deploy_dir,
        expected_paths=expected_paths,
        expected_units=expected_units,
        expected_targets=expected_targets,
    )


def _report_audit_result(cfg: AppConfig, root: Path, result: AuditRunResult) -> None:
    """Write the attestation (when present) and log/exit according to
    `result.status`/`.attestation.passed` -- exits 0 (passed), 1 (failed),
    or 2 (skipped, `VBoxManage` absent)."""
    r = result
    output_path = root / (
        cfg.deploy_audit_output or Path("deploy-audit-attestation.json")
    )

    if r.status == "skipped":
        _log.warning("deploy audit: SKIPPED -- %s", r.reason)
        sys.exit(2)

    assert r.attestation is not None  # narrows for the type checker
    output_path.write_text(r.attestation.to_json(), encoding="utf-8")
    _log.info("deploy audit: wrote attestation to %s", output_path)

    if r.attestation.passed:
        _log.info("deploy audit: PASSED (vm=%s)", cfg.deploy_vm)
        return
    _log.error(
        "deploy audit: FAILED (vm=%s) idempotence=%s artifact_freeness=%s "
        "install_exactness=%s",
        cfg.deploy_vm,
        r.attestation.idempotence_holds,
        r.attestation.artifact_freeness_holds,
        r.attestation.install_exactness_holds,
    )
    sys.exit(1)


def _run_audit(cfg: AppConfig) -> None:
    """`frob deploy audit --vm <name> [path]`: drive the T-0259 VM
    snapshot-diff harness against a live VirtualBox guest and write the
    resulting attestation JSON. Exits 0 (passed), 1 (ran, a proof or
    status assertion failed), or 2 (`VBoxManage` absent -- SKIPPED,
    module docstring's graceful-degrade requirement)."""
    _require_audit_flags(cfg)

    root = (cfg.deploy_path or Path(".")).resolve()
    model = _load_model(root)
    if model is None:
        sys.exit(1)

    vm_cfg = _build_vm_audit_config(cfg, root, model)
    result = run_vm_audit(vm_cfg)
    _report_audit_result(cfg, root, result)


# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """Dispatch `frob deploy <command>`: `generate` (T-0257) writes the
    three scripts; `audit` (T-0259) drives the VM snapshot-diff harness
    against a live guest."""
    if cfg.deploy_command == "generate":
        _run_generate(cfg)
        return
    if cfg.deploy_command == "audit":
        _run_audit(cfg)
        return
    _log.error(_USAGE)
    sys.exit(1)
