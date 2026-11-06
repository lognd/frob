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
| DUP001 | [DUP001](../reference/rules/DUP001.md) | shipped: block copied `dup_min_occurrences` or more times |
| DUP002 | [rules index](../reference/rules/README.md) | reserved: no page yet, generated pages appear with the rule |
| DUP003 | [DUP003](../reference/rules/DUP003.md) | shipped: the clone index is missing or damaged |

Rule pages are generated (`cargo dev gen rules`); do not hand-write
the DUP002 page.

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
