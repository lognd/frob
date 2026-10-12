# Paths: one discipline from type to lint (D86)

Status: draft
Owner: gob
Decisions: D86
Audience: contributor

Provenance: accepted direction, owner request 2026-10-03 ("structural and
powerful, not a cheap hotfix"). The `/` versus `\` difference broke this
repository's CI on every first Windows run: the merge driver command
line, the command-tool allowlist compare, a `--cwd` string compare, a
fixture name. Each was code that compiles everywhere and is wrong on one
platform. A lint alone finds some of them after they are written. This
design makes the wrong thing hard to write, checks the rest at compile
time, verifies both path styles on one host, and keeps the PATH lint
family (rules.md 3.1) as the second line and as the product feature for
other repositories.

## 1. Three kinds of path, three types

| Kind | Type | Separator | Where it lives |
|---|---|---|---|
| Host path: a file on this machine | `std::path::{Path, PathBuf}` | the platform's | in memory, in process arguments, never persisted |
| Repository path: a file named relative to a repository root | `gob_path::RelPath` | `/` by contract | everything persisted or compared across machines: ledger, `frob.lock`, `grimble.lock`, findings JSON, config values, scope globs, the sibling contract |
| Display path: text for a person | `gob_path::Shown` (render-only) | the platform's, home shown as `~` | the rendering layer only |

`RelPath` moves from gob-git to a new leaf crate, `gob-path`, and
becomes the one repository-path type for every crate (25 files use it
today). Its constructors are the only bridges between kinds:

- `RelPath::from_host(root: &Path, p: &Path) -> Result<RelPath>`:
  strips the root by components (`Path::strip_prefix`, never string
  prefixes), refuses a path outside the root, joins components with `/`,
  and refuses a component that is not valid on every supported platform
  (reserved device names, `<>:"|?*`, trailing dot or space, `\`), so a
  name that breaks a Windows checkout cannot enter the repository's data.
- `RelPath::to_host(&self, root: &Path) -> PathBuf`: joins components
  with `Path::join`.
- `Shown::of(p: &Path)`: the only path-to-text conversion for people;
  it scrubs the home directory to `~` (the same rule as the ledger scrub
  of ~33PZ67A, one function).

Persisted model types hold `RelPath`, never `PathBuf` or a path in a
`String`. A host path that must be recorded (a lease's worktree in the
local registry under `.git/`) is local data and says so in its type
(`LocalPath`, not serialized into anything committed).

## 2. Command lines: arguments, never strings

Processes take an argument vector of `OsString` through gob-exec
(PROC001 already confines spawning there); a path is passed as its own
argument and never interpolated. The few places a whole command line
must be one string, because another program parses it (git's
`merge.<driver>.driver` and hook lines, a `.ps1` body, a `sh -c` script),
go through one function:

`gob_exec::command_line(shell: Shell, argv: &[Arg]) -> String`, with
`Shell::{Posix, GitForWindowsSh, PowerShell, Cmd}` and per-shell quoting.
It is property-tested by round trip: for random argv (spaces, quotes,
backslashes, drive letters, `$`, `%`, non-ASCII), splitting the produced
line with a reference splitter for that shell returns the argv exactly.
`frob init` writes the merge driver through it.

## 3. Compile-time confinement

The workspace `clippy.toml` lists `disallowed-methods` for every
path-to-text conversion (`Path::to_str`, `Path::to_string_lossy`,
`Path::display`, `OsStr::to_str`, `OsStr::to_string_lossy`, and their
`PathBuf` and `OsString` forms) and `disallowed-types` for `PathBuf` in
modules that define persisted types. gob-path is the one crate allowed to
use them (an `#[expect]` with a reason at each site); everything else
goes through `RelPath`, `Shown` or `Arg`. This is the same mechanism as
the owner's "one renderer, no `println!` scattered" rule, and it fails
`cargo clippy -D warnings`, so a new conversion cannot land. The 255
existing conversions in 105 files migrate crate by crate; each
migration ticket ends with that crate free of the allow list.

### 3.1 Canonicalization and the deletion jail (~EDPHHFS)

`std::fs::canonicalize` returns a verbatim path (`\\?\C:\...`) on Windows that git and
most tools reject, so it is in `disallowed-methods` (with `Path::canonicalize`) and
`gob_exec::canonical` is the one function that calls it: it strips `\\?\` and `\\?\UNC\`
when every component survives without the prefix (no dot component, reserved device name,
trailing dot or space, `<>:"|?*`, and under `MAX_PATH`), else keeps the verbatim form. Every
product and test call site goes through it. The pure style functions beside it
(`has_dot_component`, `strictly_inside`, `simplify_verbatim`) work on text in either `Style`, so
the Windows rules are tested on Linux.

The garbage collector's jail refuses any `.` or `..` component, split on both `/` and `\\`
in every style, before it touches the file system, and compares canonical forms by whole
normalized components. Note that `PathBuf::join` and `push` onto a verbatim path resolve `..`
lexically on Windows: a test that builds a dotdot path with `join` there tests a different
path than it names, so such inputs are built as text. Until the fix is proven on Windows CI the
automatic pass only reports on Windows (`report_only`).

## 4. Both path styles verified on one host

gob-path's logic is written once over a path-style parameter using the
`typed-path` crate (pure-Rust Unix and Windows path semantics on any
host), so the bridges and the component validation are property-tested
with Windows paths on this Linux host: drive letters, UNC prefixes,
mixed separators, case, reserved names. Platform `std::path` is used
only at the outer edge, where the style is the host's. Three layers then
verify the real platform: the Windows-target clippy check before push
(~RBF6057, compile-only), the windows-latest CI job, and `goway run
--host win` before push once the goway Windows host lands (~XKXW2BJ in
goway).

## 5. The lint: PATH, for everyone else

Inside this repository the types and clippy confinement are the primary
defence. The PATH family (rules.md 3.1) is the product feature that
brings the same discipline to other repositories and other languages:
PATH001 absolute host path literal, PATH002 separator literal on a path
turned into a string, PATH003 path pasted into a command-line string.
Their remedies name the structural fix (a repository-path type, argv,
one quoting function) rather than a local patch. TICK004 is the data
counterpart for the ledger. In this repository the PATH rules also
check that nothing slips past the confinement through a different
spelling (a format string, a macro).

## 6. Order

1. gob-path crate: `RelPath` moved and extended, `Shown`, component
   validation, typed-path property tests; gob-git re-exports for one
   release.
2. `gob_exec::command_line` with round-trip property tests; the merge
   driver and every other single-string command line use it.
3. clippy confinement on, with the allow list initially covering the
   crates not yet migrated; one ticket per crate group removes its
   entries until the list holds only gob-path.
4. Persisted types audited to `RelPath` (ledger, locks, findings, config).
5. PATH family in GRL (~21PHK3V), with this repository's bugs as corpus.
