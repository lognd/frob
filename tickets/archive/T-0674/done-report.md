## Done report

Adjudicated all 6 RECONCILIATION.md finding (e) tension CWEs. In every
case the pre-existing weaknesses.yaml/cwe-1000-registry.md disposition
(recorded by T-0384) is AFFIRMED as structurally correct; the defect was
security-corpus.md's own "NOT in repo -- gap" framing, which conflated
"absent from the 2023-pinned `_threat.py` CODE catalog" with "absent from
the DOCUMENTATION registry" -- two different denominators. No
weaknesses.yaml disposition changed value; each entry got an inline
`# T-0674 adjudication: AFFIRMED ...` comment recording the ruling and
rationale (schema-safe -- YAML comments, ignored by the loader, verified
by a fresh `yaml.safe_load` still returning all 944 entries).

Per-CWE ruling:

- CWE-120 (Classic Buffer Overflow): AFFIRM `duplicate-of:CWE-787` --
  structurally an Out-of-bounds Write instance; not a code-catalog gap.
- CWE-121 (Stack-based Buffer Overflow): AFFIRM `duplicate-of:CWE-119` --
  a CWE-119 (memory-buffer-bounds) variant per CWE-1000's own child
  listing.
- CWE-122 (Heap-based Buffer Overflow): AFFIRM `duplicate-of:CWE-119` --
  same rationale as CWE-121.
- CWE-200 (Exposure of Sensitive Information): AFFIRM
  `out-of-scope:authn-authz-boundary-predicate` -- requires a role/authz-
  boundary model the kernel does not have.
- CWE-284 (Improper Access Control): AFFIRM
  `out-of-scope:authn-authz-boundary-predicate` -- same missing-model
  case as CWE-200/285/863.
- CWE-770 (Allocation of Resources Without Limits): AFFIRM
  `out-of-scope:memory-model` -- resource-budget-vs-input-size has no
  kernel model outside the unrelated T-0066 latency budget.

security-corpus.md updated to match: the six Top-25 table rows now cite
`registry-dispositioned: <disposition> (weaknesses.yaml) -- ... not a
code-catalog gap (T-0674)` instead of "NEW to 2025 list; NOT in repo --
gap" / "NOT in any repo catalog -- gap"; the section-1a "Finding"
paragraph gained a T-0674 adjudication subsection with the ruling table
above; the section-8 Coverage Summary row for "CWE Top 25 (2025)" moved
these six from the Gap column (5+1) into the Advisory column (12 -> 18)
and zeroed the Gap column, with a note pointing at the ruling.
`cwe-1000-registry.md` needed no change -- it was already the correct
side of the tension. `cross_refs: [security-corpus:cwe-top25-2025]` was
already present on all six weaknesses.yaml entries from T-0384; verified
unchanged and still present.

## Done report

Changed:
- docs/design/registry/weaknesses.yaml (CWE-120/121/122/200/284/770 entries -- annotated, disposition/cross_refs unchanged)
- docs/design/security-corpus.md (Top-25 table rows for the same 6 CWEs, section-1a finding paragraph, section-8 coverage summary row)

Evidence: tests/test_registry_reconciliation_weaknesses.py::TestExhaustivenessGateOverRealWeaknesses::test_no_weaknesses_violations (bound to acceptance index 0; 8/8 tests in the file pass, `uv run pytest tests/test_registry_reconciliation_weaknesses.py -q` green). A standalone consistency check (yaml.safe_load-based, verifying all 6 entries carry a duplicate-of/out-of-scope disposition + the security-corpus cross_ref, and that the corresponding security-corpus.md table rows no longer contain "NOT in repo -- gap"/"uncataloged" and do contain "registry-dispositioned") passed clean; not registered as CLI evidence because T-0674 is kind=security (code kind), which only accepts pytest node ids, not --evidence-cmd (docs-kind only).

Filed: none (no out-of-scope work found; cwe-1000-registry.md required no edit).

Gates: `uv run --frozen frob check --ticket T-0674 --only gates-fast` -- 5 pre-existing errors (DOC001 docs/audits/frob-blindspots-2026-07-23.md, SCOPE001 uv.lock [worktree tooling drift, reverted to main's uv.lock, now 0 diff], TEST010 x2 in tests/test_perf_loop_invariant_effect_lock.py and tests/system/test_spawn_budget.py, TICK006 T-0766 phantom-filing warning) -- all confirmed pre-existing on main (`git diff main --stat` shows only weaknesses.yaml/security-corpus.md/tickets.md touched by this ticket; none of the 5 error files appear in that diff). `--only lint` and `--only static` both clean (frob-exports/frob-dup/frob-arch findings are pre-existing repo-wide debt, unaffected by this change).

### Changed
```
 docs/design/registry/weaknesses.yaml | 26 +++++++++++++++++
 docs/design/security-corpus.md       | 56 ++++++++++++++++++++++++++----------
 tickets.md                           |  2 +-
 3 files changed, 68 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_registry_reconciliation_weaknesses.py::TestExhaustivenessGateOverRealWeaknesses::test_no_weaknesses_violations` (pytest node id, verified passing when recorded)
