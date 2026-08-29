---
id: T-3410
title: scaffold docs/index.md.j2 documents four make targets T-3400 deleted, so every
  new python project ships broken instructions
state: done
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/shared/python/docs/index.md.j2
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/data/shared/python/docs/index.md.j2
  reason: 'T-3400 regression fix: docs/index.md.j2 in same directory still references
    deleted make targets'
  actor: logan
  at: '2026-08-29'
evidence:
- cmd:pytest tests/unit/test_scaffold_project.py tests/unit/test_scaffold_managed.py
  tests/system/test_scaffold_dx.py -q exit=0 sha256=f6f0a5c777f7
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3400 trimmed `src/frob/scaffold/data/shared/python/Makefile.j2` down to
install/clean/upload and correctly updated `README.md.j2` alongside it, but
missed the third file in the same directory. Every project scaffolded from
the python template now ships documentation instructing the user to run four
targets that do not exist.

MEASURED on main, 2026-08-29, after T-3400 landed:

    git grep -n "make " main -- src/frob/scaffold/data/shared/python/docs/index.md.j2
      15: make check
      21: make test        # run tests
      22: make lint        # check style
      23: make typecheck   # check types
      24: make check       # all of the above

None of `check`, `test`, `lint`, or `typecheck` survive in the trimmed
`Makefile.j2`. Its remaining targets are `install`, `clean`, and `upload`.

THIS IS A REGRESSION INTRODUCED BY T-3400, not a pre-existing inconsistency.
Before that land the targets existed and index.md.j2 was accurate. Say so
plainly in the done report; the point of noting it is that a
three-file directory was edited two files at a time, which is a repeatable
mistake rather than a one-off.

THE FIX is to bring index.md.j2 in line with README.md.j2's already-correct
framing: steer to `frob check` / `frob test` / `frob format` directly, and keep
`make install` / `make clean` / `make upload` where they genuinely remain --
bootstrap and publish cannot be frob subcommands, because `install` is what
installs frob. Match README.md.j2's wording rather than inventing a third
phrasing for the same instructions.

WHY IT MATTERS MORE THAN A DOC TYPO. This is the FIRST thing a new user of a
scaffolded project reads, and every instruction in it fails immediately with
"No rule to make target". The owner's whole reason for the T-3400 work was that
new users were receiving a contradiction between `make` and `frob`; shipping
documentation for deleted targets is a worse version of the same contradiction.

WIDEN THE CHECK BEFORE FIXING. Do not fix only the file named here. Enumerate
EVERY file in every scaffold manifest that references a `make` target by name,
and check each against the Makefile.j2 that manifest actually ships. At least
four scaffold types carry their own `frob.toml.j2` that silently shadows the
shared one, so per-type verification is required rather than assuming the shared
directory is the only source. The cpp / web-app / pyo3 / pybind11 templates
legitimately keep their Makefiles (they wrap cmake/npm/cargo, which frob has no
equivalent for) -- those references are CORRECT and must not be "fixed".
Report the full enumeration, including the files you deliberately left alone.

THE GENERAL DEFECT WORTH CONSIDERING: nothing checks that a scaffold template's
documented commands exist in the same template set's build files. A gate rule
that resolves documented `make <target>` references against the shipped
Makefile.j2 would have caught this at land time. Decide whether to build it and
say why either way -- do not build it silently as scope creep, and do not skip
mentioning it.

MUST-FIRE FIXTURE:   a scaffold doc referencing a make target absent from its
                     own template set is flagged.
MUST-STAY-QUIET:     cpp/web-app references to targets its Makefile really has
                     are not flagged.

ACCEPTANCE
- index.md.j2 corrected, matching README.md.j2's existing wording.
- Full enumeration of make-by-name references across ALL scaffold types
  reported, with the deliberately-untouched ones named and justified.
- The gate-rule question answered either way, with reasoning.
