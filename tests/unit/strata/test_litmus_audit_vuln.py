"""Surface-syntax exhaustiveness litmus golden (T-0115).

`design/litmus/audit_vuln.strata` must reproduce, end to end through
`parse_module -> elaborate -> evaluate_exhaustiveness`, an undischarged
THREAT003 obligation in BOTH the security and quality families from one
`may "sql"` capability declaration (docs/strata/threat.md#beyond-security-
the-anti-pattern-families) -- the one piece of the T-0115 vuln-litmus that
round-trips through the parser today (module docstring on the `.strata`
file explains where the hardened twin now lives -- `audit_hardened.
strata`, T-0138 -- and why the compliance family still lives in
tests/unit/strata/test_audit.py). This golden is a permanent CI
fixture.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._audit import evaluate_exhaustiveness


def _repo_root() -> Path:
    """Walk up from this file until a directory containing `frob.toml` is found."""
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "frob.toml").is_file():
            return candidate
    raise RuntimeError(
        "could not locate repo root (no frob.toml found above test file)"
    )


_LITMUS_DIR = _repo_root() / "design" / "litmus"


def _load_model() -> KernelModel:
    text = (_LITMUS_DIR / "audit_vuln.strata").read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


class TestAuditVulnGolden:
    """design/litmus/audit_vuln.strata's `may "sql"` capability, evaluated
    end to end through the audit entrypoint."""

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_may_sql_parses_and_elaborates(self):
        model = _load_model()
        web = next(n for n in model.nodes if n.id == "web")
        assert web.may == ("sql",)

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_fires_undischarged_in_security_and_quality(self):
        model = _load_model()
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert not report.proved
        assert any(
            g.family == "security" and g.rule == "THREAT003" and "CWE-89" in g.detail
            for g in report.gaps
        )
        assert any(
            g.family == "quality" and g.rule == "THREAT003" and "CWE-639" in g.detail
            for g in report.gaps
        )
