## Done report

throwaway repro ticket for T-0590 investigation, used to manually confirm
the grace-window regression against the real diff/gate machinery before
the fix landed; its own scratch fixture (`tests/test_scratch_repro_a.py`)
was removed afterward since T-0590's own regression test
(`test_cov002_grace_covers_ticket_created_and_closed_in_same_diff`)
supersedes it -- evidence updated to point at that real, still-resolvable
test instead of the deleted scratch file.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 1 error(s), 4168 warning(s), 219 waived
- error-findings: PRE001@tickets/T-0954
