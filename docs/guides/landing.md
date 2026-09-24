# Curated landing: real work vs bookkeeping (T-3067)

<!-- frob:describes src/frob/tickets/_land_squash.py::classify_ticket_commits -->
<!-- frob:describes src/frob/tickets/_land_squash.py::_is_bookkeeping_commit -->

Full landing-pipeline reference lives in
[`docs/modules/tickets-landing.md`](../modules/tickets-landing.md) --
this guide is the narrower, operator-facing story for ONE piece of that
pipeline: a ticket's own worktree branch history is a mix of REAL WORK
commits (the code/test/doc changes an agent actually made) and
BOOKKEEPING commits (`frob ticket start`/`scope`/`points`/`evidence`/
`done-report` ledger writes -- every one of those verbs commits to
`tickets/<id>/ticket.md` or `.frob/`). A typical ticket's worktree
history carries 2-7 real-work commits interleaved with 9-21 bookkeeping
ones, one or more per verb call across the whole session.

## `classify_ticket_commits`

`frob.tickets._land_squash.classify_ticket_commits` is the mechanical
primitive: given a ticket branch's `(sha, changed_paths)` pairs (a
caller's own `git log --name-only` derivation -- this function does no
git I/O itself), it partitions them into `(real_work, bookkeeping)`, each
a tuple of shas in the branch's own commit order.

A commit counts as bookkeeping (`_is_bookkeeping_commit`) only when EVERY
changed path lives under `tickets/` or `.frob/` -- a commit that ALSO
touches a real source/test/doc path in the same commit is real work,
even if it happens to touch a ticket ledger file too (an agent that
fixes a typo in the same commit as an evidence-binding write did real
work in that commit). An empty changed-path set is never classified as
bookkeeping either -- nothing to classify away.

<!-- frob:describes src/frob/tickets/_land_squash.py::classify_ticket_commits -->

```python
from frob.tickets._land_squash import classify_ticket_commits

real_work, bookkeeping = classify_ticket_commits(
    [
        ("sha-start", ["tickets/T-1234/ticket.md"]),
        ("sha-code-1", ["src/frob/x.py"]),
        ("sha-evidence", ["tickets/T-1234/ticket.md"]),
    ]
)
# real_work == ("sha-code-1",)
# bookkeeping == ("sha-start", "sha-evidence")
```

## UNWIRED by design (this ticket's own scope)

`classify_ticket_commits` is not yet called from the live land path.
Same "prove the mechanical primitive in isolation, wire it later"
precedent `frob.tickets._land_splice.classify_test_then_impl_paths` set
for T-3546 (`docs/design/land-splice-test-then-impl.md`): today's
`_land_squash_apply` still folds a ticket's ENTIRE worktree diff into one
composed commit (`fold_worktree_into_commit`,
`docs/modules/tickets-landing.md`), never a curated multi-commit
sequence. Deciding what a caller actually DOES with a `(real_work,
bookkeeping)` split -- keep each real-work commit individually and
squash bookkeeping into one trailing consolidated commit, refuse a
branch whose real-work count falls outside the measured 2-7 range,
surface the split in a land report -- is real follow-up integration
work, not done here.
