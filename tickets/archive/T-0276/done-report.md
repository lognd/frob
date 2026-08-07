## Done report

Investigated per instructions: did NOT assume the hypothesis was
right. Built and ran the requested minimal-fixture check directly
against `frob.graph.build_graph`/`frob.gates._load_tests`: neither
takes a `check_type` parameter at all, and `_load_tests` unconditionally
calls both `collect_python_tests` and `collect_rust_tests` regardless
of `check_type`. `check_type` only gates which per-LANGUAGE TOOLCHAIN
STAGE (`cargo clippy`/`fmt`/`cargo test` itself) `_dispatch_check` runs
(`src/frob/app/check_runner.py::_DISPATCH_BY_TYPE`) -- it has no effect
on graph parsing, directive extraction, or gate evaluation. Confirmed
this empirically: reproduced feldspar's exact setup in a scratch rsync
copy (`check_type = "python"` intact, untouched) and, after T-0271/
T-0274/T-0275 landed, BOTH `crates/feldspar-library`'s `frob:tests`
binding AND (via this ticket's own fix) `crates/feldspar-core`'s
`frob:waive TEST003` now resolve correctly -- disproving the
check_type hypothesis outright, since check_type was never touched.

Real root cause of the residual `crates/feldspar-core` TEST003, traced
via direct `frob.lang._extract.extract()` calls against the real
`tests/property.rs`: `_match_waiver`'s file-scoped comparison (used
for every rule without a per-symbol `violation.symref`, which includes
TEST003/TEST004) required a waiver's own file to be LITERALLY EQUAL to
`violation.file` -- but TEST003/TEST004 violations use a package/
system INTERFACE id (`crates/feldspar-core/src`, or a system id) as
that field, never a real single file path. No real source file (every
one has an extension) can ever equal a bare interface-id string, so a
`frob:waive TEST003`/`TEST004` directive could never match ANY
violation, regardless of placement -- a structural, by-construction
gap, not a check_type exclusion.

(A SEPARATE, unrelated limitation was also found and is NOT fixed by
this ticket, reported as a known gap: `crates/feldspar-core/tests/
property.rs`'s tests are declared inside a `proptest! { ... }` macro
invocation body; tree-sitter parses that as one opaque token-tree node,
so `frob.lang._walk_rust` extracts ZERO symbols from the entire file --
confirmed directly (`extract()` returns `0 symbols` for that file).
This means a `frob:tests`/`frob:waive` comment placed anywhere in that
file can never bind to a specific test symbol either (`following`/
`enclosing` both resolve to `None`), independent of the waiver-matching
fix above. This ticket's fix still lets the FILE-level fallback waiver
work (since the bare-path fallback still lands under the package
prefix), which is why `crates/feldspar-core`'s residual TEST003 now
clears -- but a symbol-level `frob:tests` binding into a
`proptest!`-bodied test will still never resolve. Recommend as a
follow-up ticket for whoever next touches `frob.lang._walk_rust`, not
attempted here: scope creep beyond this ticket's declared fix.)

Fix: `_match_waiver` (`src/frob/gates/__init__.py`) now, for the
symref-less (file-scoped) branch, ALSO accepts a waiver whose file
lives under `violation.file`'s directory prefix (`violation.file.rstrip
("/") + "/"`), in addition to the existing exact-match checks. Safe
against over-broadening: a real per-file violation's `file` always has
an extension, so no other real path can ever start with
`"<file>/"` -- only a genuine package/system-id-shaped `violation.file`
(no extension) admits any prefix matches at all.

Test added: `TestTestGate::test_test003_waiver_in_a_file_under_the_
package_matches` (`tests/test_gates.py`) -- a `frob:waive TEST003`
comment in a file under the flagged package must now waive that
TEST003 violation via `_apply_waivers`, asserted both that it leaves
`kept` and that it lands in `waived`.

ANSWER to the coordinator's explicit question ("does rust TEST
evidence validation run at all under check_type=python?"): YES,
unconditionally -- confirmed by source read and empirical reproduction,
not assumed. `_load_tests` always calls `collect_rust_tests` regardless
of `check_type`; the earlier T-0271 fix (virtual-workspace descent) is
what actually made feldspar's rust interfaces newly discoverable this
session, not any change to check_type handling. NO DESIGN CHANGE is
needed to make collection "language-driven by `[[test.runner]]`
entries instead of check_type" -- that premise does not hold against
the current source; collection was never check_type-gated in the first
place.

Verified against the real bug (read-only feldspar, scratch rsync copy
only -- feldspar itself untouched): after this fix + `uv tool upgrade
frob`, `frob check --only gates` on the scratch copy shows NEITHER
`python/feldspar/thermo` NOR `crates/feldspar-library/src` TEST003
lines anymore (T-0275/T-0271 respectively). CORRECTION (caught by a
follow-up re-check before this ticket's coordinator report went out --
recorded here rather than silently editing away the earlier overclaim):
`crates/feldspar-core/src`'s TEST003 STILL fires even after this fix.
Root cause of the residual miss: this fix's directory-prefix widening
(`waiver_file.startswith(violation.file.rstrip("/") + "/")`) only
reaches files literally under the package id's own path
(`crates/feldspar-core/src/**`); feldspar-core's `frob:waive TEST003`
directive lives in `crates/feldspar-core/tests/property.rs` -- a
SIBLING directory of `src/`, not a descendant of it, since integration
tests never live inside `src/`. A correct general fix needs a
CRATE-root notion of "package" for this waiver-reachability purpose
(`crates/feldspar-core` as a whole, not just its `src/` subtree) --
deliberately NOT implemented in this pass: the obvious naive
broadening (matching on `violation.file`'s first two path segments)
over-broadens for python packages, where the interface id's first two
segments (e.g. `src/frob`) span MANY unrelated sibling subpackages, and
would reintroduce exactly the blanket-waiver failure mode T-0148's
review caught (one directive silently waiving unrelated violations).
Fixing this properly wants either a rust-specific crate-root
computation or extending `Violation` with an explicit waiver-scope
field (mirroring the `symref`-exact-match precedent already in this
function) -- flagged as a follow-up ticket, not attempted here as
scope creep beyond a single-session fix. What this ticket DOES fix,
confirmed real: a package-level waiver written anywhere under the
violated package's OWN directory (the common case for python packages,
and for a rust crate's `src/` unit tests) now works, where before NO
placement anywhere could ever make a TEST003/TEST004 waiver match.

All targeted tests pass; full repo suite `uv run pytest tests/ -q -n
auto` re-verified after this fix (see final aggregate report for the
exact pass count and `frob check` gate result).

Same concurrent-repo-clobber incident as T-0274/T-0275 hit this
ticket's implementation TWICE (first pass wiped between edit and
verification; a second redo was ALSO wiped between `git add`+commit
and the ticket-close step, losing the ticket record itself even though
the code commit `523d1cc` survived) -- redone a third time end-to-end
and this Done report/ticket-close is being committed immediately after
writing, with no gap for further loss.
