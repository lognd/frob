## Done report

Added src/frob/vet/_capability_csharp.py: a using-directive/alias/static-
using-aware resolver for csharp, modeled on _capability_kotlin.py's shape
(flat file-wide alias table, same disclosed reduced-fidelity posture).
Handles plain "using X.Y;" (curated wildcard-namespace exposure of bare
type names, registry-derived type-to-namespace disambiguation when
several curated namespaces are "using"'d at once), "using Alias =
X.Y.Z;" (namespace or type alias), "using static X.Y;" (bare-call-only
fallback, never hijacks a member-access base -- this was a real bug
caught and fixed mid-session via a probe script against
tree-sitter-c-sharp), fully-qualified member-access chains, and "var"
locals bound from "new Ns.Type(...)".

Wired into scan_file_capabilities's and _scan_file_operations's per-
language elif dispatch in _capability_scan.py/_capability.py, exactly
alongside the other five languages.

Added the missing File.WriteAllText/AppendAllText/WriteAllBytes fs-write
needle to _dangerous_ops_bash_csharp.py -- the taxonomy row this
ticket's own first acceptance criterion names needed a real needle to
resolve against; only File.Delete/Directory.Delete existed before.

6 new unit tests in tests/vet_suite/test_capability_scan_csharp.py
(mirrors test_capability_scan_kotlin.py's shape) against 6 new static
.cs fixtures under tests/fixtures/lang/csharp/ -- static fixtures rather
than tmp_path.write_text specifically so no new fs.write via-list entry
in design/frob.strata was needed (that file's ticket lease was held by
another in-progress ticket, T-draft-7e030cb3, for the whole session).

Measured: pytest -q tests/vet_suite/test_capability_scan_csharp.py --
6 passed. Also re-ran test_capability_scan_kotlin.py, test_vet_
capability.py, test_capability_registry.py, test_registry_
exhaustiveness.py, test_lang_conformance_gate.py, and
arch_suite/test_lang_adapters.py -- all green, no regression.

frob check --ticket T-4536 --base dev: 0 errors attributable
to files in this ticket's scope. Two self-inflicted findings were caught
and fixed during the session: ARCH001 on _capability.py's
_scan_file_operations (ceiling 70 to 80, since the new csharp elif
branch pushed it past the pre-existing waiver's ceiling) and CPLACE001
on this file's own frob:waive/frob:invariant directives (collapsed to
one physical line each, matching _capability_kotlin.py's own single-
line precedent, plus two more DUP001 waivers for the sibling per-
language resolver-entry-point shape). The repo-wide SUPPRESS001 (ty vs
ruff suppression drift) and gate:TICK (stale worktree leases T-3615/
T-4493, ticket-queue rot) failures are pre-existing and reference no
file in this ticket's scope.

Out of scope, not fixed: none found beyond the pre-existing repo-wide
issues named above.

### Changed
```
 src/frob/vet/_capability.py                        |  10 +-
 src/frob/vet/_capability_csharp.py                 | 465 +++++++++++++++++++++
 .../_dangerous_ops_bash_csharp.py                  |  17 +
 src/frob/vet/_capability_scan.py                   |  10 +
 tests/fixtures/lang/csharp/alias_using_fs_write.cs |  14 +
 .../lang/csharp/combined_static_and_namespace.cs   |  16 +
 tests/fixtures/lang/csharp/no_dangerous_apis.cs    |  17 +
 tests/fixtures/lang/csharp/plain_using_fs_write.cs |  12 +
 tests/fixtures/lang/csharp/static_using_console.cs |  12 +
 tests/fixtures/lang/csharp/var_local_httpclient.cs |  12 +
 tests/vet_suite/test_capability_scan_csharp.py     |  84 ++++
 tickets/T-4536/ticket.md                 |  95 ++++-
 12 files changed, 762 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/vet_suite/test_capability_scan_csharp.py::TestCapabilityScanCsharpTaxonomyClosureResolution::test_plain_using_namespace_resolves_fs_write` (pytest node id, verified passing when recorded)
- `tests/vet_suite/test_capability_scan_csharp.py::TestCapabilityScanCsharpTaxonomyClosureResolution::test_using_alias_follows_to_the_same_capability` (pytest node id, verified passing when recorded)
- `tests/vet_suite/test_capability_scan_csharp.py::TestCapabilityScanCsharpTaxonomyClosureResolution::test_using_static_resolves_bare_call_to_fully_qualified_symbol` (pytest node id, verified passing when recorded)
- `tests/vet_suite/test_capability_scan_csharp.py::TestCapabilityScanCsharpTaxonomyClosureResolution::test_no_dangerous_apis_reports_zero_findings` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
