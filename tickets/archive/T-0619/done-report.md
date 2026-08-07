## Done report

EPIC T-0330's ISP slice of the ARCH1xx catalog. Adds two checks to
`frob.arch._solid` (shared module with the T-0618 LSP checks, both written
once against the T-0609 normalized model): fat interface (ARCH109) and
narrow-client usage (ARCH110).

`check_fat_interface` (ARCH109): flags a same-file `ABC`/`Protocol`-family
class (`_INTERFACE_MARKER_BASES`) with at least `FAT_INTERFACE_MIN_
METHODS` (4) methods and at least `FAT_INTERFACE_MIN_IMPLEMENTERS` (2)
resolvable same-file implementers, whose AGGREGATE (interface-method,
implementer) override slots are stubbed at or above `FAT_INTERFACE_STUB_
FRACTION` (0.5) -- measured over the whole resolved-implementer pool
combined, not per implementer, matching the ticket's own "not per-class"
framing. Reuses LSP's stub-body predicates directly (`_is_stub_method`
composes `_NOT_IMPLEMENTED_EXCEPTIONS` and the same empty-shell test
`check_noop_override` already uses) rather than re-deriving them.

`check_narrow_client_usage` (ARCH110): flags a function/method with a
same-file-typed parameter (>= `NARROW_CLIENT_MIN_INTERFACE_METHODS`, 4,
methods) that calls at most `NARROW_CLIENT_MAX_USED_FRACTION` (0.34) of
that interface's methods on the parameter -- read straight off
`NormalizedCall.callee`'s dotted `<param>.<method>` text. A client calling
ZERO of the interface's methods is deliberately NOT flagged (that is an
unused-parameter smell, not a narrow-usage one).

Implementer/client resolution is same-file-only, fail-toward-silence,
matching `_iter_override_pairs`'s (T-0618) and `frob.arch._ocp`'s
precedent exactly -- an implementer or a parameter's type defined in
another file is simply unresolvable and skipped, never guessed at.

`analyze_project` dispatch wiring, `frob.arch.__init__` re-export, and a
real ARCH1xx gate are all explicitly out of this ticket's scope, matching
T-0616's/T-0618's own disclosed cuts -- `run_isp_checks` is the entry
point a future wiring ticket calls per parsed file.

### Changed
```
docs/modules/arch.md          | ISP checks section + 3 top-table rows
src/frob/arch/_models.py      | 2 new ArchCategory values (fat-interface, narrow-client-usage)
src/frob/arch/_solid.py       | +2 checks, +run_isp_checks, +helpers (~230 lines)
tests/unit/test_arch.py       | 5 new tests across 3 new test classes
```

### Evidence
Collected via `pytest tests/unit/test_arch.py -p no:cacheprovider -q`
(94 passed, full file) and `--collect-only` (all 5 node ids below
resolved):
- tests/unit/test_arch.py::TestFatInterface::test_mostly_stubbed_implementers_flag_fat_interface
- tests/unit/test_arch.py::TestFatInterface::test_mostly_implemented_methods_not_flagged
- tests/unit/test_arch.py::TestNarrowClientUsage::test_client_using_small_method_subset_flagged
- tests/unit/test_arch.py::TestNarrowClientUsage::test_client_using_most_of_interface_not_flagged
- tests/unit/test_arch.py::TestRunIspChecks::test_combines_both_checks

`frob check --only <lint|static|gates-fast|gates-native|gates-security>
--ticket T-0619` (chunked loop): all five stage groups 0 errors.

### Filed
none -- no out-of-scope work discovered.

### Gates
`frob check --only <lint|static|gates-fast|gates-native|gates-security>
--ticket T-0619` clean (0 errors each). `static`'s frob-exports warning
(`_solid.py`'s new public symbols not re-exported from `frob.arch.
__init__`) is a warning, not an error, and matches the same disclosed
scope cut T-0618/T-0616 already carry.

### Changed
```
 docs/modules/arch.md     |  62 +++++
 src/frob/arch/_models.py |   8 +
 src/frob/arch/_solid.py  | 278 ++++++++++++++++++++++-
 tests/unit/test_arch.py  | 272 ++++++++++++++++++++++
 tickets.md               | 575 ++++++++++++++++++++++++++++++++++++++++++++++-
 5 files changed, 1185 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestFatInterface::test_mostly_stubbed_implementers_flag_fat_interface` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestFatInterface::test_mostly_implemented_methods_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestNarrowClientUsage::test_client_using_small_method_subset_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestNarrowClientUsage::test_client_using_most_of_interface_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRunIspChecks::test_combines_both_checks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
