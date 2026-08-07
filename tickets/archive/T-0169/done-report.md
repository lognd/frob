## Done report

Root cause: WIRING BUG, confirmed by repro. `_selfconform.py::check_self_conformance`
handed `bind_code`'s Python-only `CodeBinding` (`_code_binding.py::_sorted_py_files`
walks only `*.py`, by design -- it also backs Python-import conformance) straight to
EVERY join that reconciles observed vs. declared capabilities. A `.ts`/`.js`/`.rs`/
`.c-cpp` file was therefore never even a KEY in `binding.owner`, so neither
`scan_file_capabilities` (extended kinds/SYS101) NOR `check_capability_conformance`
(core net/fs-write/exec kinds/SYS100) was ever called on it -- and the empty
directory-ownership set also produced a spurious SYS102 "unmodeled code" for any
directory whose only files were non-Python.

FIX ROUND 1 (extended kinds + SYS101 only): added `_capability_binding`, a superset
of `bind_code`'s binding covering every `language_for`-recognized extension, and
wired it into `_extended_kind_violations`/`_stale_design_violations`. Repro at the
time: a `.ts` file with `fetch(...)` + `localStorage.setItem(...)` went from 0
violations to correctly firing SYS100 for `fetch_url`/`client_storage`.

REVIEWER REJECT (round 1): correctly caught that `_core_undeclared_violations`
(net/fs-write/exec, delegated to THREAT004's `check_capability_conformance`) and
`_unmodeled_violations` (SYS102) were STILL being handed the raw Python-only
`binding`, not the `_capability_binding` superset -- so a `.ts` `axios.get(...)`
or `.rs` `Command::new(...).spawn()` still produced ZERO SYS100 and a SPURIOUS
SYS102, i.e. the exact same class of bug survived for the raw net/exec/fs-write
kinds the logand.app pilot most needs caught. My round-1 rationale ("Python-
import-syntax-specific by design") was WRONG for this delegate: verified by
reading `_effects.py::_line_effects`, which calls `language_for`/`_PATTERNS`
directly -- there is no Python-specific parsing anywhere in
`check_capability_conformance`'s path; only `bind_code` itself (the binding step,
not the capability-conformance check) needs Python's import syntax specifically.

FIX ROUND 2 (this round): `check_self_conformance` now passes `capability_binding`
(the superset) to ALL FOUR joins -- `_core_undeclared_violations`,
`_extended_kind_violations`, `_stale_design_violations`, AND `_unmodeled_violations`.
`bind_code`'s raw Python-only binding is still computed and is still the ONLY input
to `bind_code` itself (unrelated to this fix, stays Python-import-syntax-specific
by design) and to `_capability_binding`'s own construction (it extends that binding,
doesn't replace its Python-file entries). Repro confirmed both new cases: a `.ts`
`axios.get(...)` fires SYS100 `net` with no spurious SYS102; a `.rs`
`Command::new("ls").spawn()` fires SYS100 `exec` with no spurious SYS102. Design
choices reconfirmed unchanged: `_PACKAGE_ROOT = "src/frob"` (SYS102 scope, still
correct -- unrelated to language), and deny-by-default `AmbiguousCodeBinding` on a
multi-node glob match (unchanged in `_capability_binding`).

Fix (both files in scope):
- `src/frob/vet/_capability.py`: added public `SCANNED_LANGUAGES` (frozenset of
  every language `_EXT_LANGUAGE` maps at least one extension to) so a drift-lock
  test can assert self-conformance's scanned-language set equals
  `_capability_registry.LANGUAGES` without hand-duplicating either list.
- `src/frob/strata/_selfconform.py`: added `_sorted_capability_files` (walks every
  file under root with a `language_for`-recognized extension) and
  `_capability_binding` (extends `bind_code`'s Python-only `CodeBinding` with every
  OTHER capability-scannable-language file, bound by the SAME `code=` glob
  convention via `_node_code_globs`, reused not reimplemented; deny-by-default
  `AmbiguousCodeBinding` on a multi-node glob match, same as `bind_code`).
  `check_self_conformance` builds this superset binding once and passes it to ALL
  FOUR violation-collecting functions (`_core_undeclared_violations`,
  `_extended_kind_violations`, `_stale_design_violations`, `_unmodeled_violations`),
  so every registry-covered language is reconciled by every rule, not just
  Python by some of them.

Changed:
  src/frob/vet/_capability.py::SCANNED_LANGUAGES
  src/frob/strata/_selfconform.py::_sorted_capability_files
  src/frob/strata/_selfconform.py::_capability_binding
  src/frob/strata/_selfconform.py::_core_undeclared_violations (binding source changed, round 2)
  src/frob/strata/_selfconform.py::_observed_extended_kinds_by_node (binding source changed, round 1)
  src/frob/strata/_selfconform.py::_observed_all_kinds_by_node (binding source changed, round 1)
  src/frob/strata/_selfconform.py::_unmodeled_violations (binding source changed, round 2)
  src/frob/strata/_selfconform.py::check_self_conformance (wires _capability_binding into all four joins)

Evidence (frob:tests-bound, tests/unit/strata/test_selfconform.py, 20 tests total):
  TestNonPythonLanguageWiring.test_typescript_undeclared_capability_fires
  TestNonPythonLanguageWiring.test_typescript_undeclared_capability_discharges_once_declared
  TestNonPythonLanguageWiring.test_typescript_stale_design_fires
  TestNonPythonLanguageWiring.test_sorted_capability_files_includes_typescript
  TestCoreUndeclaredInterfaceNonPython.test_typescript_core_net_undeclared_fires
  TestCoreUndeclaredInterfaceNonPython.test_typescript_core_net_discharges_once_declared
  TestCoreUndeclaredInterfaceNonPython.test_rust_core_exec_undeclared_fires
  TestCoreUndeclaredInterfaceNonPython.test_rust_core_exec_discharges_once_declared
  TestLanguageCoverageDriftLock.test_scanned_languages_equals_registry_languages
  TestLanguageCoverageDriftLock.test_language_for_is_consistent_with_scanned_languages
The four new round-2 tests each assert both the SYS100 fire AND the absence of a
SYS102 for the same directory (the spurious-misreport the reviewer flagged). All
prior SYS100/SYS101/SYS102/drift-lock/real-gate-green tests in the same file still
pass unmodified.

POST-MERGE UPDATE (merging main a second time, after T-0181 closed): re-ran the
full verification pass. `TestRealGateGreen::test_repo_design_and_declarations_are_
self_conformant` (the real-repo-tree assertion) now FAILS: `SYS100 'html_render'
observed but not declared` on the `vet` node. Root-caused and DELIBERATELY NOT
fixed here: T-0181 added new `html_render` needles (`innerHTML`,
`dangerouslySetInnerHTML`) as literal string DATA inside
`src/frob/vet/_capability_registry.py` itself, so scanning that file's own text
self-matches `html_render` -- the exact documented self-match false-positive class
`vet.scan_directory_capabilities` already excludes via a private path check, but
`_selfconform.py`'s file-level SYS100/SYS101 joins scan node-owned files directly
and never got that exclusion. I prototyped exposing the exclusion to
`_selfconform.py` and REVERTED it: doing so correctly kills the false SYS100, but
then produces four NEW SYS101 "stale design" findings (eval/exec/deserialize/sql
on `vet`) -- proving `design/frob.strata`'s `vet` node `may` list was silently
calibrated against this same self-match noise as if it were real signal. Properly
fixing this needs `design/frob.strata` changes (recalibrating `may` against
genuine, non-self-match usage), which T-0169's `scope` explicitly excludes.
CONFIRMED this failure is 100% pre-existing and independent of every change in
this ticket: `git fetch`+checkout of unmodified `main` tip (3135c5c) and running
`TestRealGateGreen` there directly reproduces the identical failure with zero of
my changes present. Not Filed T-draft-e1beb2a8 (never refiled) (self-match + design recalibration)
and T-draft-e1beb2a8 (never refiled)'s sibling T-draft-a8e0354d (never refiled) (the tickets-archive.md splice,
below) to track both discoveries; this ticket's own diff does not touch
`design/frob.strata` or the self-match exclusion.

Not Filed:
- T-draft-a8e0354d (never refiled): `tickets-archive.md` stale T-0169 duplicate from an unrelated
  ledger-conflict splice on `main` (see NOTE below).
- T-draft-e1beb2a8 (never refiled): self-conformance `TestRealGateGreen` red on the real repo tree
  (html_render self-match on `_capability_registry.py`; needs both a
  `_selfconform.py`/`_capability.py` exclusion AND a `design/frob.strata` `may`
  recalibration for the `vet` node).
(fix itself stayed inside declared scope; T-0158's own coverage matrix and
T-0181's `_capability_registry.py` were not touched by me.)

Gates: `uv run frob check` -- the only non-waived findings are a pre-existing
campaign-wide TEST006 coverage-stamp warning (never run `make coverage` per
standing instruction) and a pre-existing COV003 on ticket T-0168's evidence id,
confirmed present on merged `main` BEFORE this ticket's changes via `git stash`
(unrelated to this ticket's scope). `uv run frob test --base main`: the python
suite is RED specifically on `TestRealGateGreen`, confirmed pre-existing on
unmodified `main` tip (see POST-MERGE UPDATE above) and NOT a regression from
this ticket's diff -- every other selected test (all 20 in
`test_selfconform.py` plus the vet hook-mode smoke test) passes, including all
four round-2 core-path regression tests. `ruff format --check .` clean.

Not closing this ticket per workflow instructions (implementer records evidence and
Done report; closing/verification is a separate step).

NOTE (ledger integrity, found while merging main, out of scope to fix here): `tickets-archive.md` on `main` (post-merge, unmodified by me -- outside this ticket's `scope`) contains a STALE, INCORRECT duplicate of this exact T-0169 block (`state: queued`, no Done report, no evidence) -- it was silently spliced into the archive by an unrelated ledger-conflict merge (same incident class the agent playbook's "ledger-conflict splice guidance" warns about), NOT a real close. This live `tickets.md` entry (in-progress, with the Done report above) is the authoritative one; the archive's stray copy needs a follow-up ticket (scope: tickets-archive.md) to delete it so a future `frob ticket` listing doesn't show two T-0169 records in conflicting states.
