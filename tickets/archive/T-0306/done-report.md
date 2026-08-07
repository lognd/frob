## Done report

Fixed the SYS100 direction of the fs/fs-read backward-compat alias in
`_extended_kind_violations` (src/frob/strata/_selfconform.py): a node's
full declared `may` kind set is now checked for bare `fs`, and if present
`fs-read` is unioned into the effective declared set before the
observed-minus-declared diff, so a broad `may "fs"` covers a real
`fs-read` observation with no SYS100 finding. The asymmetry is preserved:
a node declaring only `fs-read` still fires SYS100 (via the existing
THREAT004 delegate in `_core_undeclared_violations`) when a real
fs-write-class effect is observed -- narrower declarations never cover
broader observations, only the reverse.

Added three regression tests in
`tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceFsReadAlias`:
- `test_broad_fs_declaration_discharges_read_only_observation`
- `test_narrow_fs_read_declaration_does_not_cover_fs_read`
- `test_fs_read_only_declaration_still_fires_on_fs_write_observation`

Gates:
- `uv run pytest tests/unit/strata/test_selfconform.py -q`: all green (32
  passed, including the 3 new regression tests).
- `uv run frob check`: 0 errors, 1 warning, 204 waived (clean).

Verification against the live repro (read-only, after reinstalling the
global binary from this fix): lithos's `frob sys audit .` no longer fires
SYS100 for `fs-read` on any of the six previously-affected nodes
(rust_core, regolith_py, stdlib_records, tooling, demos, vscode_ext).
