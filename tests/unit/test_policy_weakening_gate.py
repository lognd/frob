"""INV051 gate tests (T-1843): `frob.gates._policy_weakening_gate.
policy_weakening_gate` over a real `design/` directory on disk -- exercises
the whole load -> compile -> diff path `find_policy_weakenings` (T-1482)
otherwise has no caller for, not just the pure diff function in isolation
(`tests/unit/strata/test_policy.py::TestRefinementMonotonicity` already
covers that half)."""

from __future__ import annotations

from pathlib import Path

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
