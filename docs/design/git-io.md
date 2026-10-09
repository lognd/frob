# Git and GitHub without subprocess storms

Status: current
Owner: gob
Decisions: none
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Owner direction 2026-10-01: keep everything
automatic for the agent, but minimize process IO. v1 evidence: 370
`git`/`gh` argv literals across 34 modules; one ticket verb commonly
spawned `rev-parse`, `status --porcelain` (several times), `worktree
list`, `add`, `commit`, plus the hook fleet; every spawn paid process
start and re-read the repo from disk.

## 1. Principle

One process opens the repository ONCE and does everything through
`gix` (gitoxide) in memory. A subprocess is spawned only for the
handful of operations that need git's own conflict machinery, and
those are listed and counted. GitHub goes over HTTPS from the process,
never through `gh`.

## 2. In-process git (gix) covers

| Need | gix facility | v1 spawned |
|---|---|---|
| repo root, common dir, current worktree, HEAD, branch | `gix::discover`, `head()`, `worktrees()` | rev-parse, worktree list |
| dirty check, changed paths vs HEAD or base | `status()` with pathspec, `diff` tree-to-index and index-to-worktree | status --porcelain (x11 shapes) |
| diff vs merge base for touched set and scope checks | `merge_base`, `diff::tree` | merge-base, diff --name-status |
| read a file at a revision | `rev_parse_single`, object lookup | show REV:path, cat-file -e |
| blame, log by path, conventional-commit mining | `blame`, revwalk with path filter | log, show |
| commit the ledger | write blobs and a tree built from the ledger ref's tip plus the changed ticket directory (never from an index), `commit_as` with author from config | add, commit |
| create or move refs with compare-and-swap | `refs::transaction` with expected previous value | update-ref |
| add, list, remove worktrees | `worktree` module (add is newer: verify; fallback below) | worktree add/remove |
| config (user.name, merge drivers, hooks path) | `config_snapshot` | git config |
| tags and release lookup | refs iteration | tag, describe |

Reads are snapshot inputs (salsa inputs from milestone 2) refreshed
from one `gix` snapshot per invocation (or per file-watch event in the
server), so `check`, `ticket`, and `land` share them instead of each
asking git again.

Writes the ledger needs are blob, tree, commit, and ref updates: all
plain object writes that gix does without a worktree touch. A ticket
mutation is therefore: read the tip of the ledger ref (`[tickets] ref`,
default the trunk branch), write blobs for the changed ticket
directory, write a tree equal to the tip's tree with only that
directory replaced, commit, and update the ref by compare-and-swap. The
tree is never built from any index, so staged user changes cannot enter
a ledger commit. If the CAS loses, re-read the tip, rebuild and retry up
to `[git] cas_retries` times (a bounded count with jittered backoff,
never a deadline). The guarantee is that no accepted commit is lost and
that racing writers as a whole always make progress; it is not that
every racer wins, so a writer that loses `cas_retries + 1` times in a
row gets `E-GIT-CAS-EXHAUSTED`. When a checkout has the ledger ref
checked out, its index entries and worktree files for `tickets/` are
updated to match (refused with a remedy if those paths have local
edits). No `git add`, no `git commit`, no hooks unless the repo asks for
them (`[git] run_hooks = true` executes `pre-commit` once via one
spawn). tickets.md section 2 has the full writer story and the CI,
fork and offline cases.

## 3. The short list that may spawn

The first table is the closed list of `git` spawns. The second table
is every other class of spawn the design needs; none is git, and all go
through the same runner.

| Operation | Why | Bound |
|---|---|---|
| three-way merge of a worktree branch into the land staging tree when gix's merge reports conflicts needing rename detection or a custom driver | git's merge-ort is the reference; reimplementing conflict resolution is out of scope | at most 1 spawn per land |
| `git worktree add` if the gix worktree write path is not yet complete at the pinned version | verified at build time by a feature test; removed when gix covers it | at most 1 per `work` |
| repo-configured hooks (`pre-commit`, `pre-push`) | they are user programs by definition | 1 per commit or push when enabled |
| `git push` over SSH | gix supports fetch; push transport is newer; use git until gix push is stable | 1 per `--push` |
| user-invoked escape hatch `frob git -- ...` | debugging | explicit |

| Other spawn class | Why | Bound |
|---|---|---|
| test runners and evidence providers | they are the thing being run | one per selected runner, within `[perf] jobs` |
| `[[check.tool]]` entries (ruff, clippy, tsc, cargo doc, mdbook, lychee, typos, markdownlint, zizmor, actionlint, hadolint) | opt-in external linters and doc gates | one per configured tool, concurrent, outside the 2 s check budget |
| sibling `grimble check --json` and `crunk check --json` when not linked in | the orchestrated check | at most 1 per sibling per check |
| `grimble vet --hook`, invoked by `frob hook pre-tool` | the install guard | 1 per guarded call |
| out-of-process helpers (crunk's Tailwind runtime, playwright gallery) | stay out of process | one per crunk run |
| `frob merge-driver`, spawned by git itself | git runs the driver; it is inbound, not a frob spawn | one per conflicted ticket file |

Every spawn goes through one `gob-exec` runner that logs the argv,
duration, and exit under an `exec.spawn` span, so `frob --timing` shows
the count. A repo-internal rule (PROC001, in gob-exec) fails the build if
any crate outside its allow list references `std::process`; the allow
list is `gob-exec`, `gob-git` and `frob` (the binary, whose `main` calls
the process-exit function); `gob-git` spawns through `gob-exec`.
`gob-exec` programs: `Program::Hook` carries the hook path, `Sibling`
resolves next to `current_exe` first, and tool names are open by default
(`Runner::allow_tools` restricts them).
`gob-git` as built (gix 0.87.1): `commit_paths` takes `index.lock` when
the ref is checked out; the local-edits check runs the on-disk bytes
through gix's filter pipeline (core.autocrlf and `.gitattributes` safe)
before comparing; `merge_branch` decides "up to date" in gix and
otherwise spawns one `git merge`; a name without `refs/` resolves as
`refs/heads/<name>`.
`gob-git` also owns the one worktree-content normalizer
(`Repo::worktree_content_as_git`, `WorktreeSource`): a symlink reads as
its target string and a regular file runs through the same clean filters.
Every digest compared with recorded state goes through it (`gob-walk`'s
`ContentSource` for walk digests and symbol extraction), so a CRLF
checkout under `core.autocrlf` hashes like its LF twin. Parsed text is the
normalized text, so spans are offsets into it; line numbers are identical
in both forms.

Measured target: a typical ticket verb spawns zero processes; `land`
spawns at most two git processes (merge fallback, hooks); `check` spawns
only the configured external tools and siblings.

## 4. GitHub without `gh`

Milestone 2 or later (D36). `frob-gh` (frob only; grimble and crunk have
no GitHub features) talks to the REST and GraphQL API directly
(`octocrab` or a thin `reqwest` client with `ureq` for the sync paths)
using the token from `GH_TOKEN` or `GITHUB_TOKEN`; it does not read
`gh`'s config file, because current `gh` keeps its token in the OS
keyring. Operations: open or update a PR for a landed ticket, read CI
run status and failing jobs, create a release from the milestone, read
issues for `frob migrate tickets --from-github`. Responses are cached
by ETag in `.frob/`. If no token is present the feature reports
`unavailable` with the remedy; it never shells out to `gh` to borrow its
login.

## 5. Hooks and the agent harness

v1 spawned up to eight python processes per agent Bash call. v2 ships
one `frob hook <event>` entry that reads the hook JSON on stdin,
evaluates all registered guards in-process (suggest frob verbs, root-
write guard, directive guard, telemetry), and exits. `pre-tool` invokes
`grimble vet --hook` as a sibling spawn when grimble is configured. One
small-binary start per event, no interpreter. Milestone 2 or later
(D36); v1 hooks keep running meanwhile.

## 6. Daemon option

Milestone 2 or later (D36). `frob serve` (MCP and HTTP) keeps the gix
repository, the salsa db, and the SQLite index open. When a daemon for
the repo is running, the CLI connects over a Unix socket and the command
executes in the warm process, so even the one process start per verb is
the thin client. The CLI never requires the daemon; it is an
optimization that falls back to in-process execution transparently. Two
safeguards: the CLI and daemon handshake on binary version and schema
version and the CLI refuses to forward on a mismatch (running
in-process instead); and before serving a request the daemon re-stats
the request's inputs, so an edit made a moment ago is never answered
from a stale watcher state. On Windows there is no Unix socket: the
transport is a named pipe, or in-process only until that exists.

## 7. Verification

- A test harness counts spawns (via the `gob-exec` registry) per CLI
  scenario and snapshots the counts; a change that adds a spawn to a
  ticket verb fails review.
- gix write paths (commit, CAS ref, worktree add) are covered by
  integration tests against a real temp repo and compared byte-for-
  byte with what `git` produces for the same inputs.
