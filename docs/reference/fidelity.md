# Fidelity accounting

`frob check` never skips a file silently. Every walked file is classified per
rule by `gob_check::subject_status_for` (design: `docs/design/universal-model.md`
sections 4.1, 4.2 and 4.6).

| File state | Rule needs a capability (DOC001, DOC002, INV002, COV001) | Rule reads every text artifact (TODO001, REF001, TEST001, INV001, DRIFT*) |
|---|---|---|
| Opaque F0 (no adapter), text, comments scanned (TOML) | NotApplicable | examined |
| Opaque F0, text, not scanned (for example `.py`, `.json`) | NotApplicable | one Unresolved per rule naming the file count |
| Opaque F0, binary (NUL byte or known extension) | NotApplicable | NotApplicable |
| Parse failed | Unresolved | Unresolved |
| Partial parse (holes) | examined, plus an Unresolved for symbol rules | examined |
| Fidelity below the rule's minimum (COV001 and AFFECT001 need F2) | Unresolved | Unresolved |

`NotApplicable` is a query answer only: it is counted, never a finding. A rule
outside the table is always examined. The minimum fidelity lives in
`gob_check::need_of` because `RuleMeta` is declared in `gob-rules`.

## Reach poison

`COV001` treats a callable reached only through May edges, or named by an
unresolved call in a test's reach, as Unresolved: neither covered nor
uncovered. `AFFECT001` does the same for dependents reached through May
edges or behind unresolved calls naming the changed symbol. A file that
parsed partially adds one Unresolved to each of these rules.

## Test selection

`frob test` reports changed files without an adapter in
`touched.unresolved_files` and as a warning (an Unresolved `TEST001`
finding): selection is undecided for them instead of ignoring them.

## The report

`frob check --timing --text` lists, per language (`opaque` for adapter-less
files): files, files examined, partial parses, files NotApplicable per rule
family and Unresolved counts per rule, under `fidelity`.
