## Done report

Changed:
- src/frob/arch/_python.py::_CHECK_REGISTRY_NAME_RE (new) -- matches a bare
  name of the shape `check_[a-z_]+` OR `run_[a-z_]+_checks`.
- src/frob/arch/_python.py::_is_check_registry_family (new) -- True when
  every member of a same-signature group matches
  `_CHECK_REGISTRY_NAME_RE`, mirroring `_is_dispatch_family`/
  `_is_language_parity_family`'s style: name/structure only, never raw
  text proximity.
- src/frob/arch/_python.py::_check_abstraction_opportunities -- added
  `_is_check_registry_family(members)` as a third skip alongside the
  existing dispatch-family/language-parity-family exclusions.
- tests/unit/test_arch.py::TestCheckRegistryExclusion (new, 3 tests):
  a check_*+run_*_checks group is not flagged; a non-registry-named group
  with the identical shape still flags; the helper's regex matches both
  name shapes directly.

Measurement note (methodology diverged from the ticket's literal proposal,
disclosed): the ticket proposed `^check_[a-z_]+$` alone. Empirically
re-measuring `frob arch src/frob/arch --json` before/after showed the real
27-member `(NormalizedModule) -> list[ArchSuggestion]` group is ~20
`check_*` detectors PLUS 7 `run_*_checks` per-family aggregators
(`run_smell_checks`, `run_srp_checks`, `run_typedesign_checks`,
`run_fallibility_checks`, `run_logging_checks`, `run_lsp_checks`,
`run_isp_checks`) -- an aggregator has the exact same shape as the
detectors it concatenates results from, and `all(...)`-based full-group
matching means a check_*-only regex leaves the group unexcluded (7 of 27
members don't match, so the group still flags). Broadened the regex to
accept both name shapes; this is still purely name/structure-based (no
raw text proximity), matching T-1068's own style precedent.

Re-measured per T-1068's before/after methodology:
- `frob arch src/frob/arch --json` abstraction-opportunity count:
  19 -> 18 (with the regex still `^check_[a-z_]+$` only, count stayed 19
  -- the group survived unexcluded; verified this BEFORE broadening).
- `diff` of the two runs' abstraction-opportunity findings shows EXACTLY
  one group removed: the 27-member `(NormalizedModule) ->
  list[ArchSuggestion]` group in `_layering.py` (check_no_di_construction,
  check_boolean_flag_param, run_smell_checks, run_srp_checks, ... all 27
  named per the registry convention). Every other of the 18 remaining
  groups is byte-identical across both runs -- confirmed via diff, not
  spot-checked.

Evidence:
- `tests/unit/test_arch.py::TestCheckRegistryExclusion::test_check_and_run_checks_names_not_flagged`
- `tests/unit/test_arch.py::TestCheckRegistryExclusion::test_non_registry_named_group_still_flagged`
- `tests/unit/test_arch.py::TestCheckRegistryExclusion::test_check_registry_regex_matches_both_shapes`
- `pytest tests/unit/test_arch.py -q`: 260 passed, 0 failed (full file, not
  just the new class -- confirms no regression to the existing
  `_is_dispatch_family`/`_is_language_parity_family` exclusion tests or any
  other arch check).

Filed: none new (T-1143, filed during T-1035, still covers the
parse.rs->parse/mod.rs archive-evidence residue below).

Gates: `uv run frob check --ticket T-1112 --only gates-fast` shows 26
errors, ALL pre-existing per `git diff main --stat` (zero touch) against
every flagged file -- the identical 26 disclosed in T-1035's Done report
(23 COV003 archive-evidence residue already tracked as T-1143, 1 COV001 on
src/frob/gates/_tracked_files.py, 1 INV006 on
src/frob/app/ticket_runner/_mutate.py, 1 TICK006 on T-1114's phantom
draft). No finding touches src/frob/arch/_python.py or
tests/unit/test_arch.py.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestCheckRegistryExclusion::test_check_and_run_checks_names_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCheckRegistryExclusion::test_non_registry_named_group_still_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCheckRegistryExclusion::test_check_registry_regex_matches_both_shapes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 15 error(s), 772 warning(s), 424 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:295, INV006@src/frob/app/ticket_runner/_mutate.py, SELFAUDIT001@design, TICK006@tickets.md
