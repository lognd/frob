# Reading a scaffolded frob.toml (T-4761)

Every scaffolded project ships one `frob.toml`, ordered top to bottom the
same way for every type: `[profile]`, `[testing]` (plus its
`[[test.runner]]` entries), `[gates.severity]`, `[tickets]`, then
`[[refs.entrypoint]]`. A bare `check_base = "main"` line precedes the
first table -- it is a repo-wide setting frob itself needs, not part of
any table. Every table header is preceded by one plain-English comment
saying what the table controls and when you would edit it; none of those
comments name a ticket or narrate how the file got this way -- that
history belongs in the ticket that changed it, not in a file every new
project ships with.

## `check_base`

```toml
check_base = "main"
```

The branch `frob check --base` diffs the working tree against (touched-
set tests, drift checks, and friends all key off this). Change it if your
repo's default branch is not `main`.

## `[profile]`

```toml
[profile]
profile = "rapid"
```

How strict the gates are. A brand-new project starts on `"rapid"` -- a
lighter bar while the codebase is small and mostly boilerplate. frob's
own one-way auto-ratchet upgrades this to `"standard"` automatically once
the project grows past a size threshold; there is no auto-downgrade, only
an explicit `frob profile downgrade` if you genuinely need to go back.

## `[testing]`

```toml
[testing]
min_unit_cases = 1
min_integration = 1
unit_branch_cov = 50
module_line_cov = 50
system_line_cov = 50

[[test.runner]]
language = "python"
command = ["uv", "run", "pytest", "-q", "{ids}"]
all_command = ["uv", "run", "pytest", "-q"]
cwd = "."
```

The coverage/case-count floors `frob check`'s TEST/COV gate family
enforces, and the runner(s) `frob test` shells out to per language. The
floors start low (a fresh project has one smoke test per symbol, not
three) -- raise them as the real test suite grows. A polyglot type (pyo3,
for instance) declares one `[[test.runner]]` block per language; `frob
test` dispatches `{ids}` (the touched-set node ids) to whichever
runner(s) apply.

## `[gates.severity]`

```toml
[gates.severity]
```

Empty by default. Severities come from the profile above; this table
exists only so a project can override one specific rule's severity
(promote a warning to an error, or the reverse) without touching the
profile as a whole. A rendered scaffold never lists per-rule severities
here -- that would be duplicating the profile's own defaults for no
reason.

## `[tickets]`

```toml
[tickets]
default_milestone = "0.1.0"
```

The milestone a new ticket defaults onto when none is given explicitly.
Set to match the project's own starting version; change it as the
project's milestones evolve.

## `[[refs.entrypoint]]`

```toml
[[refs.entrypoint]]
path = "scripts/bump_version.py"
reason = "release-time executable run by the `upload` Makefile target and CI, never imported by tracked source"
```

`frob check`'s anti-orphan gate (REF001/REF002) expects every tracked
file to be referenced from at least one other tracked file -- true for
ordinary source and docs, false for a file some OUTSIDE tool reads by
path convention (a CI workflow, a build tool's own manifest, a human
reading a README). Each row here is one such genuine exception: the path
(a literal, or a glob like `.github/workflows/*.yml`), and a one-line
reason a reviewer can check without re-deriving it.

Ordinary scaffold conventions (a `Makefile`, an `invariants/.gitkeep`
placeholder, a CI workflow file) are the same shape on every project of a
given type, so a landed refs-gate update recognizes them automatically
without a declaration; only a project's own genuine exceptions belong in
this table once that update ships. Until then, a rendered scaffold still
lists those ordinary conventions explicitly (each row's reason says so)
so a fresh checkout stays green rather than failing on the gate's own
current gap -- see the ticket that update is tracked under for the
follow-up that trims this table down.

## What is deliberately NOT here

- **No `*_schema` tables.** Those validate frob's OWN config shape; a
  project's `frob.toml` declares values, never the schema those values
  are checked against.
- **No per-rule severities beyond a genuine override.** They come from
  `[profile]`.
- **No ticket ids or change-history prose in a table's leading comment.**
  A comment says what the table does and when you would touch it; why it
  looks the way it does today belongs in the ticket that shaped it.
