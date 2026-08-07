## Done report

Added a new `fs-read` `CAPABILITY_KINDS` entry (`src/frob/vet/
_capability_registry.py`), patterned for real in all four scanned
languages (Python `Path.read_text`/`read_bytes`/`json.load`; TypeScript
`fs.readFile`/`readFileSync`; Rust `fs::read_to_string`/`fs::read`; C/C++
`fread`/`fgets`) -- `capability_matrix()` shows 0 unexcused empty cells.
Added `fs-read` to `_selfconform.py::_EXTENDED_KINDS` so SYS100/SYS101
see it like any other extended kind, no `_effects.py::_KIND_MAP` change
needed. Added a matching `fs-read` `DEFAULT_BENIGN_CAPABILITIES` entry in
`_threat.py` so THREAT002 does not independently flag it. Implemented
`_selfconform.py::_alias_legacy_fs_observations`: a one-directional
backward-compat alias so a pre-existing bare `may "fs"` declaration is
not marked SYS101-stale by a read-only observation (added to SYS101's
`declared - observed` join only, deliberately NOT to SYS100's
`observed - declared` join, which would otherwise report both `fs-read`
and its `fs` alias as separately undeclared for one real observation). A
node declaring `may "fs-read"` specifically is unaffected either way.
Required updating `design/frob.strata` itself (frob's own self-
conformance model): added `may "fs-read";` to 7 nodes/store (cli,
graphlang, gates, checker, stratamod, core, vet, tickets_ledger) plus
`may "fs";` to stratamod (a new real write site in
`load_repo_benign_capabilities`'s `frob.toml` read, T-0303). Documented:
new "`fs-read`/`fs-write`: the read-only filesystem signal" section in
`docs/strata/selfconform.md`; taxonomy table + implementation-notes line
updated in `docs/modules/vet.md`.

Evidence: recorded via `frob ticket evidence` (4 ids in the ticket's
`evidence:` list above), including the real-gate integration test
(`TestRealGateGreen::test_repo_design_and_declarations_are_self_
conformant`) run against `design/frob.strata` + the real `src/frob/`
tree.

Filed: none (closeable within the declared scope).

Gates:
- `uv run pytest tests/unit/strata/test_selfconform.py
  tests/test_capability_registry.py tests/unit/strata/test_lint.py -q`:
  all green.
- `uv run pytest -q` (full repo): all green.
- `uv run frob check --stamp-baseline`: clean (see T-0303's Done report,
  same run).
- `uv run frob sys audit`: `self-conformance PROVED -- zero SYS gaps`;
  `capability coverage: 14 kind(s) x 4 language(s), 34 cell(s)
  patterned+proven, 22 excused with reasons, 0 unexcused`.
- `git diff main --diff-filter=D --stat`: empty (deletion-filter clean).
