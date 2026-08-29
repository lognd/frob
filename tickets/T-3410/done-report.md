## Done report

REGRESSION, STATED PLAINLY: T-3400 introduced this bug. It trimmed
shared/python/Makefile.j2's format/lint/typecheck/test/coverage/check
targets and updated README.md.j2 to match, but did not check
docs/index.md.j2 in the same directory, which still cited the deleted
targets. Before T-3400 landed, index.md.j2 was accurate; this is a
three-file directory (Makefile.j2, README.md.j2, docs/index.md.j2)
edited two files at a time -- a repeatable mistake, named as one here
rather than described as a pre-existing inconsistency.

FIX: docs/index.md.j2's Quick start / Development sections rewritten to
match README.md.j2's wording verbatim (frob check / frob test / frob
format / frob coverage, with make install/clean/upload named as the
remaining real targets). Only the "Modules" section (unique to
index.md.j2) and the .env line (unique to README.md.j2) differ between
the two files now, by design.

FULL ENUMERATION (every scaffold file citing a `make <target>` by name,
checked per manifest type against the Makefile.j2 it actually ships --
git grep -n -oE "\bmake [a-z_-]+" over src/frob/scaffold/data/, then each
verified against src/frob/scaffold/project.py's _ManifestEntry tables so
a type's OWN frob.toml.j2/Makefile.j2 override is not missed):

  FIXED (this ticket):
  - shared/python/docs/index.md.j2 -- python-library's docs/index.md
    (python-tool overrides docs/index.md.j2 with its own file, which has
    ZERO make citations, so python-tool was never affected).

  ALREADY CORRECT (T-3400's own land, verified again here):
  - shared/python/README.md.j2 -- used by both python-tool and
    python-library.

  DELIBERATELY LEFT ALONE, with reasons:
  - shared/cpp/README.md.j2, shared/cpp/docs/index.md.j2 (cpp-library,
    cpp-tool): only "cmake" substring matches, zero real `make <target>`
    citations. cmake/ctest is the real toolchain; nothing to fix.
  - types/pyo3-library/README.md.j2: cites make check/test/lint/
    typecheck/coverage/build -- all six exist verbatim in
    types/pyo3-library/Makefile.j2 (its own override, cargo+ruff+ty
    mixed real logic). types/pyo3-library/docs/index.md.j2 has zero make
    citations, so no risk there either.
  - types/web-app/README.md.j2: cites make test/lint/typecheck/coverage/
    check -- all five exist verbatim in types/web-app/Makefile.j2 (its
    own override, npm-wrapped). types/web-app/docs/index.md.j2 has zero
    make citations.
  - types/python-tool/docs/index.md.j2: its own override of docs/index.md,
    zero make citations to begin with -- never touched by T-3400's
    Makefile trim in the first place.
  - shared/README.md.j2 (the top-level scaffold README template): zero
    make citations.

  Net: exactly ONE broken reference set existed (docs/index.md.j2, used
  by python-library only), now fixed. Every other manifest's make
  citations were verified to resolve against the Makefile.j2 that type
  actually ships, respecting per-type overrides rather than assuming
  shared/ is the only source (checked project.py's _ManifestEntry table
  directly, not inferred from directory layout).

GATE-RULE QUESTION, ANSWERED: yes, a rule resolving documented `make
<target>` references against the shipped Makefile.j2 would have caught
this at land time, and is worth building -- but NOT inside this ticket.
DOC010/docmake_gate (src/frob/gates/_docstatus.py) already does exactly
this check for real repo docs (resolves `make <target>` citations
against the nearest Makefile, T-2705), but it structurally cannot cover
scaffold .j2 templates: (1) _obligated_docs only scans real,
frob:doc-obligated markdown, never .j2 template source; (2)
_makefiles_for_doc resolves by directory-nearest-Makefile walk, but a
scaffold doc's effective Makefile is decided by project.py's manifest
COMPOSITION (shared vs. per-type override), not filesystem proximity --
this enumeration's own finding (>=4 types independently override
Makefile.j2) proves a naive directory-walk extension would mis-pair or
miss overrides. Filed T-3415 ("Extend DOC010/docmake_gate to
scaffold .j2 template pairs") with a concrete design (manifest-aware
resolver reusing docmake_gate's existing regex/target-parsing) rather
than building it silently as scope creep on this ticket.

Evidence: pytest tests/unit/test_scaffold_project.py
tests/unit/test_scaffold_managed.py tests/system/test_scaffold_dx.py -q
(exit=0, 27 passed).

Filed: T-3415.

### Changed
```
 .../scaffold/data/shared/python/docs/index.md.j2   | 16 +++--
 tickets/T-3410/ticket.md                           |  5 +-
 tickets/T-3415/ticket.md                 | 76 ++++++++++++++++++++++
 3 files changed, 91 insertions(+), 6 deletions(-)
```

### Evidence
- `cmd:pytest tests/unit/test_scaffold_project.py tests/unit/test_scaffold_managed.py tests/system/test_scaffold_dx.py -q exit=0 sha256=f6f0a5c777f7` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 17 error(s), 3946 warning(s), 857 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC006@tickets/T-1382/ticket.md, DOC006@tickets/T-3411/ticket.md, DOC011@docs/modules/tickets.md, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, SYS003@src/frob/gates/__init__.py, SYS003@src/frob/tickets/_scope_coverage.py, SYS003@tests/unit/test_nodeid.py, TEST001@src/frob/lang/__init__.py, TEST001@src/frob/lang/_extract.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/nodeid.py
