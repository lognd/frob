//! Parser tests: spec fixtures, structure, spans, malformed inputs and no-panic properties.

mod malformed;
mod props;

use std::fmt::Write as _;

use gob_text::{FileId, FileInterner};

use crate::grl::ast::{
    ClauseKind, CondKind, ExampleBody, ExpectKind, File, HeaderKind, LangSet, RelKind, Rule,
    ShapeKind, Source, TermKind,
};
use crate::grl::{ParseWarningKind, Parsed, parse};

pub(super) fn file() -> FileId {
    FileInterner::new().intern("rules/T.grl")
}

pub(super) fn parsed(src: &str) -> Parsed {
    parse(file(), src)
}

/// Parse and require no errors.
fn clean(src: &str) -> Parsed {
    let p = parsed(src);
    assert!(p.is_ok(), "unexpected errors: {:#?}", p.errors);
    p
}

fn fixture(name: &str) -> String {
    let path = format!(
        "{}/src/grl/parse/tests/fixtures/{name}.grl",
        env!("CARGO_MANIFEST_DIR")
    );
    std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("{path}: {e}"))
}

/// The fixture rules: section 2 plus the ten rules of section 12 (CI002 with escaped glob braces).
const FIXTURES: &[&str] = &[
    "NOPE001",
    "TODO001",
    "DOC002",
    "COV001",
    "INV002",
    "SCOPE001",
    "SYS001",
    "CAP001",
    "NEAT013",
    "NEAT031",
    "CI002_escaped",
];

fn slice(src: &str, span: gob_text::Span) -> &str {
    &src[span.range.to_usize_range()]
}

/// A compact dump of the tree: spans as `@start..end`, one node per line, indented.
fn dump(file: &File) -> String {
    let raw = format!("{file:?}");
    let raw = fold_spans(&raw);
    indent(&raw)
}

/// Replace every `Span { file: FileId(N), range: TextRange { start: TextSize(A), end: TextSize(B) } }` by `@A..B`.
fn fold_spans(raw: &str) -> String {
    const HEAD: &str = "Span { file: FileId(";
    let mut out = String::new();
    let mut rest = raw;
    while let Some(at) = rest.find(HEAD) {
        out.push_str(&rest[..at]);
        let tail = &rest[at..];
        let start = tail.find("start: TextSize(").expect("span start") + "start: TextSize(".len();
        let end = tail.find("end: TextSize(").expect("span end") + "end: TextSize(".len();
        let num = |from: usize| -> &str {
            let t = &tail[from..];
            &t[..t.find(')').expect("number")]
        };
        let _ = write!(out, "@{}..{}", num(start), num(end));
        let close = tail.find("} }").expect("span close") + 3;
        // `TextRange { .. } }` closes with "} }" after the end number.
        rest = &tail[close..];
    }
    out.push_str(rest);
    out
}

/// Break a one-line Debug string into indented lines, respecting string literals.
fn indent(raw: &str) -> String {
    let mut out = String::new();
    let mut depth = 0usize;
    let mut in_str = false;
    let mut escaped = false;
    let mut chars = raw.chars().peekable();
    let newline = |out: &mut String, depth: usize| {
        out.push('\n');
        out.push_str(&"  ".repeat(depth));
    };
    while let Some(c) = chars.next() {
        if in_str {
            out.push(c);
            if escaped {
                escaped = false;
            } else if c == '\\' {
                escaped = true;
            } else if c == '"' {
                in_str = false;
            }
            continue;
        }
        match c {
            '"' => {
                in_str = true;
                out.push(c);
            }
            '{' | '[' | '(' => {
                out.push(c);
                if matches!(chars.peek(), Some('}' | ']' | ')')) {
                    continue;
                }
                depth += 1;
                newline(&mut out, depth);
            }
            '}' | ']' | ')' => {
                depth = depth.saturating_sub(1);
                if !matches!(out.chars().last(), Some('{' | '[' | '(')) {
                    newline(&mut out, depth);
                }
                out.push(c);
            }
            ',' => {
                out.push(c);
                if chars.peek() == Some(&' ') {
                    chars.next();
                }
                newline(&mut out, depth);
            }
            _ => out.push(c),
        }
    }
    out.push('\n');
    out
}

// frob:tests crates/gob-plan/src/grl/parse/mod.rs::parse
#[test]
fn spec_rules_parse_without_error_and_match_snapshots() {
    for name in FIXTURES {
        let src = fixture(name);
        let p = clean(&src);
        assert_eq!(p.file.rules.len(), 1, "{name}");
        insta::assert_snapshot!(*name, dump(&p.file));
    }
}

#[test]
fn ci002_verbatim_spec_text_is_one_interpolation_error() {
    let src = fixture("CI002");
    let p = parsed(&src);
    assert_eq!(p.errors.len(), 1, "{:#?}", p.errors);
    let e = &p.errors[0];
    assert_eq!(
        e.to_string(),
        "`{...}` is not allowed in a comparison, glob or path"
    );
    assert_eq!(slice(&src, e.span), "{yml,yaml}");
    // Everything else about the rule still parsed.
    assert_eq!(p.file.rules.len(), 1);
    assert_eq!(p.file.rules[0].examples.len(), 2);
}

/// Every header, clause, example and explain has a non-empty span inside its rule that starts at its keyword.
#[test]
fn spans_cover_every_clause_header_example_and_explain() {
    for name in FIXTURES {
        let src = fixture(name);
        let p = clean(&src);
        let rule = &p.file.rules[0];
        let rule_text = slice(&src, rule.span);
        assert!(rule_text.starts_with("rule "), "{name}");
        assert!(rule_text.ends_with('}'), "{name}");
        let inside = |span: gob_text::Span| rule.span.range.contains_range(span.range);
        let mut last_end = 0u32;
        let mut check = |what: &str, span: gob_text::Span, keywords: &[&str]| {
            assert!(inside(span) && !span.range.is_empty(), "{name}: {what}");
            let text = slice(&src, span);
            assert!(
                keywords.iter().any(|k| text.starts_with(k)),
                "{name}: {what} span text {text:?}"
            );
            let start = u32::from(span.range.start());
            assert!(
                start >= last_end,
                "{name}: {what} overlaps the previous item"
            );
            last_end = u32::from(span.range.end());
        };
        for h in &rule.headers {
            check(
                "header",
                h.span,
                &[
                    "lang",
                    "polarity",
                    "severity",
                    "scope",
                    "must_measure",
                    "needs",
                    "rollup",
                    "knob",
                ],
            );
        }
        for c in &rule.clauses {
            check(
                "clause",
                c.span,
                &[
                    "find",
                    "where",
                    "some",
                    "no",
                    "def",
                    "report",
                    "note",
                    "fix",
                    "unresolved",
                ],
            );
        }
        for e in &rule.examples {
            check("example", e.span, &["example"]);
        }
        let explain = rule.explain.as_ref().expect("explain");
        check("explain", explain.span, &["explain"]);
        assert!(explain.text.value.contains("## Remedy"), "{name}");
    }
}

fn rule_of(src: &str) -> Rule {
    clean(src).file.rules.into_iter().next().expect("one rule")
}

const SKELETON_END: &str = "\n  explain \"\"\"\n    ## Remedy\n  \"\"\"\n}\n";

fn wrap(body: &str) -> String {
    format!("rule ABC001 \"a-b\" {{\n  lang rust\n  {body}{SKELETON_END}")
}

// frob:tests crates/gob-plan/src/grl/parse/mod.rs::parse
#[test]
fn lang_star_quoted_is_accepted_with_a_warning_to_drop_the_quotes() {
    let src = "rule ABC001 \"a-b\" {\n  lang \"*\"\n  explain \"\"\"\n    ## Remedy\n  \"\"\"\n}\n";
    let p = clean(src);
    assert_eq!(p.warnings.len(), 1);
    assert_eq!(p.warnings[0].kind, ParseWarningKind::QuotedLangStar);
    assert_eq!(slice(src, p.warnings[0].span), "\"*\"");
    assert_eq!(
        p.warnings[0].help().as_deref(),
        Some("drop the quotes: `lang *`")
    );
    let HeaderKind::Lang(LangSet::Any { quoted }) = &p.file.rules[0].headers[0].node else {
        panic!("expected lang *");
    };
    assert!(quoted);
    let unquoted = clean(&src.replace("\"*\"", "*"));
    assert!(unquoted.warnings.is_empty());
}

// frob:tests crates/gob-plan/src/grl/parse/mod.rs::parse
#[test]
fn unknown_words_in_kind_verb_and_field_positions_parse_and_stay_words() {
    let rule = rule_of(&wrap(
        "find t: tset where t.nme == \"x\" and t frobnicates t and t inside tset",
    ));
    let ClauseKind::Find(b) = &rule.clauses[0].node else {
        panic!("find");
    };
    let Source::Shape(shape) = &b.source else {
        panic!("shape");
    };
    let ShapeKind::Kind { kind, .. } = &shape.node else {
        panic!("kind");
    };
    assert_eq!(kind.text, "tset");
    let CondKind::And(parts) = &b.filter.as_ref().expect("filter").node else {
        panic!("and");
    };
    assert_eq!(parts.len(), 3);
    let CondKind::Rel { rel, .. } = &parts[1].node else {
        panic!("rel");
    };
    let RelKind::Verb { verb, .. } = &rel.node else {
        panic!("verb");
    };
    assert_eq!(verb.text, "frobnicates");
}

// frob:tests crates/gob-plan/src/grl/parse/mod.rs::parse
#[test]
fn hyphenated_words_are_joined() {
    let src = "rule ABC001 \"a-b\" {\n  lang rust\n  find d: function\n  fix d -> `x` [has-placeholders]\n  fix d -> `y` [maybe-incorrect]\n  example known-gap rust \"\"\"\n    x\n  \"\"\"\n  explain \"\"\"\n    ## Remedy\n  \"\"\"\n}\n";
    let rule = rule_of(src);
    assert_eq!(rule.examples[0].expect.kind, ExpectKind::KnownGap);
    assert_eq!(slice(src, rule.examples[0].expect.span), "known-gap");
    let apps: Vec<_> = rule
        .clauses
        .iter()
        .filter_map(|c| match &c.node {
            ClauseKind::Fix(f) => f.applicability,
            _ => None,
        })
        .collect();
    assert_eq!(apps.len(), 2);
    assert_eq!(slice(src, apps[0].span), "has-placeholders");
    assert_eq!(slice(src, apps[1].span), "maybe-incorrect");
}

#[test]
fn multi_word_relations_are_single_nodes() {
    let src = wrap(
        "find c: call where c resolves to f and u owned by n and p peer of q and c in unit u and c directly inside d",
    );
    let rule = rule_of(&src);
    let ClauseKind::Find(b) = &rule.clauses[0].node else {
        panic!("find");
    };
    let CondKind::And(parts) = &b.filter.as_ref().expect("filter").node else {
        panic!("and");
    };
    let words: Vec<String> = parts
        .iter()
        .map(|p| match &p.node {
            CondKind::Rel { rel, .. } => match &rel.node {
                RelKind::Verb { verb, .. } => format!("verb:{}", verb.text),
                RelKind::InUnit { .. } => "in unit".into(),
                RelKind::Containment { directly, .. } => format!("inside directly={directly}"),
                other => panic!("{other:?}"),
            },
            other => panic!("{other:?}"),
        })
        .collect();
    assert_eq!(
        words,
        [
            "verb:resolves to",
            "verb:owned by",
            "verb:peer of",
            "in unit",
            "inside directly=true"
        ]
    );
    // The verb node spans both words.
    let CondKind::Rel { rel, .. } = &parts[0].node else {
        panic!()
    };
    let RelKind::Verb { verb, .. } = &rel.node else {
        panic!()
    };
    assert_eq!(slice(&src, verb.span), "resolves to");
}

#[test]
fn precedence_and_connectives_group_as_the_grammar_says() {
    let rule = rule_of(&wrap(
        "where a == 1 or b == 2 and not c == 3\n  where x.n >= knob.k * 2 + 1",
    ));
    let ClauseKind::Where(c) = &rule.clauses[0].node else {
        panic!()
    };
    let CondKind::Or(parts) = &c.node else {
        panic!("or at the top: {c:?}")
    };
    assert!(matches!(parts[1].node, CondKind::And(_)));
    let ClauseKind::Where(c) = &rule.clauses[1].node else {
        panic!()
    };
    let CondKind::Cmp { rhs, .. } = &c.node else {
        panic!()
    };
    // `knob.k * 2 + 1` is `(knob.k * 2) + 1`.
    let TermKind::Binary { lhs, .. } = &rhs.node else {
        panic!()
    };
    assert!(matches!(lhs.node, TermKind::Binary { .. }));
}

#[test]
fn quantifier_clause_and_any_and_ranges_parse() {
    let rule = rule_of(&wrap(
        "find f: function\n  no t: test where t reaches f via calls, imports within 12\n  where any { f.line in 1..5, p in diff.changed } and exists f.name",
    ));
    assert!(matches!(rule.clauses[1].node, ClauseKind::Quant { .. }));
    let ClauseKind::Where(c) = &rule.clauses[2].node else {
        panic!()
    };
    let CondKind::And(parts) = &c.node else {
        panic!()
    };
    let CondKind::Any(inner) = &parts[0].node else {
        panic!()
    };
    assert_eq!(inner.len(), 2);
}

#[test]
fn example_forms_parse() {
    let rule = rule_of(&wrap(
        "example fire rust \"named\" {\n    file \"a.rs\" \"\"\"\n      x\n    \"\"\"\n    config \"\"\"\n      a = 1\n    \"\"\"\n    diff [\"a\", \"b\"]\n    lease [\"c/**\"]\n    expect \"line 3: warn\"\n    fixed \"\"\"\n      y\n    \"\"\"\n  }\n  example clean {}\n  example unresolved \"\"\"\n    z\n  \"\"\"",
    ));
    assert_eq!(rule.examples.len(), 3);
    let ExampleBody::Inputs(inputs) = &rule.examples[0].body else {
        panic!()
    };
    assert_eq!(inputs.len(), 6);
    assert_eq!(
        rule.examples[0].lang.as_ref().map(|w| w.text.as_str()),
        Some("rust")
    );
    assert_eq!(
        rule.examples[0].name.as_ref().map(|s| s.value.as_str()),
        Some("named")
    );
}

// frob:tests crates/gob-plan/src/grl/ast.rs::Source.span
// frob:tests crates/gob-plan/src/grl/ast.rs::Object.span
#[test]
fn source_and_object_spans_cover_their_text() {
    let src = wrap("find d: diff.changed\n  find t: tset where t inside tset");
    let rule = rule_of(&src);
    let ClauseKind::Find(side) = &rule.clauses[0].node else {
        panic!("find");
    };
    assert_eq!(slice(&src, side.source.span()), "diff.changed");
    let ClauseKind::Find(shape) = &rule.clauses[1].node else {
        panic!("find");
    };
    assert_eq!(slice(&src, shape.source.span()), "tset");
    let CondKind::Rel { rel, .. } = &shape.filter.as_ref().expect("filter").node else {
        panic!("rel");
    };
    let RelKind::Containment { object, .. } = &rel.node else {
        panic!("contain");
    };
    assert_eq!(slice(&src, object.span()), "tset");
}
