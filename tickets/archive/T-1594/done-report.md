## Done report

Design decision made and implemented: `AppConfig._check_ticket_kind_value`
stays (removing it would make `ticket_kind_value` the ONE inconsistent
field among ticket_state/ticket_kind/ticket_tier/ticket_tier_value, which
all validate the identical way at `AppConfig` construction, each with its
own `test_app_config.py::TestEnumFieldValidation` coverage already passing
today). `_kind()`'s own `TicketKind(...)` try/except is legitimate
defense-in-depth (unreachable for any value that already passed `AppConfig`
construction, same shape `_tier()` already carries for `ticket_tier_value`
with no test exercising its own dead branch either) -- not a bug, not
something to remove.

Confirmed the real CLI path already gives a clean, non-traceback message to
an end user: `src/frob/__main__.py`'s top-level `except Exception` boundary
catches the `ValidationError` from a bad `--kind`, prints a one-line
`frob: ...` to stderr, and exits 1 -- never a raw traceback for an actual
CLI invocation. The only place that saw the raw exception was this ONE
test, which constructs `AppConfig(...)` directly, bypassing that top-level
boundary entirely.

Fixed `tests/test_ticket_evidence.py::TestKindCliInvalidKind::
test_invalid_kind_refused` to assert what actually and correctly happens:
`AppConfig(ticket_kind_value="not-a-real-kind")` itself raises
`pydantic.ValidationError` with "is not a valid ticket kind" in the message
(same assertion shape as the sibling
`test_app_config.py::test_invalid_ticket_kind_value_lists_valid_values`,
which was already passing and unchanged). No production code touched --
`src/frob/app/config.py` and `src/frob/app/ticket_runner/**` are unchanged.

Verified: `pytest tests/test_ticket_evidence.py::TestKindCliInvalidKind
tests/test_app_config.py::TestEnumFieldValidation -q` -> 12 collected, 0
failed (SUITE-RESULT confirmed). `ruff check` clean on the touched file.

### Changed
```
 tests/conftest.py                     |  44 ++++++++
 tests/system/test_cli_perf.py         |  45 ++++++++-
 tests/test_coverage.py                |  30 +++++-
 tests/unit/test_conftest_stackdump.py |  80 +++++++++++++++
 tickets.md                            | 184 +++++++++++++++++++++++++++++++++-
 5 files changed, 374 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_ticket_evidence.py::TestKindCliInvalidKind::test_invalid_kind_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 5817 warning(s), 797 waived
- error-findings: none (measured, zero errors)
