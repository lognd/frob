## Done report

New INV003 gate rule (WARN severity): a docs/**.md file making an
exclusivity/normative claim -- "only", "sole"/"solely", "exclusively",
"nothing else", "never...except", "at most/exactly one"
(`frob.gates.invariants.EXCLUSIVITY_CLAIM_PATTERNS` /
`find_exclusivity_claims`, the exclusivity-word corpus this ticket names)
-- with no `<!-- frob:invariant INV-### -->` marker in the same file
naming a real, loaded invariant (`frob.gates.inv003_gate`).

Deliberately WARN, not ERROR like INV001/INV002: bare "only" is common
enough in existing prose that a first repo-wide run surfaces 88
findings across docs/ written before this rule existed. Promoting
straight to ERROR would force either a mass reword/binding pass
unrelated to this ticket's own scope, or markdown-side `frob:waive`
support that does not exist yet (`_match_waiver` keys off graph edges;
doc prose carries none today). Disclosed as a design tradeoff in
docs/modules/gates.md's new "INV003 (T-0462)" section and in
inv003_gate's own docstring; hardening to ERROR (or building markdown
waiver support) is explicitly named as follow-up, not silently dropped.
No existing doc needed rewording/binding to stay green because WARN
does not fail `frob check` -- confirmed via a full `uv run frob check`:
1 pre-existing unrelated error (docs/commands/sys.md DOC003, present
before this ticket started, outside its scope), 0 new errors.

REL001: new public API (frob.gates.inv003_gate,
frob.gates.invariants.find_exclusivity_claims,
frob.gates.invariants.EXCLUSIVITY_CLAIM_PATTERNS) bumped pyproject.toml
0.43.0 -> 0.44.0, CHANGELOG.md entry added, uv lock refreshed, `frob
release stamp` run. Scope extended (frob ticket scope --add) to cover
pyproject.toml/CHANGELOG.md/uv.lock/.frob-release.json for this reason.

ruff check/format and ty both clean under `uv run` (project-pinned) and
bare PATH `ruff`/`ruff format --check` (playbook section 12).

### Changed
```
 tickets.md | 64 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 62 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)
