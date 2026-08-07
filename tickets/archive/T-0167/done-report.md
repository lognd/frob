## Done report

Changed:
src/frob/__main__.py::_add_sys_parser (epilog with example invocations,
RawDescriptionHelpFormatter)
docs/commands/sys.md (Quickstart section)

Convention documented after live verification: plan/doc/audit take the repo
ROOT (default `.`) and the tool appends the configured design dir itself;
export is the single exception taking one .strata file (default
design/frob.strata) and errors on a directory argument. Every example
invocation in the epilog/Quickstart was run directly in the worktree and its
real output verified, including the negative cases (`sys plan design`
reproducing the design/design lookup miss the old text would have caused;
`sys export ... design` erroring on a directory). File-path behavior of
`sys audit <file>` deliberately left undocumented: T-0163 owns making it a
hard error.

Evidence: tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
(frob test --base main, PASS)
Filed: none
Gates: frob check clean for this change; TEST006 coverage-stamp staleness is
campaign-wide and re-stamped at release verification, not per-ticket.
Review: one REJECT round (initial text documented passing design/ as the
path, contradicting sys_runner's actual resolution); fixed and APPROVED.
