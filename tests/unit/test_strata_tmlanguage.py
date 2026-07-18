"""Drift-lock the strata TextMate grammar against strata-core/src/parse.rs.

WHY: editors/vscode-strata/syntaxes/strata.tmLanguage.json hand-spells the
strata surface keyword vocabulary for syntax highlighting (T-0139). That
vocabulary already has one authoritative home -- the lexer/parser dispatch
in strata-core/src/parse.rs -- so this test extracts both keyword sets
straight from source (regex over the Rust file, json.load over the
grammar) and asserts they agree bidirectionally. A keyword added to the
parser without a matching grammar update, or a stray keyword left in the
grammar after a parser change, fails this test instead of silently going
unhighlighted or unhonest.

frob:tests strata-core/src/parse.rs::parse_program kind="drift"
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PARSE_RS = REPO_ROOT / "strata-core" / "src" / "parse.rs"
TMLANGUAGE = (
    REPO_ROOT / "editors" / "vscode-strata" / "syntaxes" / "strata.tmLanguage.json"
)

_IDENT = r"[a-z_][a-z0-9_]*"


def _parse_rs_text() -> str:
    """Return the full source of parse.rs, failing loudly if it moved."""
    assert PARSE_RS.exists(), f"expected {PARSE_RS} to exist"
    return PARSE_RS.read_text(encoding="utf-8")


def _extract_construct_keywords(source: str) -> set[str]:
    """Extract the top-level declaration keywords from parse_program's dispatch.

    WHY: strata-core/src/parse.rs::parse_program dispatches on the first
    ident of each top-level statement via `match kw.as_str() { "module" =>
    ..., "node" | "flow" | ... => { ... } }`. This is the *only* place new
    top-level constructs are wired in, so anchoring on that function body
    and pulling every quoted ident out of it gives the authoritative
    construct-keyword set with no hand-copying. If parse_program's shape
    changes enough that this anchor no longer matches, fail loudly rather
    than silently extracting nothing.
    """
    fn_match = re.search(
        r"fn parse_program\(&mut self\) -> Result<ModuleAst, ParseError> \{(.*?)\n    \}\n\}",
        source,
        re.DOTALL,
    )
    assert fn_match is not None, (
        "anchor pattern for parse_program no longer matches parse.rs -- "
        "the dispatch table moved or was renamed; update this test's anchor"
    )
    body = fn_match.group(1)
    keywords = set(re.findall(rf'"({_IDENT})"', body))
    # `_ => unreachable!()` and `_ => return self.err(...)` are match arms,
    # not keywords; `kw` itself is never quoted so no filtering needed
    # beyond the quoted-string extraction above.
    assert keywords, (
        "expected at least one construct keyword extracted from parse_program"
    )
    return keywords


def _extract_clause_keywords(source: str) -> set[str]:
    """Extract every literal keyword parse.rs checks for via at_keyword/expect_keyword.

    WHY: these are the property/clause words legal inside a declaration
    body (attr, capacity, trust, issued_by, ...). Every call site in the
    file is a `self.at_keyword("word")` or `self.expect_keyword("word")`
    string literal, so a whole-file regex is exhaustive without needing to
    track control flow the way the construct-keyword extraction does.
    """
    keywords = set(re.findall(rf'\bat_keyword\("({_IDENT})"\)', source))
    keywords |= set(re.findall(rf'\bexpect_keyword\("({_IDENT})"\)', source))
    assert keywords, "expected at least one clause keyword extracted from parse.rs"
    return keywords


def _load_tmlanguage() -> dict:
    assert TMLANGUAGE.exists(), f"expected {TMLANGUAGE} to exist"
    with TMLANGUAGE.open(encoding="utf-8") as f:
        return json.load(f)


def _pattern_keyword_set(grammar: dict, repo_key: str) -> set[str]:
    """Pull the alternation's keyword set out of one repository rule's match regex."""
    rule = grammar["repository"][repo_key]
    match = rule["match"]
    inner = re.search(r"\((.*)\)", match)
    assert inner is not None, (
        f"expected an alternation group in {repo_key}'s match regex"
    )
    return set(inner.group(1).split("|"))


def test_tmlanguage_is_valid_json():
    """The grammar file must be parseable JSON (VSCode and JetBrains both require it)."""
    grammar = _load_tmlanguage()
    assert grammar["scopeName"] == "source.strata"


def test_construct_keywords_match_parser_bidirectionally():
    """Every parser construct keyword is in the grammar, and vice versa."""
    source = _parse_rs_text()
    parser_keywords = _extract_construct_keywords(source)
    grammar = _load_tmlanguage()
    grammar_keywords = _pattern_keyword_set(grammar, "declaration-keywords")

    missing_from_grammar = parser_keywords - grammar_keywords
    stale_in_grammar = grammar_keywords - parser_keywords
    assert not missing_from_grammar, (
        f"parser construct keywords missing from tmLanguage declaration-keywords: "
        f"{sorted(missing_from_grammar)}"
    )
    assert not stale_in_grammar, (
        f"tmLanguage declaration-keywords has keywords the parser no longer accepts: "
        f"{sorted(stale_in_grammar)}"
    )


def test_clause_keywords_covered_by_grammar():
    """Every clause keyword the parser checks for is highlighted by the grammar.

    One-directional (parser -> grammar): the clause-keyword extraction is a
    whole-file regex over at_keyword/expect_keyword call sites, which is
    exhaustive for "does the parser use this word" but the grammar is free
    to be conservative about it, so we only require the grammar not be
    missing any parser-recognized clause word, not that its set be minimal.
    """
    source = _parse_rs_text()
    parser_keywords = _extract_clause_keywords(source)
    grammar = _load_tmlanguage()
    grammar_keywords = _pattern_keyword_set(grammar, "clause-keywords")

    missing_from_grammar = parser_keywords - grammar_keywords
    assert not missing_from_grammar, (
        f"parser clause keywords missing from tmLanguage clause-keywords: "
        f"{sorted(missing_from_grammar)}"
    )


@pytest.mark.parametrize(
    ("text", "should_match"),
    [
        ("5 req/s", True),
        ("250 ms", True),
        ("4 KiB", True),
        ("15 %/month", True),
        ("80 %", True),
        ("api", False),
        ("node", False),
        ("42", False),
    ],
)
def test_quantity_pattern_spot_check(text: str, should_match: bool):
    """Sanity-render the quantities regex against real and non-quantity tokens."""
    grammar = _load_tmlanguage()
    pattern = grammar["repository"]["quantities"]["match"]
    matched = re.search(pattern, text) is not None
    assert matched == should_match, (
        f"quantities pattern {'failed to match' if should_match else 'incorrectly matched'} "
        f"{text!r}"
    )


# frob:waive PERF003 reason="two sibling next()-generator lookups over a small fixed grammar pattern list, each by distinct name; not a nested join"
def test_string_pattern_terminates_at_end_of_line():
    """The string pattern must match a quoted literal on one line and must not
    span a newline, matching strata-core/src/parse.rs::lex (lines 131-151),
    which forbids newlines inside string literals. A begin/end pair without a
    line restriction would let an unterminated quote highlight the rest of
    the file as string content; this locks the grammar to single-line
    matching instead.
    """
    grammar = _load_tmlanguage()
    patterns = grammar["repository"]["strings"]["patterns"]
    string_pattern = next(
        p["match"] for p in patterns if p["name"] == "string.quoted.double.strata"
    )
    illegal_pattern = next(
        p["match"]
        for p in patterns
        if p["name"] == "invalid.illegal.unterminated-string.strata"
    )

    one_line = 'store "cache/*.blob" { }'
    assert re.search(string_pattern, one_line) is not None, (
        "string pattern failed to match a quoted glob on one line"
    )

    across_newline = '"unterminated\nnext line'
    assert re.search(string_pattern, across_newline) is None, (
        "string pattern incorrectly matched across a newline"
    )
    assert re.match(illegal_pattern, across_newline.splitlines()[0]) is not None, (
        "invalid.illegal pattern failed to flag an unterminated string on its own line"
    )
