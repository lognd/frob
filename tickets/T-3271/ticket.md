---
id: T-3271
title: 'frob scaffold new writes into the output dir, not <output>/<name>: contradicts
  its own quickstart and scattered a project across a user''s home'
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/scaffold_runner.py
- src/frob/scaffold/project.py
- docs/commands/scaffold.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM A REAL FIRST-USE of frob in a sibling repo (../diax,
FROBLEMS.md F-001, frob 0.530.0, 2026-08-28). Independently confirmed in the
code by the coordinator.

`frob scaffold new <type> <name>` writes the project files DIRECTLY into the
output directory, never into a `<name>/` subdirectory. Both documented forms
are wrong:

    frob scaffold new python-tool demo
        docs/commands/scaffold.md:16 says "# scaffold into ./demo/"
        actual: writes README.md, Makefile, .gitignore, frob.toml, src/demo/...
                into the CURRENT directory

    frob scaffold new python-tool demo --output /path/to/parent/
        docs/commands/scaffold.md:17 says the flag takes a PARENT
        actual: writes straight into /path/to/parent/, not
                /path/to/parent/demo/

THE CODE, confirmed:
    src/frob/app/scaffold_runner.py:91
        out_dir = cfg.scaffold_output or Path(".")
        result = render_project(proj_type, proj_name, out_dir, force=force)
    src/frob/scaffold/project.py:318 `_resolve_manifest_paths` joins each
    manifest entry under `output_dir` directly, and the manifest entries are
    bare filenames -- `_ManifestEntry("shared/python/README.md.j2",
    "README.md")`, `.gitignore`, `Makefile`, `frob.toml`. No `{{name}}/`
    component anywhere in the path templates.

The reporter's actual experience: running it from ~/projects put a whole
project's files loose in ~/projects, and they had to move every file by hand
into diax/ afterwards, checking timestamps to work out which files were even
theirs.

BOUNDING THE SEVERITY HONESTLY -- the reporter feared a clobber and there IS a
guard, so do not overstate this. `render_project` refuses ALL-OR-NOTHING when
`force` is false:

    if not force:
        for _, out_path in resolved:
            if out_path.exists():
                return Err(ScaffoldError.OutputExists)

So scaffolding into a directory that already has a README.md refuses cleanly
and writes nothing. The damage case is the one that actually happened: a
directory whose existing contents do NOT collide with the template's filenames,
where the scaffold proceeds and scatters a project across it.

WHY THIS MATTERS NOW BEYOND THE INCONVENIENCE. `frob scaffold` is a published,
user-facing command and the owner is preparing a PyPI release. This is the
FIRST thing a new user runs -- the docs' own quickstart example -- and it does
not do what the line next to it says. It is also the kind of bug that makes a
user distrust the tool immediately, because their first experience is picking
their own directory apart by hand.

DECIDE THE SEMANTICS, THEN MAKE DOCS AND CODE AGREE. Do not just patch one
side. The reporter offered both options and either is defensible:
  (a) `--output` means PARENT (what the docs say): create `<output>/<name>/`
      and write there. This makes the bare form create `./demo/`, which is
      what the quickstart claims.
  (b) `--output` means the project directory itself: rename the flag to
      `--into` and correct the docs.
(a) matches the documentation and the reporter's expectation, and is what I
would choose, but state your reasoning rather than taking my word.

ALSO IN SCOPE: whichever semantics you choose, the bare no-`--output` form
must not scatter files into the user's current directory when that directory
is an existing project. Consider refusing when the target already looks like a
project root (a .git/, a pyproject.toml) unless --force, separately from the
per-file OutputExists check -- the per-file check did not save this user.

DO NOT FIX THIS BY EDITING ONLY docs/commands/scaffold.md. The behaviour is
surprising on its own terms, independent of what the docs claim.

MUST-FIRE FIXTURE: scaffolding `demo` into a temp dir creates
`<tmp>/demo/README.md`, not `<tmp>/README.md`.
MUST-STAY-QUIET FIXTURE: an existing colliding file still refuses without
--force, and --force still overwrites. The existing OutputExists behaviour must
not regress.
THIRD FIXTURE: the bare form (no --output) run inside an existing project root
does not scatter files into it.

ACCEPTANCE
- Chosen semantics stated with reasoning; docs and code agree afterwards.
- All three fixtures present.
- `docs/commands/scaffold.md`'s quickstart lines are true statements about the
  code when you are done.
- Every scaffold TYPE is covered, not just python-tool -- the manifests are
  per-type and the join happens in shared code, so verify rather than assume.
