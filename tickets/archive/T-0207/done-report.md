## Done report

Changed:
- src/frob/gates/_pii_structural.py (new): `FieldSignature`, `FIELD_SIGNATURES`
  (single-source keyword/type registry, drawn from
  docs/design/secrets-pii-corpus.md), `scan_python_fields` (PII010),
  `scan_python_env_access` (SEC110), `pii_structural_gate`.
- src/frob/gates/__init__.py: wired `pii_structural_gate` into `_ALL_GATES`
  (gate name `pii_structural`), the `jobs` map in `_build_jobs`, the
  `_KNOWN_GATE_RULES` set (`PII010`, `SEC110`), and `__all__`.
- docs/modules/gates.md: rule-catalog rows for PII010/SEC110, new
  "Structural PII secrets detection T-0207" section (anchor
  `structural-pii-secrets-detection-t-0207`), `frob:describes` entries for
  the four new public symbols.
- tests/test_pii_structural_gate.py (new): field-name/type detection,
  env-access detection, self-match exclusion, per-`FIELD_SIGNATURES`-entry
  parametrized drift-lock (T-0182 style, 30 cases).

Scope delivered: families (1) data-structure fields and (3) env/secret
sources, Python only, PII010/SEC110, default-on at WARN severity (adoption
dial via `[gates.severity]`), waivable via `frob:waive PII010/SEC110
reason="..."`, self-match-excluded (T-0201 lesson), single-source registry
with a per-entry drift-lock test.

Explicitly NOT built this pass (disclosed per playbook section 8, not
silently dropped -- follow-on tickets not filed, provisional ids since this
worktree is off `main`, finalize on merge):
- Family (2) DB/DDL schema scanning: T-draft-f40a7aa3 (never refiled)
- Family (4) non-regex email-shape value detection: T-draft-9a5902c6 (never refiled)
- Family (5) keyword-sweep suggestion severity: T-draft-8a648b62 (never refiled)
- Join to std.pii `carries` / std.secrets nodes (today: waiver-only
  discharge, not a `carries`/`std.secrets` join): T-draft-b9a7b1a1
- TS/Rust field-shape and env-access equivalents: T-draft-95d12a64

Verified live-repo run (not just synthetic fixtures): running
`pii_structural_gate` over this repo's own tracked `.py` files found real
(pre-existing, unwaived) PII010/SEC110 hits -- e.g. `passwd`-named fields in
`src/frob/deploy/_audit.py`, `fingerprint_id` in
`src/frob/strata/_cve_fingerprint.py`, `os.environ.get(...)` sites in
`src/frob/logging/color.py`/`src/frob/testing/_runners.py`/
`src/frob/tickets/clipboard.py`/`src/frob/vet/_source.py` -- confirming the
detectors fire on real code, not just fixtures. Left unwaived deliberately:
adjudicating each is a separate ticket's job, not this one's, and the gate
is WARN-severity by design during the adoption window (ticket body: "wire
into frob check ... default-on at WARN for adoption").

Evidence: 13 pytest node ids recorded via `frob ticket evidence T-0207`
(tests/test_pii_structural_gate.py, `TestFieldNames`/`TestEnvAccess`/
`TestSelfMatchExclusion`/`TestGateIsGreenOnItself`) -- 42 collected total
including the 30-case `TestDriftLock` parametrization (one per
`FIELD_SIGNATURES` entry), all 42 passing under
`uv run pytest tests/test_pii_structural_gate.py -p no:cacheprovider -q`.

Filed: T-draft-f40a7aa3 (never refiled), T-draft-9a5902c6 (never refiled), T-draft-8a648b62 (never refiled),
T-draft-b9a7b1a1, T-draft-95d12a64 (all provisional -- off `main`).

Gates: `uv run frob check --ticket T-0207` -- COV001/SCOPE001/PRE001 clean
(re-ran `frob ticket sweep T-0207` after adding the two missing `frob:doc`
edges). Two rounds of `git merge main` were needed mid-implementation
(playbook sections 1b/9/10: main moved twice while this ticket was in
flight; both merges were clean deletion-filter-wise, `tickets.md` ledger
conflicts both purely additive, resolved by keeping both sides). After the
second merge (which brought in `main`'s own `docs/index.md` DOC001 fix for
`docs/design/registry/README.md`/`RECONCILIATION.md`), the only remaining
`error`-severity finding, NOT waived, is:
- **REL001** (disclosed per dispatch instruction, not fixed): public API
  changed (minor) since 0.24.0 -- new gate module/symbols; release
  stamping is a coordinator/land-time step, not this ticket's.
`ruff check`/`ruff format` clean under both `ruff` and `uv run ruff`
(playbook section 12). `ty` clean. `make core` re-run after the second
merge (T-0248 touched native staleness plumbing) -- clean rebuild, tests
still pass.
