## Done report

Added the console/bash command-drift tier to DOC004
(`frob.gates._docblocks`): a ```console```/```bash```/```sh```/```shell```
fenced block's `<prog> <subcommand...>` invocations are checked against a
frob.toml-configured `[[docblocks.commands]]` array (`prog` + a
`module:callable` dotted path to a zero-argument argparse.ArgumentParser
factory). The gate imports that factory at check time and walks its live
`add_subparsers` tree -- the argparse registry is the single source of
truth, never a second hand-maintained subcommand list. A chain that does
not resolve is STALE (error); a resolving one with no nearby
frob:doc/frob:describes/frob:tests anchor is UNBOUND (warn), matching the
existing python/rust/ts tiers. No configured commands means zero
console/bash checking (fail-open).

This repo now configures itself as the first instance
(`[[docblocks.commands]] prog = "frob" parser =
"frob.__main__:_build_parser"` in frob.toml) -- dogfooding it against this
repo's own docs found 0 stale console commands and 59 unbound-console
warnings (pre-existing undocumented examples, no error-level regressions),
confirmed via `frob check --only docblocks --json`.

Acceptance verified: a fenced ```console``` block citing
`frob nonexistent-subcommand` fires DOC004 (stale, error); a real
subcommand (`frob check --delta`) with a nearby anchor passes; the same
real subcommand unanchored warns unbound; `frob:waive DOC004 reason="..."`
suppresses; no `[[docblocks.commands]]` entries means no console checking
at all -- all five as automated tests in tests/test_gates.py.

### Changed
```
 docs/modules/gates.md        |  35 +++++--
 frob.toml                    |  12 +++
 src/frob/gates/_docblocks.py | 239 +++++++++++++++++++++++++++++++++++++++++--
 tests/test_gates.py          | 104 +++++++++++++++++++
 tickets.md                   |  47 ++++++++-
 5 files changed, 418 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_nonexistent_subcommand_is_stale` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_real_subcommand_anchored_passes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_real_subcommand_unanchored_warns_unbound` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_waive_suppresses_console_stale` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDoc004ConsoleCommandDrift::test_no_config_means_no_console_checking` (pytest node id, verified passing when recorded)
