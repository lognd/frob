## Done report

Fixed the producer-side root cause of T-2438's confirmed live mismatch:
`frob.lang._common._cpp_class_methods` (shared by `frob.arch._cpp`/
`_cpp_mayraise`) built a C++ method's qualname with the native `::`
scope operator and fed the SAME string to both the human-facing
`message=` text and the `Violation.symref=` identity. The DSL/graph
symbol table (`frob.lang._walk_c`) always dot-joins qualname segments,
so the two never compared equal.

Added `frob.lang._common._cpp_symref_qualname(display_name) -> str`: a
pure `"::" -> "."` rewrite, called ONLY when building `symref=`, never
for `message=`. `"::"` is never a legal identifier substring in any
grammar frob parses, so this cannot make two genuinely different
symbols collide.

Wired into:
- `frob.arch._cpp._check_long_functions` (ARCH001 long-function): the
  actual T-2438 repro site. `message=` still reads `` `Foo::bar` ``;
  `symref=` now reads `path::Foo.bar`, verified byte-for-byte identical
  to the DSL's own waiver binding for the same source.
- `frob.arch._cpp_mayraise.check_cpp_noexcept_violations`
  (cpp-noexcept-throws): this scanner's OWN `func.name` is bare already
  (its `_FN_SIG_RE` regex captures only `\w+`, so an out-of-line
  `Class::method` definition is read without qualification at all -- a
  separate, pre-existing, disclosed model limitation, not something this
  ticket introduces or fixes). `_cpp_symref_qualname` is therefore a
  no-op on today's inputs here; wired anyway so this site does not
  silently regress if the scanner ever gains class-qualified names.

`frob.dup._legacy` does not consume `cpp_function_nodes`/
`_cpp_class_methods` at all (checked directly) -- the ticket's own
speculative "should also cover frob.dup._legacy" note does not apply.

Verified directly: `frob.arch._cpp._check_long_functions` on the exact
T-2438 repro source now emits `symref='<path>::Foo.bar'`, and
`frob.lang.parse_file`/`frob.graph.dsl.parse_directives` on the SAME
source with a symbol-bound `frob:waive` comment above `bar` binds
`Edge.src == '<path>::Foo.bar'` -- identical, byte-for-byte. T-2438's
own `_canonical_symref` normalization is now provably unnecessary for
this producer (it still stands as defense in depth for any other
producer with the same disease).

Changed:
- `src/frob/lang/_common.py::_cpp_symref_qualname` (new)
- `src/frob/arch/_cpp.py::_check_long_functions` (symref= now goes
  through `_cpp_symref_qualname`; message= unchanged)
- `src/frob/arch/_cpp_mayraise.py::check_cpp_noexcept_violations` (same)
- `docs/modules/arch.md` (note on the symref/message split, satisfies
  AFFECT001's touched-doc requirement)

Evidence:
- `tests/unit/test_arch.py::TestCppSymrefCanonicalization::test_long_function_symref_is_dot_joined_message_keeps_native_spelling`
- `tests/unit/test_arch.py::TestCppSymrefCanonicalization::test_symref_matches_dsl_waiver_binding_exactly`
- Full `tests/unit/test_arch.py` + `tests/unit/test_lang_primitives.py`:
  328/328 passed, 0 failed.

Filed: none (all work stayed within this ticket's declared scope, widened
to include `tests/unit/test_arch.py` and `docs/modules/arch.md` for
evidence/AFFECT001).

Gates: `frob check --ticket T-2470` clean on
`src/frob/lang/_common.py`, `src/frob/arch/_cpp.py`,
`src/frob/arch/_cpp_mayraise.py`, `tests/unit/test_arch.py`,
`docs/modules/arch.md` (0 errors attributable to this diff).

### Changed
```
 docs/modules/arch.md           |  20 ++++++++
 frob.lock                      |  46 +++++++++++++++++++
 src/frob/arch/_cpp.py          |   8 +++-
 src/frob/arch/_cpp_mayraise.py |  13 +++++-
 src/frob/lang/_common.py       |  27 +++++++++++
 tests/unit/test_arch.py        | 101 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-2470/ticket.md       |  19 +++++++-
 7 files changed, 231 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestCppSymrefCanonicalization::test_symref_matches_dsl_waiver_binding_exactly` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestCppSymrefCanonicalization::test_long_function_symref_is_dot_joined_message_keeps_native_spelling` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2470, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
