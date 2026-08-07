## Done report

Filed from T-0393 (failed as too large for one pass): frob.arch's abstraction-opportunity
detector (frob.arch._python._check_abstraction_opportunities) flags same-signature-3+ groups
as missing abstractions unless T-0360's _is_dispatch_family exclusion applies. Re-measured this
repo's own src/ before any change: 91 abstraction-opportunity findings via
analyze_project(Path("src")). The remaining false-positive class the ticket names -- parallel
per-language tree-sitter walkers (frob.arch's own _py_*/_rust_*/_kt_*/_ts_*/_cpp_* adapter
functions independently implementing the same structural operation for each language, e.g.
src/frob/arch/_rust.py's _rust_build_module/_kt_build_module/_ts_build_module trio) -- is a
distinct false-positive shape from T-0360's dispatch-table case (no common call site links
them; each is called only from its own language's PythonAdapter/RustAdapter/etc, never from
one shared registry), so a new, narrow exclusion was added alongside it, not folded into it.

Litmus-first: before implementing, confirmed the target false-positive groups genuinely fire
under current code by direct measurement (analyze_project(Path("src")), grep over the returned
suggestions for src/frob/arch/_rust.py) -- 91 total findings, including
"_rust_build_module, _kt_build_module, _ts_build_module" and 4 other exact one-per-language
groups.

Added `_language_tag`/`_LANGUAGE_TAG_RE` (underscore-delimited `_py_`/`_rust_`/`_kt_`/`_ts_`/
`_cpp_` segment match -- structural, not raw substring proximity, mirroring T-0360's own
`_is_dispatch_family` rigor) and `_is_language_parity_family` (true only when EVERY member of
a same-signature group carries a language tag AND every member's tag is DISTINCT from every
other member's -- a same-tag duplicate, e.g. two `_rust_*` members, still flags as a genuine
same-language collision, not parity) to `src/frob/arch/_python.py`, wired into
`_check_abstraction_opportunities` right after the existing `_is_dispatch_family` check.

Re-measured after: analyze_project(Path("src")) now reports 86 abstraction-opportunity findings
(down from 91, 5 groups suppressed) -- confirmed the suppressed groups are exactly the clean
one-per-language cases (e.g. the _rust_build_module/_kt_build_module/_ts_build_module trio no
longer appears). Groups with a duplicate tag within them (e.g.
_rust_err_call_type/_rust_type_text/_kt_type_text/_kt_throw_exception_type/_ts_annotation_text,
two _rust_ and two _kt_ members) or an untagged member (e.g. lang/_extract.py's
_effective_end_row alongside tagged siblings) correctly still fire -- these are the genuinely
residual findings the ticket's own body already anticipates ("the remaining non-language-family
findings become the scope of a further per-file ticket"), not something this ticket's narrower
exclusion should have suppressed.

Found while working, filed (out of scope, not fixed here):
- T-1080: T-0666's archived evidence in tickets-archive.md names three
  tests/test_vet.py node ids with a stale "_not_detected" suffix; the live tests are named
  "_detected" (opposite) -- pre-existing on main, tickets-archive.md is outside T-1068's scope.
- T-1081: gate:ARCH reports an unwaived ARCH102 on src/frob/gates/_waive.py (the
  recent gates split's 35-export module) -- pre-existing on main, src/frob/gates/** is
  explicitly out of scope for this ticket.

No file under src/frob/gates/** was touched.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestLanguageParityExclusion::test_one_member_per_language_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestLanguageParityExclusion::test_non_parity_group_still_flagged[duplicate_rust_tag]` (pytest node id, renamed by T-1195's DUP002 fix; verified passing)
- `tests/unit/test_arch.py::TestLanguageParityExclusion::test_non_parity_group_still_flagged[untagged_member]` (pytest node id, renamed by T-1195's DUP002 fix; verified passing)
- `tests/unit/test_arch.py::TestLanguageParityExclusion::test_tag_requires_underscore_boundary` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
