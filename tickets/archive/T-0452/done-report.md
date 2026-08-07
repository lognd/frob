## Done report

New INV004 gate rule (advisory, always WARN, never fails frob check): the
section-level inverse of INV003's per-claim check. docs/**.md is split
into ATX-heading-delimited sections (`_markdown_sections`); a section
using ANY normative language at all -- must, must not, never, always,
shall, guarantees, ensures, requires, plus INV003's exclusivity
vocabulary (new `frob.gates.invariants.NORMATIVE_CLAIM_PATTERNS` /
`find_normative_claims`) -- but anchoring ZERO `frob:invariant` markers
at all (a marker naming an UNKNOWN invariant id still counts here,
unlike INV003 -- INV004 only asks "is anything tracked here") is flagged
as likely under-specified. `frob.gates.inv004_gate` is the gate entry
point.

Deliberately always WARN: this is the "silence" signal T-0452 asks for
-- a suggestion to formalize, not a broken obligation. A full repo run
surfaces 672 findings across docs/ written before this rule existed;
confirmed via `uv run frob check`: 0 new errors (1 pre-existing
unrelated error, docs/commands/sys.md DOC003, present before this
ticket started and outside its scope).

REL001: new public API (frob.gates.inv004_gate,
frob.gates.invariants.find_normative_claims,
frob.gates.invariants.NORMATIVE_CLAIM_PATTERNS) bumped pyproject.toml
0.44.0 -> 0.45.0, CHANGELOG.md entry added, uv lock refreshed, `frob
release stamp` run. Scope extended (frob ticket scope --add) to cover
pyproject.toml/CHANGELOG.md/uv.lock/.frob-release.json.

ruff check/format and ty clean under both `uv run` and bare PATH
`ruff`/`ruff format --check`. tests/test_gates.py full suite passes.

### Changed
```
 .frob-release.json           |   5 +-
 CHANGELOG.md                 |  17 +++++
 docs/modules/gates.md        |  28 +++++++++
 pyproject.toml               |   2 +-
 src/frob/gates/__init__.py   |  96 +++++++++++++++++++++++++++--
 src/frob/gates/invariants.py |  42 ++++++++++++-
 tests/test_gates.py          |  51 +++++++++++++++
 tickets.md                   | 144 +++++++++++++++++++++++++++++++++++++++++--
 uv.lock                      |   2 +-
 9 files changed, 375 insertions(+), 12 deletions(-)
```

### Evidence
(no evidence recorded)
