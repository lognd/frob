# Dup: duplicate-code tiers and their cost

Status: draft
Owner: grimble
Decisions: none
Audience: contributor

Provenance: ticket ~107NYEF. Documents the clone tiers used by the
duplicate-code rule family. This file changes no code.

## Tiers

The duplicate-code check finds token blocks that occur at several places
in the walk. A copy matches at one of three rungs, strictest first. A
block reported at a stricter rung is not reported again at a looser one.

| Tier | Rung | Match | Relative cost |
|---|---|---|---|
| 1 | R1 | the exact tokens | lowest: hash the token stream as is |
| 2 | R2 | tokens with identifiers consistently renamed | medium: alpha-rename identifiers per window before hashing |
| 3 | R3 | token shape, names and literals abstracted to their kind | highest: most candidate windows collide and need verification |

Cost grows with the rung because a looser match produces more hash
collisions to confirm. Raise `dup_min_tokens` to cut cost on large repos.

## Rules

| Rule | Page | Status |
|---|---|---|
| DUP001 | [DUP001](../reference/rules/DUP001.md) | shipped: exact (R1) block copied `dup_min_occurrences` or more times |
| DUP002 | [DUP002](../reference/rules/DUP002.md) | shipped: renamed (R2) or same-shape (R3) block copied `dup_min_occurrences` or more times |
| DUP003 | [DUP003](../reference/rules/DUP003.md) | shipped: the clone index is missing or damaged |
| DUP004 | [DUP004](../reference/rules/DUP004.md) | shipped: a function in a changed file has the same statement shapes as another function |

Rule pages are generated (`gob-dev gen all`) from the rule files.
Both are Error by default with no opt-in knob; adopt existing clones with
`frob baseline adopt`, so only a diff that adds a new cluster fails.

## The clone index

Provenance: ticket ~XJ1W4P0. `DUP001` caches the window hashes of each
file in `<git common dir>/frob/dup-index`, so the primary checkout and
every linked worktree share one store. An entry is named by the digest of
the file text, the window size (`dup_min_tokens`), the language style and
the format version, so a changed file gets a new entry and an unchanged
file is never hashed again: the index is built once and updated only for
changed files. Entries are written through a temp file and a rename, so
concurrent worktrees never see half an entry. Outside a git checkout
there is no index and every run computes the hashes.

The store fails closed. If the directory exists but its manifest is
missing or foreign, an entry is truncated or fails its checksum, or the
store cannot be written, the check reports `DUP003` with the path and
the hint to delete that directory, and `DUP001` is not evaluated for that
run. Only the first build, when the directory does not exist yet, is
silent. Bump `FORMAT` in `dup_index.rs` whenever the lexer or the window
hash changes.

## Structural clones (DUP004)

Provenance: ticket ~NQ5SB96. The token windows need the copy to keep its
statement order. `DUP004` instead fingerprints each function by the sorted
multiset of its statement shapes (the R3 token abstraction applied per
statement; statements end at `;` and braces, or at a line break for
Python and shell), so a renamed and reordered copy has the same
fingerprint. It runs only with a base ref (`frob check --base`, which
`frob land` passes): the changed set is the diff of the work tree against
the merge-base, and a class is reported only when one member sits in a
changed file, so a land pays only for what it touches. The changed-set
digest is part of the arch report cache key. Classes that keep statement
order and reach `dup_min_occurrences` stay with `DUP002`. It reuses
`dup_min_tokens` as the minimum function size and covers Rust, Python,
TypeScript, C#, Java, C, C++, Go and shell. Limit: scoping is per changed
file, not per changed hunk.

## Knobs

`[grimble] dup_min_tokens` (default 50; 0 disables) and
`dup_min_occurrences` (default 3; below 2 disables). See
[the config reference](../reference/config/frob.md).

## Baselining existing clones

DUP001 is an Error by default, so a repository with existing clones adopts
them once instead of failing: `frob baseline adopt DUP001 --reason "<why>"
--ticket <owner>`. Every adopted entry in `frob-baseline.toml` carries that
reason and owner ticket. Baselined clusters stop failing the gate but stay
visible in the `baselined` section of `frob check`; a new cluster is not in
the file and still fails. `frob baseline prune` drops entries whose cluster
is gone.
