"""INV051 gate tests (T-1843): `frob.gates._policy_weakening_gate.
policy_weakening_gate` over a real `design/` directory on disk -- exercises
the whole load -> compile -> diff path `find_policy_weakenings` (T-1482)
otherwise has no caller for, not just the pure diff function in isolation
(`tests/unit/strata/test_policy.py::TestRefinementMonotonicity` already
covers that half)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._policy_weakening_gate import policy_weakening_gate


def _write_design(root: Path, text: str) -> None:
    """Write `text` as the sole `.strata` file under `root/design/`."""
    design_dir = root / "design"
    design_dir.mkdir(parents=True, exist_ok=True)
    (design_dir / "m.strata").write_text(text)


class TestPolicyWeakeningGate:
    """`policy_weakening_gate` (INV051)."""

    # frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate.test_no_design_dir_noop  # noqa: E501
    def test_no_design_dir_noop(self, tmp_path: Path) -> None:
        assert policy_weakening_gate(tmp_path) == ()

    # frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate.test_weakening_detected  # noqa: E501
    def test_weakening_detected(self, tmp_path: Path) -> None:
        _write_design(
            tmp_path,
            """
            module m
            node api : trusted
            node db : trusted
            policy Parent on trust >= trusted {
                confine use psycopg to "src/api/db.py"
            }
            policy Child on component api {
                confine use psycopg to "src/other/place.py"
            }
            """,
        )
        violations = policy_weakening_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "INV051"
        assert "Child" in violations[0].message
        assert "Parent" in violations[0].message

    # frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate.test_clean_policies_no_finding  # noqa: E501
    def test_clean_policies_no_finding(self, tmp_path: Path) -> None:
        _write_design(
            tmp_path,
            """
            module m
            node api : trusted
            node db : trusted
            policy Parent on trust >= trusted {
                confine use psycopg to "src/api/db.py"
            }
            policy Child on component api {
                confine use psycopg to "src/api/db.py/nested.py"
            }
            """,
        )
        assert policy_weakening_gate(tmp_path) == ()

    # frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate.test_load_failure_skips_silently  # noqa: E501
    def test_load_failure_skips_silently(self, tmp_path: Path) -> None:
        _write_design(tmp_path, "not valid strata syntax {{{")
        assert policy_weakening_gate(tmp_path) == ()


def _write_design_file(root: Path, filename: str, text: str) -> None:
    """Write `text` as `root/design/<filename>` -- like `_write_design`
    but lets a test control multiple distinct `.strata` files (T-3460:
    needed to exercise per-file INV051 identity, which a single shared
    `m.strata` file cannot distinguish)."""
    design_dir = root / "design"
    design_dir.mkdir(parents=True, exist_ok=True)
    (design_dir / filename).write_text(text)


# frob:ticket T-3460
class TestPolicyWeakeningGateFileIdentity:
    """T-3460: every INV051 finding used to report `Violation.file` as the
    constant `design_dir` regardless of which `.strata` file declared the
    weakening policy -- so two DISTINCT weakenings in two DIFFERENT files
    were indistinguishable by `(rule, file)` identity (the same anchor-
    collapse class T-3419 fixed generically for SELFAUDIT001; INV051's
    own message names policy ids, not a file, so that fix could not
    reach it). `policy_weakening_gate` now resolves each finding's own
    child policy back to its declaring file via `_policy_id_file_map`,
    the same `node_file`-map shape VMOD001 already uses (T-3264)."""

    # frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGateFileIdentity.test_must_fire_two_weakenings_in_different_files_get_distinct_file_identities  # noqa: E501
    def test_must_fire_two_weakenings_in_different_files_get_distinct_file_identities(
        self, tmp_path: Path
    ) -> None:
        """MUST-FIRE fixture (T-3460's own acceptance, mirroring T-3419's):
        two unrelated weakenings declared in two different `.strata`
        files must report two DIFFERENT `(rule, file)` identities, not
        both collapse onto `design_dir`. This MUST FAIL on main (both
        used to report `file="design"`)."""
        _write_design_file(
            tmp_path,
            "a.strata",
            """
            module a
            node api_a : trusted
            policy ParentA on trust >= trusted {
                confine use psycopg to "src/api_a/db.py"
            }
            policy ChildA on component api_a {
                confine use psycopg to "src/other_a/place.py"
            }
            """,
        )
        _write_design_file(
            tmp_path,
            "b.strata",
            """
            module b
            node api_b : trusted
            policy ParentB on trust >= trusted {
                confine use requests to "src/api_b/net.py"
            }
            policy ChildB on component api_b {
                confine use requests to "src/other_b/place.py"
            }
            """,
        )
        violations = policy_weakening_gate(tmp_path)
        assert len(violations) == 2
        identities = {(v.rule, v.file) for v in violations}
        assert identities == {
            ("INV051", "design/a.strata"),
            ("INV051", "design/b.strata"),
        }, (
            "the two weakenings must resolve to their own DISTINCT "
            "declaring files, not collapse onto the shared design_dir "
            "anchor and become indistinguishable"
        )

    # frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGateFileIdentity.test_single_file_weakening_reports_that_real_file  # noqa: E501
    def test_single_file_weakening_reports_that_real_file(self, tmp_path: Path) -> None:
        """Must-still-pass control: the ordinary single-file case (the
        pre-existing `test_weakening_detected` fixture's own scenario)
        now reports the REAL declaring file, not the constant anchor."""
        _write_design(
            tmp_path,
            """
            module m
            node api : trusted
            node db : trusted
            policy Parent on trust >= trusted {
                confine use psycopg to "src/api/db.py"
            }
            policy Child on component api {
                confine use psycopg to "src/other/place.py"
            }
            """,
        )
        violations = policy_weakening_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].file == "design/m.strata"

    # frob:tests tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGateFileIdentity.test_unresolvable_child_id_falls_back_to_design_dir  # noqa: E501
    def test_unresolvable_child_id_falls_back_to_design_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Must-still-pass control: when `_policy_id_file_map` cannot
        resolve a weakening's `child_id` (simulated here -- in practice
        every policy that reached `find_policy_weakenings` was just
        parsed successfully, so this is a defensive fallback, never
        expected in real use), the finding degrades to the pre-T-3460
        `design_dir` anchor rather than raising or dropping the finding."""
        import frob.gates._policy_weakening_gate as gate_mod

        _write_design(
            tmp_path,
            """
            module m
            node api : trusted
            node db : trusted
            policy Parent on trust >= trusted {
                confine use psycopg to "src/api/db.py"
            }
            policy Child on component api {
                confine use psycopg to "src/other/place.py"
            }
            """,
        )
        monkeypatch.setattr(gate_mod, "_policy_id_file_map", lambda root, dd: {})
        violations = policy_weakening_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].file == "design"
