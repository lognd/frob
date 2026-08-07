# Docs completeness sweep (2026-08-06)

Status: 2026-08-06

Mechanical enumeration of the repo's real surface (CLI verb tree, config
model, env vars, gate rule registry) diffed against what `docs/` actually
covers, per T-1610's method: enumerate from code first, then diff against
docs, rather than a prose read-through that only re-finds what earlier
read-throughs already found.

This is the input to T-1611 (why frob's own detectors did not catch each
gap) -- do not fold cause analysis into this list; that ticket does it.

## Method

- CLI surface: `frob --help` (top-level verb tree) cross-checked against
  `docs/commands/*.md` and `docs/modules/*.md`.
- Env vars: `grep` for every `FROB_*` constant assigned a string literal
  in `src/frob/**/*.py`, cross-checked against every doc file (matching
  either the literal string or the Python constant name that carries it,
  since several vars are documented by referencing the owning module's
  Python constant name rather than spelling the literal string).
- Gate rule ids: `grep` for every `"XXXX###"`-shaped string literal under
  `src/frob/gates/`, cross-checked against `docs/modules/gates.md`'s own
  "Rule catalog" table (which reads as the intended exhaustive catalog --
  its own header frames the file as covering "the checks that join the
  obligation graph...").

## Gaps found

### 1. `FROB_WORKER_STDOUT_LOG_LEVEL` (T-0806) was undocumented anywhere in docs/

`src/frob/gates/__init__.py::_WORKER_STDOUT_LOG_LEVEL_ENV` gates a
process-pool worker's own stdout log-level clamp (prevents a worker's
default-DEBUG parse logging from corrupting a quiet/`--json` `frob check`
run's stdout). `git log -S` on its introducing string dates it to
T-0806, first appearing 2026-07-23 -- roughly two weeks undocumented at
sweep time. It was previously referenced only in passing, as "worker
log-level markers" inside an unrelated SEC110-promotion paragraph in
`docs/modules/gates.md` (line ~2544), never explained on its own.

Fixed in this ticket: added a dedicated paragraph to
`docs/modules/gates.md` (next to the existing T-1436 process-pool-cap
note, the natural neighboring section) explaining the mechanism and
naming the env var explicitly.

### 2. `docs/modules/gates.md`'s "Rule catalog" table is missing ~122 rule ids

The table frames itself as the rule catalog, but a mechanical scan of
every gate module under `src/frob/gates/` for `"XXXX###"`-shaped string
literals turns up 275 distinct rule ids, of which 122 do not appear in
the catalog table at all. Every one of the 122 IS documented somewhere
in `docs/` (a per-family doc: `docs/modules/vet.md` for VET*,
`docs/modules/release.md` for the REL2xx/REL3xx block, `docs/modules/
perf.md` for PERF*, strata docs for KRB*/THREAT*/PII*, etc.) -- so this
is not an undocumented-behavior gap, it is a discoverability/
completeness gap in the one file that claims to be the exhaustive index.
Representative age check (`git log -S`): `VET001` introduced
2026-08-02 (4 days old at sweep time), `REL220` introduced 2026-07-28
(9 days old) -- these are recent additions accumulating in a
fast-moving repo, not a single one-time miss.

Families missing from the table (representative, not exhaustive --
see the full 122-id list captured in this ticket's Done report):
ARCH102/103, COMPLIANCE001-003, DEC000, DOC011, FUZZ002/003,
HOST001/002, KRB001-004, LANG001-003, LINT001-005, PERF002/005/006/
007/010/013/014, PII001-004, PROTO004, REG002-007/009,
REL220-397 (the entire REL2xx/REL3xx block, ~50 ids), RELWAIVE002,
RENDER001, SEC004/005, SYS103/105-107/201-204, SYSWAIVE003,
TEST009/010/013-015, THREAT001-005, TICK003, TIERBDEMO001, TODO003,
VET001-011, WAIVE006/007.

NOT fixed in this ticket: backfilling ~122 accurate table rows requires
reading each gate's implementation to state its actual fire condition
correctly (the existing table's own rows are each a precise one-line
description, not a name-only stub) -- disproportionate to fold into this
sweep without risking inaccurate entries. Filed as a follow-up ticket
(see Filed, below) scoped to `docs/modules/gates.md` alone.

### 3. `frob coverage` (T-1516/T-1525) has no dedicated doc section

The command exists in the CLI verb tree (`frob --help` lists it,
`docs/modules/cli.md` names it in the verb table) but its own behavior --
touched-set-incremental-by-default, flags, relationship to `make
coverage`/`make coverage-fast` -- is documented only in a passing
comment inside `docs/modules/testing.md` (~line 440, itself about a
different topic, `make coverage-fast`'s delegation). Every other
top-level verb of comparable weight (`frob clean`, `frob vet`, `frob
release`) has its own `## ` section in a `docs/modules/*.md` file
describing its own flags and behavior; `frob coverage` does not.

NOT fixed in this ticket: writing an accurate flag-by-flag section
requires reading `native_coverage_refresh`'s actual CLI wiring in
`src/frob/_cli_parsers/**`, which is out of this ticket's declared
`docs/**` scope to touch as a reference without risking a stale
description drifting further. Filed as a follow-up ticket (see Filed,
below).

## Not gaps (checked, found adequately documented)

- `FROB_PARSE_ARTIFACT_CACHE` (T-1464): initially flagged as
  undocumented by a literal-string grep, but `docs/modules/graph.md`'s
  "Persistent parse-artifact cache (T-1464)" section documents the full
  mechanism, referencing it by its Python constant name
  (`frob.lang.PARSE_ARTIFACT_CACHE_ENV`) rather than the literal string
  -- adequate, just not literal-string-greppable. No action taken.
- Every other top-level CLI verb (`frob arch`, `frob docs`, `frob agent`,
  `frob worktree`, `frob ack`, `frob debt`, `frob deprecated`, `frob
  pool`, `frob registry`, `frob doctor`, `frob fmt`, `frob natives`,
  `frob explore`, `frob dup`, `frob bind`, `frob deploy`, `frob fleet`,
  `frob mutate`, `frob perf`, `frob release`, `frob serve`, `frob
  stats`, `frob vet`, `frob test`, `frob cycle`, `frob gitlog`, `frob
  graph`, `frob clean`, `frob sys`) has at least one dedicated doc
  section under `docs/modules/` or `docs/commands/` describing its own
  behavior, not just a passing mention.

## Filed

- T-1681 -- backfill the `docs/modules/gates.md` rule-catalog
  table with the ~122 missing rows (item 2 above); carries the full
  missing-id list.
- T-1682 -- add a dedicated `frob coverage` doc section (item 3
  above).

Both filed against `docs/**` scope. Draft ids renumber at land; verify
the real ids on `main` before citing them elsewhere.
