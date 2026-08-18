---
id: T-2469
title: LEXCHECK001 widening surfaced 5 real symref-less lexical deciders in vet/_supplychain.py
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/vet/_supplychain.py
- tests/unit/gates/test_lexical_selfcheck.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_supplychain_lexcheck001_backlog_is_empty_t2469
designated_repro_test: tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_supplychain_lexcheck001_backlog_is_empty_t2469
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 22a4e5530d9fd622e42888a1c61fd73862f956a1
---
T-2466 widened LEXCHECK001's scanned scope from `src/frob/gates/**` to
`DETECTOR_PACKAGE_ROOTS` (gates/, vet/, strata/, check/ -- measured by
which packages construct `Violation(...)` objects at all). That widening
immediately surfaced 5 REAL, previously-invisible LEXCHECK001 findings
that were always there, just never scanned:

    src/frob/vet/_supplychain.py:52   _pyproject_unpinned_violations
    src/frob/vet/_supplychain.py:91   _package_json_unpinned_violations
    src/frob/vet/_supplychain.py:122  _cargo_toml_unpinned_violations
    src/frob/vet/_supplychain.py:170  _python_install_artifact_violations
    src/frob/vet/_supplychain.py:212  _unpinned_ci_action_violations

Each decides from `re.search`/`re.match`-shaped parsing of a manifest
file (`pyproject.toml`, `package.json`, `Cargo.toml`, a CI workflow) and
builds a `Violation` with no `symref=`.

THIS IS OUT OF T-2466's OWN SCOPE (`src/frob/gates/_lexical_selfcheck.py`
and its own test/doc, not `src/frob/vet/_supplychain.py`) -- T-2466 filed
this rather than fixing it inline, mirroring the T-2348/`_wire001_cli_
dest_violations` precedent this file's own test docstring already cites
for the identical situation.

WHAT TO DECIDE, per docs/design/gate-semantics-classification.md's own
class-(a)-vs-(b) split:

  - Class (b), genuinely lexical: these manifests are TOML/JSON/YAML --
    structured formats with real parsers already in the stdlib
    (`tomllib`, `json`) or already a project dependency. Regex-parsing a
    structured format when a real parser is available is arguably a
    DIFFERENT instance of "parse, don't grep" (this repo's own standing
    rule) rather than a case where "the subject genuinely is text" the
    way SEC001's entropy scan or EXCL001's path-glob question are. Worth
    checking whether switching to `tomllib.load`/`json.loads` and walking
    the resulting structure removes the regex dependency entirely, which
    would fix this at the root rather than allowlist it.
  - Class (a), needs a symref: if a real parse is not practical (e.g. the
    CI-workflow-unpinned-action check, which may need to stay closer to
    line-oriented text), add `symref=` to each `Violation` construction
    site (attach it to the manifest FILE's own resolvable identity, or
    the enclosing scan function) and it stops being a LEXCHECK001 hit on
    its own terms, same fix shape T-2348 used for WIRE001.

Either fix removes these 5 from LEXCHECK001's finding set. Until this
lands, T-2466's own `test_every_known_detector_package_module_stays_clean`
test asserts against this KNOWN, ticket-tracked backlog by name (not a
blind `== []`) so a genuinely NEW offender anywhere else still fails
loudly -- update that assertion in the SAME change that fixes this
ticket, so the test goes back to asserting a true empty set.