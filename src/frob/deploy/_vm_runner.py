"""VM orchestration half of `frob deploy audit --vm` (T-0259). Deliberately
thin: a sequence of `VBoxManage`/`ssh` subprocess calls that fill in
`_audit.StateCapture` values and drive the sequence spec, then hand
everything to `_audit.build_attestation` (pure, fully unit-tested) for the
actual proofs. Nothing in this module re-implements diffing or proof
logic -- if you're tempted to compare two states here, that logic belongs
in `_audit.py` instead.

Graceful degrade (module requirement, T-0259 ticket body): when
`VBoxManage` is not on `PATH`, `run_vm_audit` returns `AuditRunResult`
with `status="skipped"` and a clear reason -- it never fabricates a pass.

Unit-tested (T-0293) with `subprocess.run` faked at this module's
boundary (`tests/unit/deploy/test_vm_runner.py::TestFullSequence`) --
this proves the SEQUENCE and each helper's own control flow, never
real `VBoxManage`/ssh/guest behavior, which stays exercised only by an
actual `frob deploy audit --vm` run against a live guest.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/deploy/_vm_runner.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import hashlib
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.deploy._audit import (
    AuditAttestation,
    CheckpointResult,
    FileFact,
    StateCapture,
    assert_healthy,
    assert_not_installed,
    build_attestation,
)
from frob.deploy._conform import MutationTarget
from frob.logging import get_logger
from frob.process._guard import EXEC_KILL_SWITCH_ENV, guarded_subprocess_run

_log = get_logger(__name__)

_SSH_OPTS = (
    "-o",
    "StrictHostKeyChecking=no",
    "-o",
    "UserKnownHostsFile=/dev/null",
    "-o",
    "ConnectTimeout=20",
)


# frob:doc docs/commands/deploy.md#vm-orchestration
class VmAuditConfig(BaseModel):
    """Everything `run_vm_audit` needs to drive one audit run against one
    VirtualBox guest: the VM name, the snapshot to restore before CHECK
    C0, ssh connection facts, the local directory holding the three
    generated deploy scripts, and the remote paths those scripts declare
    (`expected_paths`/`expected_units`/`expected_targets` -- derived by
    the caller from `expected_mutation_surface(model)`, T-0258, never
    re-derived here)."""

    model_config = ConfigDict(frozen=True)

    vm_name: str
    base_snapshot: str
    ssh_host: str
    ssh_user: str
    ssh_key_path: Path
    deploy_dir: Path
    expected_paths: tuple[str, ...]
    expected_units: tuple[str, ...]
    expected_targets: frozenset[MutationTarget]
    remote_workdir: str = "/tmp/frob-deploy-audit"


# frob:doc docs/commands/deploy.md#vm-orchestration
class AuditRunResult(BaseModel):
    """`run_vm_audit`'s outcome: either `status="ran"` with a filled-in
    `attestation`, or `status="skipped"` with `reason` set (graceful
    degrade, module docstring) -- never a fabricated pass when the VM
    tooling is unavailable."""

    model_config = ConfigDict(frozen=True)

    status: str
    reason: str | None = None
    attestation: AuditAttestation | None = None


# frob:doc docs/commands/deploy.md#vm-orchestration
def vboxmanage_available() -> bool:
    """`True` iff `VBoxManage` resolves on `PATH` -- the ONE gate
    `run_vm_audit` checks before doing anything else, so a host without
    VirtualBox installed degrades cleanly instead of failing deep inside
    a subprocess call."""
    return shutil.which("VBoxManage") is not None


def _run_guarded(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    """`subprocess.run(args, **kwargs)` routed through `guarded_subprocess_
    run` (T-0778/T-0803) so `FROB_DISABLE_EXEC=1` refuses every VBoxManage/
    ssh/scp spawn this module makes, not just `frob check`'s own tool
    runners. Raises `RuntimeError` (instead of silently returning) when the
    kill switch is flipped, matching this module's existing "let a spawn
    failure raise, no local error handling" contract (`check=True` sites
    already raise `CalledProcessError` on a nonzero exit; a refused spawn
    is the same class of hard failure, not a soft skip)."""
    guarded = guarded_subprocess_run(args, **kwargs)
    if guarded.is_err:
        msg = f"exec disabled ({EXEC_KILL_SWITCH_ENV}) -- refused to spawn {args!r}"
        raise RuntimeError(msg)
    return guarded.danger_ok


def _vboxmanage(*args: str) -> subprocess.CompletedProcess[str]:
    """Run one `VBoxManage` subcommand, capturing output as text."""
    return _run_guarded(
        ["VBoxManage", *args], capture_output=True, text=True, check=True
    )


def _ssh(cfg: VmAuditConfig, remote_command: str) -> str:
    """Run one command over ssh on the guest, returning stdout text."""
    result = _run_guarded(
        [
            "ssh",
            *_SSH_OPTS,
            "-i",
            str(cfg.ssh_key_path),
            f"{cfg.ssh_user}@{cfg.ssh_host}",
            remote_command,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _scp_to_guest(cfg: VmAuditConfig, local_path: Path, remote_path: str) -> None:
    """Copy one local file onto the guest via `scp`."""
    _run_guarded(
        [
            "scp",
            *_SSH_OPTS,
            "-i",
            str(cfg.ssh_key_path),
            str(local_path),
            f"{cfg.ssh_user}@{cfg.ssh_host}:{remote_path}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def _restore_base_snapshot(cfg: VmAuditConfig) -> None:
    """Power off (idempotent -- ignores "not running") and restore the
    guest to `cfg.base_snapshot`, then start it headless. This is the
    sequence's very first step, run once before CHECK C0."""
    _run_guarded(
        ["VBoxManage", "controlvm", cfg.vm_name, "poweroff"],
        capture_output=True,
        text=True,
        check=False,
    )
    _vboxmanage("snapshot", cfg.vm_name, "restore", cfg.base_snapshot)
    _vboxmanage("startvm", cfg.vm_name, "--type", "headless")


# Only the manifest-declared paths/units are captured individually (a
# full-disk walk is not practical over ssh); artifact-freeness still
# catches an UNEXPECTED path because `diff_states` compares the two
# captures' `filesystem` dicts key-for-key, and any path
# install.sh/uninstall.sh touched outside `expected_paths` would make S0
# and S2 differ in whichever surviving artifact IS in both captures' path
# sets, or -- for a path fully outside what either snapshot enumerates --
# is out of this capture strategy's reach, a documented scope cut (see
# docs/commands/deploy.md#state-capture).
def _capture_state(cfg: VmAuditConfig, label: str) -> StateCapture:
    """One CHECK's state half: ssh in and hash/stat every
    `cfg.expected_paths` entry, read `/etc/passwd`+`/etc/group`, read
    every `cfg.expected_units` unit file body, list the enabled-unit set,
    and list listening sockets (`ss -tln`)."""
    filesystem = _capture_filesystem_facts(cfg)
    passwd = tuple(_ssh(cfg, "cat /etc/passwd").splitlines())
    group = tuple(_ssh(cfg, "cat /etc/group").splitlines())
    unit_files = _capture_unit_files(cfg)
    enabled = _ssh_nonblank_lines(
        cfg, "systemctl list-unit-files --state=enabled --no-legend 2>/dev/null"
    )
    sockets = _ssh_nonblank_lines(cfg, "ss -tln 2>/dev/null | tail -n +2")

    return StateCapture(
        label=label,
        filesystem=filesystem,
        passwd=passwd,
        group=group,
        unit_files=unit_files,
        enabled_units=enabled,
        listening_sockets=sockets,
    )


def _capture_filesystem_facts(cfg: VmAuditConfig) -> dict[str, FileFact]:
    """Hash/stat every `cfg.expected_paths` entry present on the guest."""
    filesystem: dict[str, FileFact] = {}
    for path in cfg.expected_paths:
        stat_out = _ssh(
            cfg,
            f'if [ -e "{path}" ]; then '
            f'sha256sum "{path}" 2>/dev/null | cut -d" " -f1; '
            f'stat -c "%U %G %a" "{path}"; '
            "else echo MISSING; fi",
        ).strip()
        if stat_out == "MISSING" or not stat_out:
            continue
        lines = stat_out.splitlines()
        digest = lines[0] if len(lines) > 1 else hashlib.sha256(b"").hexdigest()
        owner, group, mode = lines[-1].split()
        filesystem[path] = FileFact(sha256=digest, owner=owner, group=group, mode=mode)
    return filesystem


def _capture_unit_files(cfg: VmAuditConfig) -> dict[str, str]:
    """Every `cfg.expected_units` unit file body present on the guest."""
    unit_files: dict[str, str] = {}
    for unit in cfg.expected_units:
        body = _ssh(
            cfg,
            f'cat "/etc/systemd/system/{unit}" 2>/dev/null || echo MISSING',
        )
        if body.strip() != "MISSING":
            unit_files[unit] = body
    return unit_files


def _ssh_nonblank_lines(cfg: VmAuditConfig, command: str) -> tuple[str, ...]:
    """Run `command` over ssh and return its non-blank, stripped output lines."""
    return tuple(
        line.strip() for line in _ssh(cfg, command).splitlines() if line.strip()
    )


def _run_status_and_assert(
    cfg: VmAuditConfig, label: str, *, expect_installed: bool
) -> CheckpointResult:
    """Run `status.sh` on the guest and check it against the expected
    health at this checkpoint (module docstring: not-installed at C0/C2,
    healthy at C1/C1') -- the "assert status.sh reports X" half of every
    CHECK, always paired with `_capture_state` for that same label."""
    status_text = _ssh(cfg, f"bash {cfg.remote_workdir}/status.sh")
    passed = (
        assert_not_installed(status_text)
        if not expect_installed
        else assert_healthy(status_text, frozenset(cfg.expected_units))
    )
    return CheckpointResult(
        label=label, status_assertion=status_text, status_assertion_passed=passed
    )


# frob:doc docs/commands/deploy.md#vm-orchestration
def run_vm_audit(cfg: VmAuditConfig) -> AuditRunResult:
    """Drive the full T-0259 sequence: restore base snapshot -> CHECK C0
    -> install.sh -> CHECK C1 -> install.sh again -> CHECK C1' ->
    uninstall.sh -> CHECK C2 (module docstring) -- then hand the four
    captures to `_audit.build_attestation` for the actual proofs.
    Graceful degrade: returns `status="skipped"` immediately, before any
    `VBoxManage`/`ssh` call, when `vboxmanage_available()` is `False`."""
    if not vboxmanage_available():
        _log.warning("deploy audit: VBoxManage not found on PATH, skipping VM audit")
        return AuditRunResult(status="skipped", reason="VBoxManage not found on PATH")

    started_at = datetime.now(UTC)
    _restore_base_snapshot(cfg)
    _stage_scripts(cfg)

    c0, s0, c1, s1, c1_prime, s1_prime, c2, s2 = _run_checkpoint_sequence(cfg)

    attestation = build_attestation(
        vm_name=cfg.vm_name,
        base_snapshot=cfg.base_snapshot,
        started_at=started_at,
        checkpoints=(c0, c1, c1_prime, c2),
        s0=s0,
        s1=s1,
        s1_prime=s1_prime,
        s2=s2,
        expected_surface=cfg.expected_targets,
    )
    return AuditRunResult(status="ran", attestation=attestation)


def _stage_scripts(cfg: VmAuditConfig) -> None:
    """Create the remote workdir, copy install/status/uninstall scripts to
    the guest, and make them executable."""
    _ssh(cfg, f"mkdir -p {cfg.remote_workdir}")
    for script in ("install.sh", "status.sh", "uninstall.sh"):
        _scp_to_guest(cfg, cfg.deploy_dir / script, f"{cfg.remote_workdir}/{script}")
    _ssh(cfg, f"chmod +x {cfg.remote_workdir}/*.sh")


def _run_checkpoint_sequence(
    cfg: VmAuditConfig,
) -> tuple[
    CheckpointResult,
    StateCapture,
    CheckpointResult,
    StateCapture,
    CheckpointResult,
    StateCapture,
    CheckpointResult,
    StateCapture,
]:
    """Drive C0 -> install -> C1 -> install again -> C1' -> uninstall -> C2,
    returning each checkpoint's (status-assertion, state-capture) pair in
    sequence order."""
    c0 = _run_status_and_assert(cfg, "C0", expect_installed=False)
    s0 = _capture_state(cfg, "S0")

    _ssh(cfg, f"sudo bash {cfg.remote_workdir}/install.sh")
    c1 = _run_status_and_assert(cfg, "C1", expect_installed=True)
    s1 = _capture_state(cfg, "S1")

    _ssh(cfg, f"sudo bash {cfg.remote_workdir}/install.sh")
    c1_prime = _run_status_and_assert(cfg, "C1'", expect_installed=True)
    s1_prime = _capture_state(cfg, "S1'")

    _ssh(cfg, f"sudo bash {cfg.remote_workdir}/uninstall.sh")
    c2 = _run_status_and_assert(cfg, "C2", expect_installed=False)
    s2 = _capture_state(cfg, "S2")

    return c0, s0, c1, s1, c1_prime, s1_prime, c2, s2
