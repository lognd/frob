## Done report

Removed the uv, ruff, ty and pytest badge rows from the README badge block, keeping PyPI version, Python 3.11+, license and CI status. Verified by reading the rendered badge block; no tests per owner direction (docs-only, four-line deletion). No new tickets filed.

### Changed
```
 README.md                | 4 ----
 tickets/T-4177/ticket.md | 2 +-
 2 files changed, 1 insertion(+), 5 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 6 error(s), 4526 warning(s), 935 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/vet/_bare_toolchain.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/gates/_rule_id_scan.py, DRIFT002@src/frob/check/_python.py, PRE001@tickets/T-4177

### Acceptance amendments
- [3] remove: removed 'given the README outside the badge block, when diffed against main, then it is unchanged' (reason: owner: no tests needed for a README badge deletion; a diff-is-unchanged criterion is ceremony on a four-line docs change; logan, 2026-09-07)
- [2] remove: removed 'given the four retained badges, when each URL is requested, then it resolves' (reason: owner: no tests needed for a README badge deletion; the retained badge URLs were already verified by hand when the ticket was filed; logan, 2026-09-07)
