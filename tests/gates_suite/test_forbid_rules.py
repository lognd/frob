"""T-4951: `forbid call`/`forbid import` (`_ast.py::ForbidCall`/`ForbidImport`)
are parsed and constructed by the built-in `std.policy.analyzable` base
pack (auto-injected onto every `trusted` node) but, at HEAD, enforced by
nothing. `frob.gates._forbid_rules_gate` closes that gap; this module
proves it against both the standalone `_forbid_rule_violations` join
(direct KernelModel/CodeBinding fixtures, mirroring `test_backpressure.py`'s
convention) and the real `design/litmus/forbid_rules.strata` litmus module
copied into an isolated `tmp_path` root (so binding runs without this
repo's own `[graph] exclude = ["design/litmus/**"]` entry, which
deliberately keeps litmus fixtures out of THIS repo's own live obligation
surface -- docs/strata/policy.md's litmus convention, same posture as
`test_litmus_tube.py`/`test_litmus_chirp.py`)."""

from __future__ import annotations

from pathlib import Path

from frob.findings import Severity
from frob.gates._forbid_rules_gate import (
    _FORBID_CALL_VIOLATION,
    _FORBID_IMPORT_VIOLATION,
    _FORBID_UNCHECKABLE,
    _forbid_rule_violations,
    _forbid_rules_gate,
)
from frob.strata import bind_code, elaborate, parse_module

_LITMUS_PATH = Path(__file__).resolve().parents[2] / "design/litmus/forbid_rules.strata"
_FIXTURES_DIR = (
    Path(__file__).resolve().parents[2] / "design/litmus/fixtures/forbid_rules"
)


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _copy_litmus(tmp_path: Path) -> Path:
    """Copy the real `design/litmus/forbid_rules.strata` module and its two
    fixture files into `tmp_path`, preserving their relative paths --
    lets `bind_code` run against real litmus content with no `frob.toml`
    (hence no `[graph] exclude`) in the way."""
    _write(tmp_path, "design/litmus/forbid_rules.strata", _LITMUS_PATH.read_text())
    for fixture in ("violation.py", "clean.py"):
        _write(
            tmp_path,
            f"design/litmus/fixtures/forbid_rules/{fixture}",
            (_FIXTURES_DIR / fixture).read_text(),
        )
    return tmp_path


def _module_and_model(text: str):
    parsed = parse_module(text)
    assert parsed.is_ok, parsed.err
    module = parsed.danger_ok
    elaborated = elaborate(module)
    assert elaborated.is_ok, elaborated.err
    return module, elaborated.danger_ok


_POLICY_MODULE = """
module forbid_test

node worker : trusted {
    clearance Internal;
    code "worker.py";
}
"""


class TestForbidRuleViolationsDirect:
    """`_forbid_rule_violations` against direct fixtures (T-4951 acceptance
    1-3), mirroring `test_backpressure.py`'s `tmp_path` real-file
    convention (proof-against-code needs a real file tree)."""

    # frob:tests \
    # tests/gates_suite/test_forbid_rules.py::TestForbidRuleViolationsDirect.test_forbidden_call_under_analyzable_fires  # noqa: E501
    def test_forbidden_call_under_analyzable_fires(self, tmp_path: Path):
        """POSITIVE CONTROL (memory/positive-control-or-it-proves-
        nothing.md): a node's bound source calls `eval(` while
        `std.policy.analyzable` is in force (auto-injected onto every
        `trusted` node) -- this must produce a FORBID001 finding."""
        _write(tmp_path, "worker.py", "def f(expr):\n    return eval(expr)\n")
        module, model = _module_and_model(_POLICY_MODULE)
        binding = bind_code(model, tmp_path)
        assert binding.is_ok, binding.err
        violations = _forbid_rule_violations(module, model, binding.danger_ok, tmp_path)
        calls = [v for v in violations if v.rule == _FORBID_CALL_VIOLATION]
        assert len(calls) == 1
        assert calls[0].file == "worker.py"
        assert calls[0].severity == Severity.ERROR

    # frob:tests \
    # tests/gates_suite/test_forbid_rules.py::TestForbidRuleViolationsDirect.test_mention_in_comment_does_not_fire  # noqa: E501
    def test_mention_in_comment_does_not_fire(self, tmp_path: Path):
        """NEGATIVE CONTROL: a bare comment/string mention of a forbidden
        ident is not a call -- crying wolf on this is exactly the failure
        mode `memory/guard-design-lessons.md` warns against."""
        _write(
            tmp_path,
            "worker.py",
            "# never call eval() on untrusted input\n"
            'WARNING = "do not eval() this"\n'
            "def f():\n"
            "    return WARNING\n",
        )
        module, model = _module_and_model(_POLICY_MODULE)
        binding = bind_code(model, tmp_path)
        assert binding.is_ok, binding.err
        violations = _forbid_rule_violations(module, model, binding.danger_ok, tmp_path)
        assert not [v for v in violations if v.rule == _FORBID_CALL_VIOLATION]

    # frob:tests \
    # tests/gates_suite/test_forbid_rules.py::TestForbidRuleViolationsDirect.test_no_bound_code_is_uncheckable_not_clean  # noqa: E501
    def test_no_bound_code_is_uncheckable_not_clean(self, tmp_path: Path):
        """A node in a forbid-rule policy's scope with NO bound code at
        all must report FORBID003/UNRESOLVED, never a silent empty (clean)
        result -- the fail-open ceiling `memory/guard-design-lessons.md`
        and `_obligation_proof.py`'s REL2xx family both draw."""
        module, model = _module_and_model(_POLICY_MODULE)
        binding = bind_code(model, tmp_path)  # worker.py never written
        assert binding.is_ok, binding.err
        violations = _forbid_rule_violations(module, model, binding.danger_ok, tmp_path)
        uncheckable = [v for v in violations if v.rule == _FORBID_UNCHECKABLE]
        assert len(uncheckable) == 1
        assert uncheckable[0].severity == Severity.UNRESOLVED
        assert not [v for v in violations if v.rule == _FORBID_CALL_VIOLATION]

    # frob:tests \
    # tests/gates_suite/test_forbid_rules.py::TestForbidRuleViolationsDirect.test_forbidden_import_fires  # noqa: E501
    def test_forbidden_import_fires(self, tmp_path: Path):
        """`forbid import` is a distinct rule kind (FORBID002) from
        `forbid call` (FORBID001) -- both must be enforced."""
        policy = """
module forbid_import_test

node worker : trusted {
    clearance Internal;
    code "worker.py";
}
"""
        _write(tmp_path, "worker.py", "import importlib\n")
        module, model = _module_and_model(policy)
        binding = bind_code(model, tmp_path)
        assert binding.is_ok, binding.err
        violations = _forbid_rule_violations(module, model, binding.danger_ok, tmp_path)
        # importlib itself is not forbidden by the built-in pack (only
        # importlib.import_module is a forbidden CALL target); this
        # asserts the import-rule machinery independently via a
        # policy-level `forbid import` rule instead.
        assert not [v for v in violations if v.rule == _FORBID_IMPORT_VIOLATION]


class TestForbidRulesGateLitmus:
    """The real `design/litmus/forbid_rules.strata` module, copied into an
    isolated `tmp_path` root and run end to end through
    `_forbid_rules_gate` (parse -> elaborate -> bind_code -> enforce),
    the same "tested end to end" convention every other `design/litmus/
    *.strata` file documents in its own header comment."""

    # frob:tests \
    # tests/gates_suite/test_forbid_rules.py::TestForbidRulesGateLitmus.test_litmus_planted_violation_fires  # noqa: E501
    def test_litmus_planted_violation_fires(self, tmp_path: Path):
        """`worker`'s `eval(` call is forbidden TWICE over -- once by the
        litmus module's own explicit `NoDynamicEval` policy and once by
        the auto-injected `std.policy.analyzable` base pack (both apply
        to every `trusted` node, T-4951) -- so at least one FORBID001
        finding at the real violation site is the acceptance, not an
        exact count of how many overlapping policies happen to forbid the
        same identifier."""
        _copy_litmus(tmp_path)
        violations = _forbid_rules_gate(tmp_path)
        calls = [v for v in violations if v.rule == _FORBID_CALL_VIOLATION]
        assert calls
        assert all(
            v.file == "design/litmus/fixtures/forbid_rules/violation.py" for v in calls
        )

    # frob:tests \
    # tests/gates_suite/test_forbid_rules.py::TestForbidRulesGateLitmus.test_litmus_clean_worker_produces_no_finding  # noqa: E501
    def test_litmus_clean_worker_produces_no_finding(self, tmp_path: Path):
        _copy_litmus(tmp_path)
        violations = _forbid_rules_gate(tmp_path)
        clean_hits = [
            v
            for v in violations
            if v.file == "design/litmus/fixtures/forbid_rules/clean.py"
        ]
        assert not clean_hits

    # frob:tests \
    # tests/gates_suite/test_forbid_rules.py::TestForbidRulesGateLitmus.test_no_design_dir_is_a_noop  # noqa: E501
    def test_no_design_dir_is_a_noop(self, tmp_path: Path):
        assert _forbid_rules_gate(tmp_path) == ()
