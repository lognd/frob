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
# frob:ticket T-1989

from __future__ import annotations

from frob.graph._models import EdgeKind
from frob.graph.dsl import markdown_anchors


# frob:ticket T-1989
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

    # frob:ticket T-1989
    def test_unknown_verb_entirely_is_reported(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # Generic: ANY unrecognized verb, not just waive, is caught --
        # a future directive/file-type gap needs no new regex here.
        # T-1989: `invariant` moved to `_MD_HANDLED_VERBS` (a real reader,
        # `frob.gates._inv`, exists for its markdown-side marker) so it no
        # longer stands in for "genuinely unrecognized" here -- a verb
        # nothing owns anywhere in the codebase is the correct fixture.
        text = '<!-- frob:bogus-verb-xyz something reason="x" -->\n'
        _edges, malformed = markdown_anchors("doc.md", text)
        assert len(malformed) == 1
        assert "bogus-verb-xyz" in malformed[0].reason


# frob:ticket T-1989
class TestMarkdownDirectiveMentionVsUse:
    """T-1989: T-1968's land took the unscoped floor from 0 to 105 DSL001
    errors, because a `frob:` verb quoted as a worked EXAMPLE inside
    markdown's own `` `...` ``/```` ```...``` ```` code-span syntax --
    documentation demonstrating the DSL's own grammar, or a CHANGELOG
    entry recording a past waiver -- was parsed exactly the same as a
    live directive. `_blank_code_spans` fixes the mention half; this
    class is the acceptance test named in T-1989's own body: one case
    that must NOT raise (a mention inside an inline-code span), one that
    still MUST (a genuinely unhandled live directive, same shape, no
    backticks) -- proving the fix discriminates by code-span membership,
    not by silencing DSL001 wholesale."""

    # frob:ticket T-1989
    def test_unhandled_verb_inside_inline_code_span_is_a_mention_not_a_finding(
        self,
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # T-1989 measured shape (docs/modules/graph.md, docs/modules/
        # gates.md, CHANGELOG.md): a doc explaining the DSL quotes an
        # example directive inside single backticks. This must produce
        # NO MalformedDirective -- it is prose ABOUT the syntax, not a
        # live directive, the same mention/use distinction T-1970
        # established for `frob:quote(...)`, here applied automatically
        # to markdown's own code-span convention instead of requiring an
        # author to hand-wrap every worked example.
        text = (
            "A real waiver looks like "
            '`<!-- frob:waive DOC006 reason="..." -->` in this repo.\n'
        )
        _edges, malformed = markdown_anchors("doc.md", text)
        assert malformed == ()

    # frob:ticket T-1989
    def test_unhandled_verb_outside_any_code_span_still_raises(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # Same rule id, same verb, NO backticks -- a genuinely live,
        # unhandled directive must still be reported loud. This is the
        # class T-1968 exists to surface (docs/guides/install.md's real
        # `frob:waive SCOPE001`, T-1989's own measured incident) --
        # code-span masking must never become a way to silently re-hide
        # a real defect.
        text = '<!-- frob:waive SCOPE001 reason="..." -->\n'
        _edges, malformed = markdown_anchors("doc.md", text)
        assert len(malformed) == 1
        assert "SCOPE001" in malformed[0].reason

    # frob:ticket T-1989
    def test_unhandled_verb_inside_fenced_code_block_is_also_a_mention(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # The other code-span shape: a fenced ``` block showing a
        # directive as sample text (e.g. a "how to write a waiver"
        # snippet) must not be parsed as live either.
        text = (
            "```\n"
            '<!-- frob:waive SCOPE001 reason="example" -->\n'
            "```\n"
        )
        _edges, malformed = markdown_anchors("doc.md", text)
        assert malformed == ()

    # frob:ticket T-1989
    def test_ticket_directive_in_markdown_produces_a_ticket_edge(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # T-1989: `<!-- frob:ticket T-#### -->` is markdown's own
        # bare-target provenance tag (35 sites at measurement time,
        # docs/strata/*.md and others) -- now a real TICKET edge, the
        # same disposition `_UNTIL_RE` already gets, not an unhandled
        # directive.
        text = "# H\n\n<!-- frob:ticket T-0042 -->\n"
        edges, malformed = markdown_anchors("doc.md", text)
        assert malformed == ()
        assert len(edges) == 1
        assert edges[0].kind == EdgeKind.TICKET
        assert edges[0].target == "T-0042"
        assert edges[0].src == "doc.md#h"

    # frob:ticket T-1989
    def test_doc_directive_in_markdown_produces_a_doc_edge(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        # T-1989: `<!-- frob:doc <target> -->` is markdown's own
        # bare-target self-anchor tag (18 sites at measurement time,
        # mostly self-referencing `path#slug`) -- now a real DOC edge.
        text = "# H\n\n<!-- frob:doc doc.md#h -->\n"
        edges, malformed = markdown_anchors("doc.md", text)
        assert malformed == ()
        assert len(edges) == 1
        assert edges[0].kind == EdgeKind.DOC


# frob:ticket T-1994
class TestChangelogMultiLineCodeSpanMention:
    """T-1994: `_blank_code_spans` only masks a SAME-LINE inline-code
    span (its own docstring, and T-1989's own investigation into why a
    whole-file multi-line pairing regex is unsafe -- docs/modules/
    gates.md alone carries an odd total backtick count, so non-greedy
    file-wide pairing silently mispairs everything downstream of one
    stray backtick). CHANGELOG.md's T-0509 entry used to quote a
    `frob:waive`-verb HTML-comment example as prose, wrapped across two
    physical lines by prose-wrapping -- invisible to the same-line-only
    mask, so it was reported as a live, unhandled directive (DSL001).
    Fixed by rewrapping the example onto one physical line rather than
    teaching the masker to span lines. This reads the REAL repo
    `CHANGELOG.md` (not a fixture) so a future reflow/rewrap regressing
    this back onto two lines is caught."""

    # frob:ticket T-1994
    def test_real_changelog_has_no_malformed_markdown_directive(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        text = (repo_root / "CHANGELOG.md").read_text()
        _edges, malformed = markdown_anchors("CHANGELOG.md", text)
        waive_mentions = [m for m in malformed if "waive" in m.reason]
        assert waive_mentions == []
