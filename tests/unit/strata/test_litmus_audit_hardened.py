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

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._audit import evaluate_exhaustiveness


# frob:waive DUP001 reason="parallel litmus scenario fixtures: 7 sites \
# across 7 file(s) sharing the exhaustiveness-fixture arrange-act shape by \
# design (store-backed vs non-store-backed, or per-CWE scenario variants); \
# extracting would obscure per-scenario intent"
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
        model = _load_model()
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert report.proved
        assert report.gaps == ()
