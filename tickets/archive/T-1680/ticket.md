---
id: T-1680
title: Deletion filter rejects an exact root-level filename as an 'over-broad glob'
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_git_ops.py
- tests/test_evidence_integrity.py
- src/frob/tickets/_land.py
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: the breadth heuristic and its regression lock
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_evidence_integrity.py
  reason: the breadth heuristic and its regression lock
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_land.py
  reason: the same land landed three gate errors (2x ARCH001 oversized functions,
    1x PII012); fixing them here keeps main green rather than leaving it red behind
    a closed ticket
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: the same land landed three gate errors (2x ARCH001 oversized functions,
    1x PII012); fixing them here keeps main green rather than leaving it red behind
    a closed ticket
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_leases.py
  reason: the same land landed three gate errors (2x ARCH001 oversized functions,
    1x PII012); fixing them here keeps main green rather than leaving it red behind
    a closed ticket
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 closure for _check_already_landed
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_evidence_integrity.py::TestD12DeletionFilterBroadScope::test_exact_root_level_file_authorizes_its_own_deletion
- tests/test_evidence_integrity.py::TestD12DeletionFilterBroadScope::test_wildcard_breadth_rules_are_unchanged
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_refuses_while_land_lock_held
designated_repro_test: null
threat: null
component: null
---
_deletion_glob_too_broad in src/frob/tickets/_land_git_ops.py decides whether a scope entry may authorize a DELETION. Its final test is:

    return '/' not in stripped

The intent (D-12) is to refuse a bare top-level DIRECTORY like 'src' (expanded to 'src/**'), which would silently authorize deleting anything beneath it. But the test it actually performs is 'does this string contain a slash', and that also rejects an exact root-level FILE path:

    _deletion_glob_too_broad('FROBLEMS.md')  -> True
    _deletion_glob_too_broad('tickets.md')   -> True
    _deletion_glob_too_broad('README.md')    -> True

An exact literal path naming one file is the NARROWEST possible authorization -- strictly more specific than 'src/frob/tickets/**', which the same function trusts. The consequence: a ticket whose declared scope names precisely the file it deletes is refused with a message that prints the scope containing that very path and then says it is outside it:

    land: T-1612 refused -- worktree deletes file(s) outside its scope
    ['FROBLEMS.md', 'skills/**', ...]: ['FROBLEMS.md']

There is no way to satisfy this: adding the path to scope is the remedy the error suggests, and the path is already there. Deleting any root-level file is currently impossible via a scoped land.

This is the T-1662 shape: a lexical property (presence of '/') standing in for the semantic question (does this pattern authorize more than the file being deleted, and is it a directory rather than an exact path).

Fix: decide breadth from what the pattern MATCHES, not from its punctuation. A pattern containing no wildcard metacharacter ('*', '?', '[') is exact -- it authorizes exactly one path and is always narrow enough, slash or no slash. Only a directory-expanded glob at top level ('src/**' from a bare 'src', '.', '*') is over-broad. Keep the existing refusal for those.

Add regression cases for an exact root-level file, an exact nested file, a bare top-level directory, and the whole-tree pattern, so the distinction is locked rather than re-derived.

Found while landing T-1612 (removes the tracked FROBLEMS.md artifact), which cannot land at all until this is fixed.