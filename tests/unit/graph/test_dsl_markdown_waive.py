"""Tests for T-1968: an unhandled `frob:<verb>` markdown directive must
be a loud, visible `MalformedDirective`, never silent prose.

T-1968's own measured evidence (`docs/modules/fuzz.md`'s `frob:waive
DOC006`, `docs/modules/deploy.md`'s `frob:waive INV003`/`INV004`,
corroborated by `frob check --only gates` reporting `gate:DOC 0 waived`)
undercounted: reading `frob.gates._docptr`/`frob.gates._inv` directly
shows BOTH rules already have their own dedicated markdown-waiver
mechanism (`_WAIVE_DOC006_RE`, `_DOC_WAIVE_MARKER_RE`) -- `0 waived`
undercounts because those mechanisms suppress the violation before it is
ever emitted (no graph-edge WaiverRef to count), not because the
directives do nothing. `_MD_WAIVE_HONORED_RULES` records every rule id
this repo's gates actually read from markdown today (REF001/REF002/
DOC004/DOC006/INV003/INV004/BUG002); this test file's "unhonored"
examples use a rule id genuinely outside that set.
"""
# frob:ticket T-1968

from __future__ import annotations

from frob.graph.dsl import markdown_anchors


class TestUnhandledMarkdownWaiveDirective:
    def test_waive_of_a_genuinely_unhonored_rule_is_reported_unparsed(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # T-1968 acceptance: place a frob:waive <RULE> in markdown and
        # assert it is reported as unparsed/ignored, not accepted
        # silently, when no gate actually reads that rule from markdown.
        text = (
            "# Perf\n\n"
            '<!-- frob:waive PERF004 reason="illustrative sorted() call" -->\n'
        )
        edges, malformed = markdown_anchors("docs/modules/perf.md", text)
        assert edges == ()
        assert len(malformed) == 1
        assert malformed[0].file == "docs/modules/perf.md"
        assert "PERF004" in malformed[0].reason
        assert "waive" in malformed[0].reason

    def test_waive_of_each_honored_rule_produces_no_finding(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # Every rule id SOME gate's own mechanism actually reads from
        # markdown today -- verified by reading each gate's own source
        # (frob.gates._refs/_docptr/_docblocks_refs/_inv/
        # _mutation_evidence), not assumed. Must never be flagged as
        # unhandled.
        for rule in ("REF001", "REF002", "DOC004", "DOC006", "INV003", "INV004"):
            text = f'<!-- frob:waive {rule} reason="genuinely handled" -->\n'
            edges, malformed = markdown_anchors("docs/x.md", text)
            assert edges == (), rule
            assert malformed == (), rule

    def test_multiple_unhonored_waivers_each_reported(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # T-1968's own measured shape -- multiple waivers, multiple rule
        # ids, one per line, all unhandled.
        text = (
            '<!-- frob:waive PERF004 reason="x" -->\n'
            '<!-- frob:waive WIRE001 reason="y" -->\n'
        )
        edges, malformed = markdown_anchors("docs/modules/example.md", text)
        assert edges == ()
        assert len(malformed) == 2
        assert {m.line for m in malformed} == {1, 2}

    def test_recognized_verbs_produce_no_unhandled_finding(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # describes/enumerates/until (markdown_anchors' own edges) and
        # generated-start/generated-end (frob.gates._docblocks' table
        # fences, T-1011) must not be flagged -- they ARE handled, just
        # not by this function's own edge-producing branch for the
        # fence markers.
        text = (
            "# H\n\n"
            "<!-- frob:describes src/x.py::Y -->\n"
            '<!-- frob:enumerates src/x.py::Z members="a,b" -->\n'
            "<!-- frob:until T-0001 -->\n"
            "<!-- frob:generated-start cli-commands T-1011 -->\n"
            "<!-- frob:generated-end cli-commands T-1011 -->\n"
        )
        _edges, malformed = markdown_anchors("doc.md", text)
        assert malformed == ()

    def test_unknown_verb_entirely_is_reported(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # Generic: ANY unrecognized verb, not just waive, is caught --
        # a future directive/file-type gap needs no new regex here.
        text = '<!-- frob:invariant something reason="x" -->\n'
        _edges, malformed = markdown_anchors("doc.md", text)
        assert len(malformed) == 1
        assert "invariant" in malformed[0].reason
