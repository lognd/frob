# Changelog fragments

Status: current
Owner: frob
Decisions: none
Audience: contributor

Every user-visible change carries one fragment in `changelog.d/`. At release,
`frob release changelog --version X` compiles them into a new section at the top
of `CHANGELOG.md` and removes them. `CHANGELOG.md` is never hand-edited between
releases; the frob v1 history lives in [CHANGELOG-v1.md](../../CHANGELOG-v1.md).

## Fragment files

`changelog.d/<ulid>.<type>.md`

- `<ulid>` is the ULID of the ticket that shipped the change; it must resolve to a
  ticket in the ledger (the entry cites its handle and full ULID in plain text, never a path).
- `<type>` is one of `notice`, `added`, `changed`, `fixed`, `removed`,
  `deprecated`, `security`; this is also the rendering order. A `notice` is the
  lead notice: one paragraph rendered above everything else in the section, with
  no type heading. A release section takes at most one; a second is refused with
  the files named. Its product prefix, if any, is dropped (a notice speaks for
  the whole release).
- The body is one or two user-facing sentences, ASCII only. A first-line prefix
  names the product: `frob:`, `gob:`, `grimble:` or `crunk:`. Without a prefix the
  entry belongs to `frob`. A prefix that is a near-miss of a product (`grimbel:`)
  is refused with a did-you-mean; other leading words such as `Note:` are text.

## The command

| Form | Effect |
|---|---|
| `frob release changelog --version X` | write the section, then remove the compiled fragments |
| `... --dry-run` | print the section (in the response `data.section`), change nothing |
| `... --check` | validate every fragment and that every older section is unedited (for CI) |
| `... --date YYYY-MM-DD` | section date (default today; fixed for reproducible output) |
| `frob release notes --version X` | print one version's section body (no heading, no integrity marker) in `data.notes` (`--text` prints just the section, raw, so `--text > notes.md` is a notes file), for `gh release create --notes-file`; refuses with `E-CHANGELOG-NO-SECTION` when CHANGELOG.md has none |

An empty `changelog.d/` adds nothing and reports `already: true`. Invalid
fragments are all listed at once, each naming its file and the remedy, and exit
3 (refusal). A version already present is refused. The CHANGELOG is written
through a temporary file and a rename, and the fragments are removed only after
that succeeds.

## Writing a fragment

`frob ticket fragment TICKET [--type T] [--sentence S] [--force]` writes the file
into the ticket's worktree. Without `--sentence` the text defaults to
`<ticket title>.` with no product prefix, except for `bug`, `security` and `incident` tickets: their
titles describe the problem, so the verb exits 2 and shows
`frob ticket fragment TICKET --sentence "<what changed for the user>"`.
A repository that wants a prefix on every skeleton sets `[release] fragment_prefix`
in `frob.toml` (for example `"frob: "`); it defaults to empty.

## Section shape

```text
## X.Y.Z - YYYY-MM-DD

Read this before upgrading. (~R8CA0D, 01M4069QWSJEH5KW8K0YR8CA0D)

### frob

#### Added

- Added a thing. (~R8CA0D, 01M4069QWSJEH5KW8K0YR8CA0D)

<!-- frob-section: X.Y.Z blake3:<hash> -->
```

The lead notice comes first, above the product headings. The rest is grouped by product (frob, gob, grimble, crunk), then by type, then
by ULID. The closing marker is a BLAKE3 hash of the section; `--check` fails
with `E-CHANGELOG-EDITED` when a section no longer matches it, so a hand edit of
an older section is caught without consulting git history.
