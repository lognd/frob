+++
id = "01M41H9Y7TTWDN6DAQ5C06R6B7"
title = "SYS001 reports every ledger directory as unowned (894 warnings here); the ledger is frob-owned"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-03T18:44:28Z"
updated = "2026-10-03T19:10:06Z"
scope = ["crates/grimble-bind/**", "crates/frob-check/src/product.rs", "docs/design/binding.md", "crates/grimble-check/src/lib.rs", "crates/grimble-check/src/config.rs", "crates/grimble-check/src/bind_cache.rs", "crates/grimble-check/tests/binding.rs"]

[[acceptance]]
text = "Given a repository with a ledger of N tickets and no model node covering it, when frob check runs, then SYS001 reports nothing under the ledger directory"
bound = true

[[acceptance]]
text = "Given a file outside frob-owned paths that no node owns, when frob check runs, then SYS001 still reports it"
bound = true
+++

Found by ~V92VDGB: of about 1020 check warnings on this repository, 894 are SYS001 'N unowned file(s) in tickets/<ULID>', one per ticket directory, and consumer repositories (cloc, mdcat, goway) will see the same once their ledgers grow. The ledger directory (and other frob-owned paths: changelog.d fragments, frob.lock, .frob/) belongs to frob itself, not to any node of the user's design model. frob should pass its owned paths to grimble as an implicit owner (a built-in 'frob ledger' owner in the binding owner function, or excluded from SYS001's universe), so SYS001 never reports them; the ledger path comes from configuration, not a hard-coded tickets/. Decide which of the two fits binding.md and record it there.
