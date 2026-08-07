## Done report

Triaged the 32-finding REF002 single-anchor pool (`uv run frob check
--only refs`). 31 of 32 were already covered by pre-existing waivers
(28 litmus-fixture waivers following the established "read by exactly
one dedicated test module by design" precedent; 2 lang-walker-module
waivers following the T-0450 "private per-language walker imported only
by its sibling aggregator" precedent; those needed no new action).

The one genuinely unwaived finding was `invariants/INV-007.md`: its real
consumers are `docs/modules/bind.md`'s `<!-- frob:invariant INV-007 -->`
anchor and `src/frob/bind/__init__.py`'s `# frob:invariant INV-007`
directive, both of which reference it by invariant ID -- a shape the
refs gate's textual path/basename matcher does not recognize, so it only
counted a synthetic `tests/test_gates.py` fixture (which constructs an
unrelated file that happens to share the basename `INV-007.md` in a
tmp_path) as the sole inbound reference. Added one natural doc-reference
sentence to `docs/modules/bind.md` pointing readers at the real
`invariants/INV-007.md` file -- a genuine second literal-path consumer,
not a fabricated one.

`uv run frob check`: gate:REF went from 32 warnings/31 waived (1
unwaived) to 31 warnings/31 waived (0 unwaived). No other gate's counts
changed. Full `frob check` is clean (0 errors).

### Changed
```
 docs/modules/bind.md              |   3 +
 src/frob/gates/_pii_structural.py | 167 ++++++++++++++++++++++++++++++++++++--
 tickets.md                        |  88 +++++++++++++++++++-
 3 files changed, 249 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestTiers::test_one_ref_weak_warns_ref002` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReferenceDetection::test_markdown_link_counts_as_a_reference` (pytest node id, verified passing when recorded)
