## Done report

C/C++ macro-alias-aware capability resolution added to vet/_capability.py
(_c_macro_alias_table, _c_declared_name/_c_scope_bound_names/_c_shadowing_
scope, _resolve_c_identifier, _c_binding_capabilities/operations), wired
into scan_file_capabilities + _scan_file_operations, mirroring the Python
(T-0328)/TS (T-0377)/Rust (T-0378) resolvers. Scope-shadow discipline is
POSITION-aware from the start (Rust's round-2 fix, T-0339 fail-closed
built in directly, not repeated as a round 2) -- `_record_rust_binding` is
reused for the C table's bookkeeping so a call site textually BEFORE a
same-named local declaration still resolves through the macro, and a call
AFTER it does not.

Object-like macro aliasing only (`#define SYS system`), transitively
chased (`#define A B` + `#define B system` resolves `A`). A function-like
macro (`#define SYS(x) system(x)`, a distinct `preproc_function_def` grammar
node) is a documented out-of-scope limitation, mirroring T-0378's grouped-
`use` limitation note -- its own expansion already contains literal
"system(" text in the common case, so the pre-existing lexical scan still
has a real shot at it. `using`-declarations and namespace-qualified calls
(`fs::system(...)`) need no special resolution: the registry's needles are
bare substrings (`"system("`), which already occur verbatim in a qualified
call site, so the pre-existing lexical pass already catches them -- only a
true rename (the preprocessor case) evaded detection. Type-only aliases
(`typedef`/C++11 alias-declarations) do not rename a callable and are out
of scope for the same reason. Block scoping is over-approximated to whole-
function granularity (matches the python/rust resolvers' own granularity,
not per-`compound_statement` C block scoping) -- documented in the module's
new block comment, not a silent gap.

8 new tests in TestCapabilityScanCBindingResolution: macro alias resolved,
registry entry named (library="libc"), transitive 2-hop alias resolved, no
false positive with no #define present, parameter shadow not detected,
local-declaration shadow not detected, call-before-shadow still detected
(the security property, mirrors T-0378's ordering test), function-like
macro documented-limitation case (still caught, but via the pre-existing
lexical path, not the new resolver). Full tests/test_vet.py: 190 passed.
`uv run frob check --delta --ticket T-0379`: 6 pre-existing errors
(unrelated: DRIFT001 tickets ledger debt, TEST003 doctor.py debt, a stale
DRIFT002 ref in tests/test_tickets_evidence_cli.py, all pre-existing
outside this ticket's scope), 0 new errors from this change; ty's one
pre-existing diagnostic is in tests/unit/strata/test_threat.py, untouched
by this ticket. No doc file changes needed -- scan_file_capabilities/
_scan_file_operations keep their existing frob:doc anchors, and neither
T-0328/T-0377/T-0378 required a docs/modules/vet.md edit either (grepped
for precedent before writing this report).

Filed: none. Not closed (review-gated per dispatch instructions).

### Changed
```
 src/frob/vet/_capability.py | 312 ++++++++++++++++++++++++++++++++++++++++++++
 tests/test_vet.py           | 110 ++++++++++++++++
 tickets.md                  |  60 ++++++++-
 3 files changed, 480 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)
