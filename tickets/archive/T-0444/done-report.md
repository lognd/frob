## Done report

Fixed evidence_covers_scope (src/frob/gates/__init__.py): a ticket whose
kind is in CMD_EVIDENCE_ALLOWED_KINDS (today just `docs`) and which carries
at least one real cmd: evidence entry is now considered covered, short-
circuiting the covering-TEST requirement that cannot apply to a doc-only
scope. Reuses the SAME CMD_EVIDENCE_ALLOWED_KINDS frozenset the record-time
and land-time guards use, so record/close/land stay consistent. Code kinds
cannot carry cmd evidence (enforced elsewhere against the same frozenset),
so this cannot loophole a bug/feature/security ticket into closing on an
unrelated command -- proved by the negative test.

Evidence (2 ids, both pass): test_evidence_covers_scope_true_for_docs_kind_with_cmd_evidence
(docs + cmd -> covered) and test_evidence_covers_scope_false_for_code_kind_with_cmd_shaped_evidence
(bug + cmd-shaped -> NOT covered, no loophole). This fix is self-dogfooded:
it is what let T-0267 (the docs ticket that surfaced this) close honestly.
