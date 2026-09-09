## Done report

Survey (kind=docs, no code changes -- ticket declared no_scope via
`frob ticket scope T-4333 --declare-no-scope`).

### Inventory of hand-maintained membership lists surveyed

Ranked by consequence of drift, not by count.

1. **`_CACHEABLE_PROCESS_GATES`** (src/frob/gates/__init__.py, T-1445) --
   must stay a subset of `_build_process_jobs`'s cacheable entries.
   NO completeness check exists anywhere (grepped src/frob and tests/ for
   any assert or set-comparison against `_build_process_jobs`/`_ALL_GATES`;
   none found), unlike its neighbors `_CANONICAL_GATE_ORDER` and
   `_GATE_STAGE_GROUPS`, which both carry an import-time
   `assert set(...) == _ALL_GATES`. Drift is a SILENT GAP: a new cacheable
   process-job gate omitted here never crashes, never fails a test, never
   shows in CI -- it just permanently loses whole-tree caching for that one
   gate. Not correctness-affecting, but exactly the "list A must track list
   B by memory" shape named in the parent ticket, landing on perf instead
   of red CI. Currently undetected. Membership looks fully derivable from
   `_build_process_jobs` plus a small documented-reason exemption list
   (mirroring `_COMMITTED_DIFF_GUARDS`'s `exemption_reason` field, #2
   below). FILED: T-4361.

2. **`_COMMITTED_DIFF_GUARDS`** (src/frob/tickets/_land.py, T-1940) --
   registers every diff-content-reading `_check_*` land guard alongside its
   post-mutation reverification twin or a documented exemption reason.
   Six of ten `_check_*` functions in `_land.py` are registered; the other
   four (`_check_tdd_order`, `_check_uncommitted_waive_deletions`,
   `_check_committed_waive_deletions`, `_check_unowned_deletions`) are not,
   but that is because they do not read committed diff content (the T-1932
   hazard this registry exists for) -- NOT unaccounted omissions.
   Drift IS caught: `tests/ticket_land_suite/test_verify_reset.py`'s
   `TestCommittedDiffGuardRegistryCompleteness` enforces both directions
   (every diff-reading call site is registered; every registration still
   has a real call site) plus that registered twins are actually wired in.
   This is the T-4336-adjacent-but-different shape: a HAND-MAINTAINED list
   verified by a STRUCTURAL TEST rather than DERIVED outright (an
   import-time assert cannot easily replace it here, since "reads
   committed diff content" is a semantic property of a function body, not
   a registrable declaration at definition time). Genuinely fine as-is:
   the test is the correct enforcement mechanism for this shape, and the
   registry's own `exemption_reason` field already forces an explicit,
   reviewed decision for every diff-reading guard that does NOT get a
   post-mutation twin. No ticket filed.

3. **`_KNOWN_GATE_RULES`** (src/frob/gates/_waive.py) -- the registry of
   every live rule id a `frob:waive`/gate message may cite. Rule ids are
   free-text literals scattered across gate modules, not decorator- or
   enum-registered, so hand-maintaining the registry is the only option;
   what matters is drift detection, which is a REAL GATE
   (`frob.gates._rule_id_scan`, wired into every `frob check` run) that
   fails loud (see `tests/gates/test_rule_id_scan_branches.py`,
   `tests/gates_suite/test_sys.py`) the moment a rule id used in src/ is
   missing from the registry. This is hand-maintenance with live, red-CI
   enforcement, not a silent-gap shape -- correctly curated as designed,
   confirmed by its own module docstring. No ticket filed.

4. **`_KIND_TO_COMMIT_TYPE`** (src/frob/tickets/_land_merge.py) -- maps
   `TicketKind` values to conventional-commit type prefixes for land
   commit messages. `.get(ticket.kind.value, "chore")` has a safe default,
   so a `TicketKind` added without a matching entry here does not crash or
   silently corrupt state -- it just mislabels that kind's land commits as
   "chore:" instead of the more accurate type. Real but low-consequence
   drift (cosmetic commit-message prefix only); the ticket-kind enum
   changes rarely and the failure mode is visible in the commit itself.
   Judged not worth a follow-up ticket given the consequence -- noted here
   per the survey's own instruction to say when a list is fine as-is.

5. **`_TIER_RANK`** (src/frob/tickets/_setters.py) and **`_STATE_RANK`**
   (src/frob/tickets/_land_ledger_merge.py) -- each maps every member of a
   small, closed enum (`TicketTier`: 3 members; `TicketState`: 6 members)
   to a totally-ordered rank used for parent/child and land-ordering
   checks. Both enums change extremely rarely (adding a new ticket state
   or tier is itself a significant, rare design decision, not routine
   feature work), and a missing entry would raise `KeyError` immediately
   on first use rather than silently degrading -- fail-loud-by-construction,
   not fail-silent. Deliberate curation, fine as-is.

6. **`_NESTED_MARKER_FILES`/`_NESTED_SOURCE_SUFFIXES`** (src/frob/check/
   __init__.py) -- independent marker-file and source-suffix heuristics
   for `_detect_nested_project_type`. Neither is required to stay in sync
   with the other or with any registry elsewhere; each is its own
   self-contained heuristic table. Fine as-is.

7. **`_TOOL_ONLY_STAGE_GROUPS`/`_TOOL_STAGES`** (src/frob/check/__init__.py)
   -- the "lint"/"static" stage-group members are frob's own fixed,
   rarely-changing external tool names (ruff, ty, cycle, dup, arch, bind,
   exports), explicitly documented in-line as "never gates, so safe to
   hand-list directly" -- contrasted against the gates half of
   `_STAGE_GROUPS`, which T-4336 already fully derives via the
   `_GATE_STAGE_GROUPS`-driven `_stage_groups()` PEP 562 hook (confirmed
   read at src/frob/check/__init__.py:1337-1396: an import-time assert in
   `frob.gates` makes the eight-incident "_ALL_GATES but never added to
   a _STAGE_GROUPS member" omission structurally impossible now, with the
   pre-existing structural test kept as an independent second proof per
   the function's own docstring). This confirms T-4336's fix is complete
   and this specific starting point needs no further ticket.

8. **`tests/conftest.py`'s heavy-scan lists** -- confirmed T-4329's fix is
   in place and is the only membership-affecting list left in the file
   (`_SELF_SCAN_HEAVY_NAME_SUBSTRINGS` alongside
   `_SELF_SCAN_HEAVY_FIXTURE_NAMES`, fixture-closure-derived per that
   ticket). No further action.

9. **`_DISCLOSURE_PHRASES`** (src/frob/tickets/_reporting.py, T-1648) and
   **`_TIER_A_GENERATED_SUBHEADINGS`** (same file, T-2638) -- natural-
   language heuristic trigger lists (English disclosure phrases; frob's
   own fixed literal subheading strings). Both carry explicit docstrings
   stating why they are deliberately hand-typed rather than derived
   (generous-trigger-by-design for the phrases; an exact-title allowlist
   immune to rewording for the subheadings). Not derivable from usage --
   there is no code-level "usage" a natural-language phrase list could be
   derived from. Fine as-is.

### Gates/tickets already-closed instances confirmed

- `_ALL_GATES` <-> `_CANONICAL_GATE_ORDER`: bound by
  `assert set(_CANONICAL_GATE_ORDER) == _ALL_GATES` (src/frob/gates/
  __init__.py:7011).
- `_ALL_GATES` <-> `_GATE_STAGE_GROUPS`: bound by
  `assert set(_GATE_STAGE_GROUPS) == _ALL_GATES` (same file:7115), which
  is exactly the mechanism `frob.check._stage_groups()` (T-4336) derives
  the real `_STAGE_GROUPS` from -- confirmed this closes all eight
  incident comments the parent ticket's Description named.

Changed: none (survey only; no_scope declared per above)
Evidence: `uv run frob check --ticket T-4333` -- gate-summary 0 errors,
  4784 warnings, 0 unresolved, 957 waived (repo-wide gate counts, not
  ticket-scoped per gate:scope-note -- expected for a no-scope ticket)
Filed: T-4361 (Derive _CACHEABLE_PROCESS_GATES completeness check)
Gates: frob check --ticket T-4333 clean, 0 errors

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 4784 warning(s), 957 waived
- error-findings: none (measured, zero errors)
