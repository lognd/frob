## Done report

Changed:
pyproject.toml (serve extra + dev group mcp pin bounded <2)
docs/guides/release.md (Decision 5: mcp 2.x pin, port-later decision, unbounded-dependency enumeration)
tests/unit/test_dependency_pins.py (regression test)

Evidence:
tests/unit/test_dependency_pins.py::TestMcpPinIsBounded::test_serve_extra_excludes_mcp_2x
tests/unit/test_dependency_pins.py::TestMcpPinIsBounded::test_dev_group_excludes_mcp_2x
tests/unit/test_dependency_pins.py::TestMcpPinIsBounded::test_serve_extra_still_allows_mcp_1x
Confirmed the same tests fail against the pre-fix pin (mcp>=1.28.1, no upper bound) and pass against the fix (mcp>=1.28.1,<2).

Filed: T-3904 (port frob.serve.server to mcp 2.x API), triggered by this pin, cited from docs/guides/release.md's Decision 5 section.

Pin decision: bounded mcp<2 in both the serve extra and the dev group (not a hard exact pin) -- checked mcp 2.1.1's actual API surface directly (downloaded the wheel): MCPServer's constructor, the tool() decorator, and run(transport="stdio") are all present with compatible signatures, so the eventual port is low-risk, but end-to-end verification against a real mcp 2.x client has not happened, so the port is deferred (T-3904), not done now.

Release workflow check (T-3884-relevant): .github/workflows/release.yml's upload job runs three gh-action-pypi-publish steps sequentially with no continue-on-error, so GitHub Actions' default abort-on-step-failure means a failed publish step stops the job before any later step runs.

Unbounded-dependency enumeration: reported in docs/guides/release.md's Decision 5 section. tree-sitter-language-pack (floor 0.13, latest 1.16.1) is the one other production dependency that crossed a major boundary unbounded; flagged for a follow-up compatibility check, not bounded here (no observed break).

Gates: frob check --ticket T-3857 clean except two pre-existing, out-of-scope errors, both confirmed present on main before this ticket's changes:
  - gate:DOC DOC006 tickets/T-3886/ticket.md:91 (T-3886's own ticket body, out of T-3857's scope; will be fixed when T-3886 is worked, same series)
  - gate:SCOPE SCOPE001 uv.lock (tooling-regenerated lock file, reverted to HEAD before each check run; land-owned per T-0731, not part of this ticket's diff)

### Changed
```
 docs/guides/release.md             | 58 +++++++++++++++++++++++++++++++++
 pyproject.toml                     | 16 +++++++--
 tests/unit/test_dependency_pins.py | 67 ++++++++++++++++++++++++++++++++++++++
 tickets/T-3857/ticket.md           | 33 +++++++++++++++++++
 tickets/T-3904/ticket.md | 29 +++++++++++++++++
 5 files changed, 201 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_dependency_pins.py::TestMcpPinIsBounded::test_serve_extra_excludes_mcp_2x` (pytest node id, verified passing when recorded)
- `tests/unit/test_dependency_pins.py::TestMcpPinIsBounded::test_dev_group_excludes_mcp_2x` (pytest node id, verified passing when recorded)
- `tests/unit/test_dependency_pins.py::TestMcpPinIsBounded::test_serve_extra_still_allows_mcp_1x` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 4350 warning(s), 924 waived
- error-findings: DOC006@tickets/T-3886/ticket.md
