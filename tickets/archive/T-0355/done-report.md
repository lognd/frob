## Done report

T-0355 bundled three items split out from a T-0240-adjacent report.
Verified against current code first (T-0474 already backgrounds the
sweep at `frob ticket start`, T-0484 landed coverage-fast changes) --
neither mooted this ticket's items.

Item 1 (SIGINT clean message): main() used to run its dispatch inline,
so a Ctrl-C during a long-running command (e.g. a slow synchronous
sweep on a bad mount) surfaced as a bare KeyboardInterrupt traceback.
Split the dispatch body into a private _dispatch(argv) helper and wrap
only that call in main() with a KeyboardInterrupt handler that prints
"frob: interrupted" to stderr and exits 130 (128+SIGINT, the
conventional code). Moved the frob:ticket T-0358 stale-install-warning
directive back onto main (now public) since it rode onto the newly
private _dispatch otherwise (COV005).

Item 3 (scope_digest content-keying): verified scope_digest's per-file
hash already comes from frob.graph._content_hash -- a plain sha256 of
file bytes, never folded with _stat_key's mtime/size (that pair is only
a cheap cache-invalidation check). Combined with the repo-relative path
key, a recorded sweep digest is already checkout-portable: identical
scope files at the same relative paths in two independent checkouts
produce the same digest regardless of absolute root or timestamps.
Added a regression test across two independent tmp_path checkouts
pinning this so a future change keying on stat metadata instead would
fail loudly rather than silently reintroducing the bug the ticket
described.

Item 2 (PRE001 catch-22 on slow mounts) was NOT implemented here: the
ticket's own text says it "needs a design decision (timeout +
partial-sweep-ok state, or async sweep)", not a mechanical port of an
existing fix. `frob ticket sweep` (the always-available resweep path
used after a scope edit) is still fully synchronous by design, and
PRE001 only ever compares against a fully-completed digest -- there is
no partial-sweep-ok state today. Forcing a partial implementation here
risked either a correctness hole (a provisional-pass state that lets
PRE001 go green on incomplete data) or silently deciding the product
design question myself. Not Filed as a new ticket instead: T-draft-ac820c46 (never refiled)
(off-default-branch provisional id; will mint a real T-#### id on
merge to main).

### Changed
```
 src/frob/__main__.py          | 31 ++++++++++++++---
 src/frob/app/ticket_runner.py | 77 ++++++++++++++----------------------------
 src/frob/gates/__init__.py    | 13 ++++++++
 tests/test_prework_parity.py  | 19 +++++++++++
 tests/unit/test_main_entry.py | 45 +++++++++++++++++++++++++
 tickets.md                    | 78 ++++++++++++++++++++++++++++++++++++++++---
 6 files changed, 202 insertions(+), 61 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/test_prework_parity.py::TestScopeDigestParity::test_digest_is_content_only_portable_across_checkouts` (pytest node id, verified passing when recorded)
