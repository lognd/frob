"""Unit-level coverage for `frob.deploy._audit` (T-0259): the pure diff/
proof/attestation logic behind `frob deploy audit --vm`, exercised
entirely against fixture `StateCapture` dicts -- no VirtualBox, no ssh, no
VM anywhere in this file (module docstring's "isolate the VM orchestration
behind a thin runner so the diff/proof logic is pure and fully
unit-tested" requirement).
"""

from __future__ import annotations

from datetime import UTC, datetime

from frob.deploy._audit import (
    CheckpointResult,
    FileFact,
    StateCapture,
    artifact_freeness_holds,
    assert_healthy,
    assert_not_installed,
    build_attestation,
    diff_states,
    idempotence_holds,
    install_exactness_holds,
)
from frob.deploy._conform import MutationTarget


def _fact(
    sha: str = "aaa", owner: str = "root", group: str = "root", mode: str = "644"
) -> FileFact:
    return FileFact(sha256=sha, owner=owner, group=group, mode=mode)


def _state(
    label: str,
    *,
    filesystem: dict[str, FileFact] | None = None,
    passwd: tuple[str, ...] = (),
    group: tuple[str, ...] = (),
    unit_files: dict[str, str] | None = None,
    enabled_units: tuple[str, ...] = (),
    listening_sockets: tuple[str, ...] = (),
) -> StateCapture:
    return StateCapture(
        label=label,
        filesystem=filesystem or {},
        passwd=passwd,
        group=group,
        unit_files=unit_files or {},
        enabled_units=enabled_units,
        listening_sockets=listening_sockets,
    )


class TestDiff:
    """`diff_states` -- identical captures, an added/changed/removed mix,
    and the allowlist filter."""

    # frob:tests src/frob/deploy/_audit.py::diff_states kind="unit"
    # frob:tests src/frob/deploy/_audit.py::StateDiff.is_empty kind="unit"
    def test_no_diff(self) -> None:
        s = _state(
            "s",
            filesystem={"/etc/api": _fact()},
            passwd=("root:x:0:0:root:/root:/bin/bash",),
        )
        assert diff_states(s, s).is_empty

    # frob:tests src/frob/deploy/_audit.py::diff_states kind="unit"
    def test_delta(self) -> None:
        before = _state(
            "before",
            filesystem={
                "/etc/api": _fact(sha="aaa"),
                "/etc/gone": _fact(sha="bbb"),
            },
        )
        after = _state(
            "after",
            filesystem={
                "/etc/api": _fact(sha="ccc"),
                "/etc/new": _fact(sha="ddd"),
            },
        )
        diff = diff_states(before, after)
        assert diff.added_paths == ("/etc/new",)
        assert diff.removed_paths == ("/etc/gone",)
        assert diff.changed_paths == ("/etc/api",)
        assert not diff.is_empty

    # frob:tests src/frob/deploy/_audit.py::diff_states kind="unit"
    # frob:tests src/frob/deploy/_audit.py::StateDiff.is_empty kind="unit"
    def test_allowlist(self) -> None:
        before = _state("before", filesystem={})
        after = _state("after", filesystem={"/var/log/frob.log": _fact()})
        diff = diff_states(before, after)
        assert diff.is_empty


class TestProofs:
    """Idempotence, artifact-freeness, and install-exactness proofs."""

    # frob:tests src/frob/deploy/_audit.py::idempotence_holds kind="unit"
    def test_holds(self) -> None:
        s1 = _state("s1", filesystem={"/etc/api": _fact()})
        s1_prime = _state("s1p", filesystem={"/etc/api": _fact()})
        assert idempotence_holds(s1, s1_prime)

    # frob:tests src/frob/deploy/_audit.py::idempotence_holds kind="unit"
    def test_fails(self) -> None:
        s1 = _state("s1", filesystem={"/etc/api": _fact(sha="aaa")})
        s1_prime = _state("s1p", filesystem={"/etc/api": _fact(sha="bbb")})
        assert not idempotence_holds(s1, s1_prime)

    # frob:tests src/frob/deploy/_audit.py::artifact_freeness_holds kind="unit"
    def test_af_holds(self) -> None:
        s0 = _state("s0", passwd=("root:x:0:0::/root:/bin/bash",))
        s2 = _state("s2", passwd=("root:x:0:0::/root:/bin/bash",))
        assert artifact_freeness_holds(s0, s2)

    # frob:tests src/frob/deploy/_audit.py::artifact_freeness_holds kind="unit"
    def test_af_fails(self) -> None:
        s0 = _state("s0", filesystem={})
        s2 = _state("s2", filesystem={"/etc/leftover": _fact()})
        assert not artifact_freeness_holds(s0, s2)

    # frob:tests src/frob/deploy/_audit.py::install_exactness_holds kind="unit"
    # frob:tests src/frob/deploy/_audit.py::StateDiff.mutated_targets kind="unit"
    def test_ie_holds(self) -> None:
        s0 = _state("s0")
        s1 = _state(
            "s1",
            filesystem={"/etc/api": _fact()},
            unit_files={"frob-deploy-api.service": "body"},
            passwd=("api-svc:x:100:100::/:/usr/sbin/nologin",),
        )
        expected = frozenset(
            {
                MutationTarget(kind="path", target="/etc/api"),
                MutationTarget(kind="unit", target="frob-deploy-api.service"),
                MutationTarget(kind="user", target="api-svc"),
            }
        )
        holds, extra, missing = install_exactness_holds(s0, s1, expected)
        assert holds
        assert not extra
        assert not missing

    # frob:tests src/frob/deploy/_audit.py::install_exactness_holds kind="unit"
    def test_ie_extra(self) -> None:
        s0 = _state("s0")
        s1 = _state("s1", filesystem={"/etc/api": _fact(), "/etc/rogue": _fact()})
        expected = frozenset({MutationTarget(kind="path", target="/etc/api")})
        holds, extra, missing = install_exactness_holds(s0, s1, expected)
        assert not holds
        assert MutationTarget(kind="path", target="/etc/rogue") in extra
        assert not missing

    # frob:tests src/frob/deploy/_audit.py::install_exactness_holds kind="unit"
    def test_ie_missing(self) -> None:
        s0 = _state("s0")
        s1 = _state("s1", filesystem={})
        expected = frozenset({MutationTarget(kind="path", target="/etc/api")})
        holds, extra, missing = install_exactness_holds(s0, s1, expected)
        assert not holds
        assert not extra
        assert MutationTarget(kind="path", target="/etc/api") in missing


class TestStatus:
    """`assert_not_installed`/`assert_healthy` over raw `status.sh` text."""

    # frob:tests src/frob/deploy/_audit.py::assert_not_installed kind="unit"
    def test_not_inst_true(self) -> None:
        text = (
            "unit=frob-deploy-api.service node=api active=inactive enabled=disabled\n"
        )
        assert assert_not_installed(text)

    # frob:tests src/frob/deploy/_audit.py::assert_not_installed kind="unit"
    def test_not_inst_false(self) -> None:
        text = "unit=frob-deploy-api.service node=api active=active enabled=enabled\n"
        assert not assert_not_installed(text)

    # frob:tests src/frob/deploy/_audit.py::assert_healthy kind="unit"
    def test_healthy_true(self) -> None:
        text = "unit=frob-deploy-api.service node=api active=active enabled=enabled\n"
        assert assert_healthy(text, frozenset({"frob-deploy-api.service"}))

    # frob:tests src/frob/deploy/_audit.py::assert_healthy kind="unit"
    def test_missing_unit(self) -> None:
        text = "unit=frob-deploy-api.service node=api active=active enabled=enabled\n"
        assert not assert_healthy(
            text, frozenset({"frob-deploy-api.service", "frob-deploy-other.service"})
        )


class TestAttest:
    """`build_attestation` -- the assembled `AuditAttestation.passed`."""

    def _checkpoints(self, *, all_pass: bool) -> tuple[CheckpointResult, ...]:
        return (
            CheckpointResult(
                label="C0", status_assertion="", status_assertion_passed=True
            ),
            CheckpointResult(
                label="C1", status_assertion="", status_assertion_passed=all_pass
            ),
            CheckpointResult(
                label="C1'", status_assertion="", status_assertion_passed=True
            ),
            CheckpointResult(
                label="C2", status_assertion="", status_assertion_passed=True
            ),
        )

    # frob:tests src/frob/deploy/_audit.py::build_attestation kind="unit"
    # frob:tests src/frob/deploy/_audit.py::AuditAttestation.passed kind="unit"
    # frob:tests src/frob/deploy/_audit.py::AuditAttestation.to_json kind="unit"
    def test_all_green(self) -> None:
        s0 = _state("s0")
        s1 = _state("s1", filesystem={"/etc/api": _fact()})
        s1_prime = _state("s1p", filesystem={"/etc/api": _fact()})
        s2 = _state("s2")
        expected = frozenset({MutationTarget(kind="path", target="/etc/api")})
        attestation = build_attestation(
            vm_name="test-vm",
            base_snapshot="base",
            started_at=datetime.now(UTC),
            checkpoints=self._checkpoints(all_pass=True),
            s0=s0,
            s1=s1,
            s1_prime=s1_prime,
            s2=s2,
            expected_surface=expected,
        )
        assert attestation.passed
        assert attestation.idempotence_holds
        assert attestation.artifact_freeness_holds
        assert attestation.install_exactness_holds
        parsed = attestation.to_json()
        assert '"vm_name": "test-vm"' in parsed

    # frob:tests src/frob/deploy/_audit.py::build_attestation kind="unit"
    # frob:tests src/frob/deploy/_audit.py::AuditAttestation.passed kind="unit"
    def test_proof_fail(self) -> None:
        s0 = _state("s0")
        s1 = _state("s1", filesystem={"/etc/api": _fact()})
        s1_prime = _state("s1p", filesystem={"/etc/api": _fact(sha="changed")})
        s2 = _state("s2")
        expected = frozenset({MutationTarget(kind="path", target="/etc/api")})
        attestation = build_attestation(
            vm_name="test-vm",
            base_snapshot="base",
            started_at=datetime.now(UTC),
            checkpoints=self._checkpoints(all_pass=True),
            s0=s0,
            s1=s1,
            s1_prime=s1_prime,
            s2=s2,
            expected_surface=expected,
        )
        assert not attestation.idempotence_holds
        assert not attestation.passed
