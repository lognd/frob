"""Surface-syntax hardened-twin litmus golden (T-0138).

`design/litmus/audit_hardened.strata` must reproduce, end to end through
`parse_module -> elaborate -> evaluate_exhaustiveness`, a PROVED-clean
result for the exact firing preconditions that `audit_vuln.strata` refutes
-- `web`'s `may "sql"` capability, discharged in both the security
(CWE-89) and quality (CWE-639) families via a STRING-quoted discharge
claim id (`weakness:<cwe-id>:<node-id>`, `_threat.py::_discharge_claim_id`).
This is the exact fixture `audit_vuln.strata`'s docstring flagged as
BLOCKED by the pre-T-0138 bare-IDENT-only claim-id grammar; it now
round-trips through the real parser. Permanent CI fixture.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates import known_gate_rule_ids
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
    text = (_LITMUS_DIR / "audit_hardened.strata").read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


class TestAuditHardenedGolden:
    """design/litmus/audit_hardened.strata's discharge claims, evaluated
    end to end through the audit entrypoint."""

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_string_quoted_claim_ids_round_trip(self):
        model = _load_model()
        ids = {c.id for c in model.claims}
        assert ids == {"weakness:CWE-89:web", "weakness:CWE-639:web"}

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_proves_clean_in_security_and_quality(self):
        """T-0503: `known_rule_ids=known_gate_rule_ids()` is now required
        for a clean PROVED result -- `COMPLIANCE_OUT_OF_SCOPE`'s caught_by
        entry references a real gate rule (PII010) that only resolves
        against the live gate-rule-id set, mirroring `frob.app.sys_runner`'s
        own production callsite."""
        model = _load_model()
        result = evaluate_exhaustiveness(model, known_rule_ids=known_gate_rule_ids())
        assert result.is_ok
        report = result.danger_ok
        assert report.proved
        assert report.gaps == ()
