## Done report

Documented T-1102's disclosed doc debt at the exact anchors
`analyze_project`'s own `frob:doc` directives cite: added two new
paragraphs to docs/modules/arch.md's `#public-api` section (the
`analyze_project` block) --

1. Single-file-mode parity (T-1102): what changed (`root.is_file()` ->
   resolve to `root.parent` + a one-file candidate list instead of
   `_collect_files`), why the old behavior silently produced zero
   findings for a plain file (`.git`/`os.walk` both no-op on a file), and
   the byte-identical-shape guarantee `_analyze_one_file` gives, citing
   the real proving test.
2. `large-file`/`LARGE001` (T-0368/T-0372 advisory, T-1102 gate wiring):
   the advisory category's own threshold/exemption rule plus the gate-
   side WARN first-turn-on wiring, cross-referencing docs/modules/gates.md's
   existing rule-catalog entry rather than duplicating its turn-on-count
   detail.

Retired the disclosed `frob:waive AFFECT001` directive T-1102 left on
`analyze_project` (citing this ticket's pre-renumber draft id) -- the doc
debt it was waiving is now paid, so the waiver is dead weight, not a live
disclosure; replaced with a plain `frob:ticket T-1104` marker matching
this module's existing per-ticket marker convention. Confirmed no
AFFECT001 refire: `frob check --ticket T-1104 --only affect_drift` is
clean (0 errors).

Verified the anchor exists and resolves: `<a id="public-api"></a>` is
the same anchor `# frob:doc docs/modules/arch.md#public-api` on
`analyze_project` already cited (docanchor/doclink gates both clean, see
below) -- no new anchor was invented, the existing one now carries more
content.

Docs-kind ticket, no code behavior changed -- scope-added the two tests
that actually prove the documented behavior
(`tests/unit/test_memo.py`, `tests/test_arch_gate.py`) before recording
evidence, per the playbook's docs-kind land-refusal note, and bound both
to the ticket's single acceptance criterion (`--accepts 0`).

Gates (manual `--only` loop, `--ticket T-1104`): prework/coverage/
docanchor/doclink/scope/affect_drift/drift all 0 errors (measured after a
fresh `frob ticket sweep T-1104`, since PRE001 went stale after the
mid-ticket `frob ticket scope --add`).

Tests: both cited evidence node ids re-run individually and pass
(`tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit`,
`tests/test_arch_gate.py::TestArchGateLargeFile::
test_single_file_mode_matches_directory_walk` -- 1 passed each, measured).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit` (pytest node id, verified passing when recorded)
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_single_file_mode_matches_directory_walk` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 752 warning(s), 428 waived
- error-findings: INV006@src/frob/gates/_todo_fmt.py, TICK006@tickets.md
