# Litmus fixture mappings

<!-- frob:describes tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens -->

## What it is and where it lives

A litmus fixture is a real `.strata` model proving a catalog family's
rules actually fire on real source, not just in a hand-built
`KernelModel` unit test
(`docs/strata/threat.md#litmus-coverage-every-catalog-entry-fires-from-real-source-t-0145`).
Two directories, two
different jobs:

- `tests/unit/strata/litmus/*.strata` -- one VULN/HARDENED PAIR per
  catalog family (`cwe_79_vuln.strata`/`cwe_79_hardened.strata`,
  `pii_vuln.strata`/`pii_hardened.strata`, `lint_vuln.strata`/
  `lint_hardened.strata`, ...): the vuln fixture fires every rule in the
  family from one small model; the hardened fixture discharges every one
  of them. Loaded by `test_litmus_<category>.py::_load_model` in
  `tests/unit/strata/`, one test module per family.
- `design/litmus/*.strata` -- larger, product-shaped scenario models
  (`payments.strata`, `chirp.strata`, `tube.strata`, `audit_vuln.strata`/
  `audit_hardened.strata`, `deploy_secret.strata`) used as end-to-end
  "naive surface goldens" -- realistic systems, not minimal rule-firing
  cases, exercised by `tests/unit/strata/test_litmus_surface.py` and
  friends.

## Add-an-entry recipe (new litmus pair for a new catalog family)

1. Write `<family>_vuln.strata` under `tests/unit/strata/litmus/`: the
   smallest model that fires every rule the new family defines (mirrors
   `cwe_79_vuln.strata`'s minimality -- one flow, one node, exactly enough
   to trip each rule once).
2. Write `<family>_hardened.strata`: the SAME model with every fired
   obligation discharged (a boundary added, a claim asserted/assumed, an
   attr declared) -- never a different, unrelated model; the pairing is
   the point.
3. Write `test_litmus_<family>.py` following the existing modules'
   structure: `_load_model` parses+elaborates each fixture
   (`parse_module` + `elaborate`), one test asserting the vuln model fires
   every rule, one asserting the hardened model discharges every one of
   them.
4. If the family belongs in `frob sys audit`'s exhaustiveness report,
   confirm `_audit.py::evaluate_exhaustiveness` includes the new family's
   evaluator under its own view (mirrors LINT/PII's fixed-view treatment,
   `docs/strata/threat.md`).

## Drift-locks that fire

- No dedicated `frob check` gate ties a catalog family to a required
  litmus pair -- litmus coverage is enforced by the test module existing
  and being collected (an ordinary pytest presence, not a graph-level
  obligation). A new catalog family (e.g. a new CWE weakness) does NOT
  require a NEW litmus pair per se -- it can join an EXISTING family's
  fixture (a new `WeaknessEntry` added to `CWE_CATALOG`'s existing
  `cwe_79_vuln.strata`-style coverage would need that fixture extended,
  not a new file) unless it needs its own minimal model to fire cleanly.
- Both fixtures parse through the REAL parser (`strata-core`'s
  `parse_module`) -- a fixture with a syntax error the parser rejects
  fails the test at load time, which is itself part of the coverage
  guarantee (litmus fixtures are never hand-constructed `KernelModel`
  objects that could drift from what the parser actually accepts).

## Worked example

`pii_vuln.strata`/`pii_hardened.strata` (T-0154) is the newest pair: the
vuln fixture is a collection flow into a `carries "identifier.email"`
store with no protection claim, no retention/erasure, and a mislabeled
downstream flow, firing PII002/PII003/PII004; the hardened fixture adds an
assumed `pii:PROTECTION:f_collect` claim, a revocation-edge flow, and
relabels the downstream flow `Pii` -- discharging all three. Both round-
trip through `test_litmus_pii.py`, the same T-0145 discipline
`cwe_79_vuln.strata`/`cwe_79_hardened.strata` established.

## Common mistakes

- Building the hardened fixture as a DIFFERENT model instead of the vuln
  fixture with fixes layered on -- this breaks the pairing's value (proof
  that discharge, not a different scenario, is what silences the rule).
- Forgetting PII001-style rules that have NO discharge shape (a malformed
  category tag is just wrong, not assumable) -- those rules have no
  litmus pair at all by design; their coverage lives in a plain unit test
  against a hand-built `KernelModel` instead (see `test_pii.py`). Do not
  force a litmus pair onto a rule family with no discharge concept.

## See also

- `docs/strata/threat.md#litmus-coverage-every-catalog-entry-fires-from-real-source-t-0145`
  -- the full litmus coverage design rationale.
