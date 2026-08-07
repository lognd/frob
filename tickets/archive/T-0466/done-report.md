## Done report

ref_gate now TEXT-SCANS a .md file's own bytes for `frob:waive REF001/REF002
reason="..."` and honors them for findings on that same .md file (new
_WAIVE_REF_RE / _md_waived_rules, wired into ref_gate's tier loop) -- same
posture _docblocks.py uses for DOC004, since frob.graph has no edge to attach
a waiver to on a bare doc file. So a doc-anchor 1:1 REF002 (or a .md REF001)
can now be waived with a reasoned inline directive, closing the "markdown
frob:waive is inert" gap.

Evidence (2 tests): ref002-on-md-suppressed-by-inline-waive,
ref002-on-md-without-waive-still-fires. Landed in one worktree with T-0467
(both edit _refs.py); coordinator inline-reviewed, landed via 3-way.
