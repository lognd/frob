## Done report

Changed:
src/frob/graph/digest.py::_normalize_newlines
src/frob/graph/digest.py::_hash_tokens
src/frob/graph/digest.py::_digest_doc

Windows CRLF checkouts made DRIFT001's body digest platform-dependent: a tree-sitter leaf token spanning a multi-line string/docstring captures the raw source bytes between its quotes, embedded line endings included, so an acked digest computed on LF reads as "moved" on the identical CRLF-checked-out source. `_normalize_newlines` collapses `\r\n`/`\r` to `\n` before hashing in `_hash_tokens` and `_digest_doc`, so sig/body/doc digests are now line-ending independent.

Evidence: tests/test_graph.py::TestDigests::test_crlf_checkout_does_not_move_digest plants a CRLF-encoded copy of a multi-line-docstring symbol's source alongside the LF original and asserts all three digests match. All 6 TestDigests tests pass.

Filed: none (this IS the filed CI-followup ticket).

Gates: ruff-check/ruff-format clean on the touched files; ty clean on the touched files. `frob ticket done-report` itself hung past 590s in this worktree (unrelated pre-existing tool stall, not investigated further under this ticket's scope) so this section was written directly. `--check-repro` could not produce an automated fail-then-pass verdict because this repo's `frob ticket land` squashes a ticket's repro test and its fix into one commit (docs/modules/tickets.md#check-repro-post-land-limitation-t-2025), so no pre-existing ref carries the test without the fix; manually confirmed the new test fails (digest inequality) against the pre-fix digest.py and passes against the fixed version.
