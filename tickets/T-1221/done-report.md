## Done report

Delivered (this dispatch): the rust capability-scan resolver kernel,
`frob_core.scan_python_capabilities(source: bytes) -> (candidates,
unresolved, spans)`, mirroring `frob.vet._capability_python`'s import-
table / position-aware scope-shadowing / scope-local alias-copy-
propagation resolution natively via `tree-sitter`, including the two
T-1626 evasions the coordinator's own brief named explicitly
(`functools.partial(dangerous, ...)` and literal-string/integer-keyed
dict/list container-alias dispatch).

1. frob-core/src/capability_python.rs (new file, ~880 lines): the full
   resolver -- import table (`py_import_table`, `bind_import_statement`/
   `bind_import_from_statement`), position-aware scope-bound shadowing
   (`py_scope_bound_names`/`shadowing_scope`, T-0468 parity), scope-local
   alias copy-propagation (`build_alias_table`/`record_alias`, covering
   identifier rebind, attribute rebind, `functools.partial` resolution,
   and dict/list container-alias resolution), and the candidate/
   unresolved walk (`collect_candidates`).

   THE UNRESOLVED REQUIREMENT (the coordinator's stated priority): a
   third return collection, `unresolved: Vec<(usize, usize)>`, flags
   every call site this resolver can SEE is a dynamic-dispatch shape (a
   subscript keyed by a non-literal expression, `handlers[computed](x)`)
   but cannot identify the callee for -- an explicit, loud outcome
   distinct from "no capability observed", never silently folded into
   the empty case. This widens the ticket's own `(candidates, spans)`
   acceptance-criterion floor to a third collection; documented and
   intentional, not a scope departure. Verified directly:
   `test_dynamic_dispatch_is_unresolved_not_silently_dropped` confirms
   the exact call-site span lands in `unresolved`, and that the SAME
   span is genuinely absent from the Python resolver's own candidate
   output too (both paths agree on WHERE resolution stops).

   Three disclosed, narrow deviations from `_python_resolved_candidates`
   (full reasoning in the module's own doc comment): no dangerous-
   priority import tie-break (T-0659, needs the needle registry, which
   this extraction-only kernel deliberately does not consume -- rule
   evaluation stays entirely Python-side, same design line as T-1222's
   arch walk), no `from X import *` wildcard registry fallback (T-0659,
   same reason), no tuple/list destructuring alias (T-0659,
   implementable without the registry but lower-value than the two
   evasions this ticket's own dispatch named -- documented future work).
   All three narrow recall in a specific, named, non-silent way; none
   silently claim parity and then drop behavior.

2. frob-core/src/extract.rs: added `python_non_executable_byte_spans`
   (pub(crate)) -- the BYTE-offset sibling of the T-1220 kernel's own
   LINE-based `comment_spans`/`docstring_spans`, sharing the same parse/
   leaf-walk/docstring-query rather than duplicating it (matches
   `frob.vet._capability_core._non_executable_byte_spans`'s bisect-over-
   byte-offsets contract exactly).

3. frob-core/src/lib.rs: wired `scan_python_capabilities` into the
   `frob_core` `#[pymodule]` (twentieth export).

4. frob-core/frob_core.pyi: typed stub for the new export (never raises,
   verified by `frob check --only ffi_boundary`: 0 errors/warnings).

5. docs/modules/vet.md (Public API) + docs/modules/dup.md (frob-core
   kernel export count) describe the new kernel, the UNRESOLVED design,
   and all three disclosed deviations.

6. tests/unit/test_capability_native.py (new file): 5 tests --
   import/alias/scope-shadowing parity, the two T-1626 evasions'
   parity, the UNRESOLVED requirement's own dedicated test, the never-
   raises contract, and a golden test against this repo's own
   `_capability_python.py` source (byte-identical `candidates`/`spans`
   vs. `_python_resolved_candidates`/`_non_executable_byte_spans`).

7. design/frob.strata: `testsuite` node's `may "fs.write"`/`"fs.read"`/
   `"exec"` declarations extended to cover
   `tests/unit/test_capability_native.py` (SELFAUDIT001 -- the new test
   file writes/reads a tmp fixture and spawns the resolver via a real
   subprocess-shaped call site inside its own fixture text, same as
   T-1220's own precedent for `test_extract_native.py`).

Golden-test proof: `sorted(candidates) == sorted(cp._python_resolved_
candidates(path))` and `tuple(sorted(spans)) == cc._non_executable_byte_
spans(path)`, both asserted directly in the test file (not just an ad hoc
script this time -- committed regression locks), across representative
shapes plus this repo's own `src/frob/vet/_capability_python.py` (the
file the coordinator's own brief pointed at).

FFI gate compliance: `frob check --only ffi_boundary` -- 0 errors, 0
warnings.

COV002 disambiguation (new finding class this portion hit, not seen in
T-1220): `frob-core/**` is scoped broadly by THREE open tickets right now
(T-1219, T-1221, T-1222 -- concurrent siblings per the coordinator's own
dispatch), so `_scope_covers`'s "unambiguous single open-ticket scope
match" rule cannot silently cover a new symbol the way it did when T-1220
was the sole occupant of that glob. Root-caused via direct inspection of
`_scope_covers`/`_open_ticket_scopes` rather than guessing, then fixed
correctly: every new/changed top-level symbol in `capability_python.rs`,
the new function in `extract.rs`, `lib.rs`'s changed `frob_core`
registration, and `design/frob.strata`'s `testsuite` node all carry an
explicit `// frob:ticket T-1221` edge now, exactly as the gate's own
error message instructs. `frob check --land-parity` is clean with these
in place. Filing this as a general finding for the other two `frob-core`
siblings: none, since this is exactly the kind of overlap concurrent
same-glob dispatch is expected to produce, not a defect -- the disclosed
mechanism (explicit `frob:ticket` edges) is the intended way to resolve
it, not a symptom of anything to fix upstream.

Also disclosed, unfixed (identical to T-1220's own precedent, confirmed
by the coordinator as non-systemic): `tickets/T-1221/ticket.md` shows a
SCOPE001 under `--only scope` while the ticket is actively in-progress --
resolves the same way T-1220's did, not a new class of issue.

Filed: none -- no out-of-scope work discovered this pass.

Gates: `frob check --ticket T-1221 --only scope --only prework --only fmt
--only affect_drift --only ffi_boundary` -- 0 errors (the one SCOPE001
above is the known, disclosed, non-systemic ticket.md pattern). `frob
check --land-parity` -- clean, 0 unscoped errors.

Status: leaving T-1221 IN-PROGRESS for the coordinator/reviewer to close
after land, per this repo's review-gated ticket workflow (playbook
section 11.4) -- not closing it myself.

### Changed
```
 design/frob.strata                   |   7 +-
 docs/modules/dup.md                  |   5 +
 docs/modules/vet.md                  |  45 ++
 frob-core/frob_core.pyi              |  23 +
 frob-core/src/capability_python.rs   | 856 +++++++++++++++++++++++++++++++++++
 frob-core/src/extract.rs             |  55 +++
 frob-core/src/lib.rs                 |   5 +
 tests/unit/test_capability_native.py | 115 +++++
 tickets/T-1221/ticket.md             |  49 +-
 9 files changed, 1155 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_import_alias_and_scope_shadowing` (pytest node id, verified passing when recorded)
- `tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_functools_partial_and_literal_dict_dispatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_dynamic_dispatch_is_unresolved_not_silently_dropped` (pytest node id, verified passing when recorded)
- `tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_this_repos_own_capability_python_module_matches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 1091 warning(s), 740 waived
- error-findings: none (measured, zero errors)
