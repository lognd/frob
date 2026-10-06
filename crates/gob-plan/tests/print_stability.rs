//! GRL printer stability harness (build-test-ci.md section 6, D98), modelled on
//! `crates/grimble-model/tests/stability.rs`: the printer must be a fixed point
//! (`print(print(x)) = print(x)`), must round-trip (`parse(print(t)) = t` up to source
//! ranges) over every fixture and a generated family of trees, and a deliberately broken printer
//! must fail with a shrunk example.

// frob:ticket 01M47YJF46HM8MA5PVWNH92W1H

use std::fmt::Write as _;

use gob_plan::grl::ast::{
    Applicability, ApplicabilityKind, ArithOp, Binding, BlockLit, Call, Cast, CastKind, Certainty,
    Clause, ClauseKind, CmpOp, Cond, CondKind, Containment, Def, Example, ExampleBody, Expect,
    ExpectKind, Explain, FieldEq, File, Fix, FixKind, Header, HeaderKind, Input, InputKind, Knob,
    LangSet, Literal, LiteralKind, Message, MessagePart, Note, Object, Path, Placement, Polarity,
    Position, Quant, Rel, RelKind, Report, Rollup, Rule, Scope, Severity, Shape, ShapeKind, Source,
    Spanned, StrLit, Term, TermKind, TypeKind, TypeRef, Unresolved, Word,
};
use gob_plan::grl::{Regex, Snippet, TokenKind, lex, parse, print};
use gob_text::{FileId, FileInterner, Span, TextRange, TextSize};
use proptest::prelude::*;
use proptest::sample::select;
use proptest::test_runner::{Config, RngAlgorithm, TestError, TestRng, TestRunner};

// ---- the harness proper ----

fn file_id() -> FileId {
    FileInterner::new().intern("rules/T.grl")
}

/// The `Debug` text of a tree with every `Span { .. }` removed: trees compare up to source ranges.
fn strip(tree: &impl std::fmt::Debug) -> String {
    let raw = format!("{tree:?}");
    let mut out = String::with_capacity(raw.len());
    let mut rest = raw.as_str();
    while let Some(at) = rest.find("Span {") {
        out.push_str(&rest[..at]);
        out.push_str("Span");
        let tail = &rest[at + "Span ".len()..];
        let mut depth = 0usize;
        let mut end = tail.len();
        for (i, c) in tail.char_indices() {
            match c {
                '{' => depth += 1,
                '}' => {
                    depth -= 1;
                    if depth == 0 {
                        end = i + 1;
                        break;
                    }
                }
                _ => {}
            }
        }
        rest = &tail[end..];
    }
    out.push_str(rest);
    out
}

/// Parse `src`, requiring a clean parse.
fn parse_clean(src: &str) -> File {
    let parsed = parse(file_id(), src);
    assert!(
        parsed.is_ok(),
        "does not parse:\n{src}\n{:#?}",
        parsed.errors
    );
    parsed.file
}

/// The real printer as text to text: parse, then print.
fn real(src: &str) -> String {
    print(&parse_clean(src))
}

/// Why a text printer is unstable on `src`, or `None` when it is a fixed point preserving the tree.
fn instability(print_text: &dyn Fn(&str) -> String, src: &str) -> Option<String> {
    let once = print_text(src);
    let twice = print_text(&once);
    if once != twice {
        return Some(format!("print(print(x)) != print(x) for {src:?}"));
    }
    let before = strip(&parse(file_id(), src).file);
    let reparsed = parse(file_id(), &once);
    if !reparsed.is_ok() {
        return Some(format!("print(x) does not parse for {src:?}: {once}"));
    }
    (before != strip(&reparsed.file)).then(|| format!("parse(print(t)) != t for {src:?}"))
}

/// The text around the first byte where two stripped trees differ, from each side.
fn first_difference(want: &str, got: &str) -> String {
    let at = want
        .bytes()
        .zip(got.bytes())
        .position(|(a, b)| a != b)
        .unwrap_or(want.len().min(got.len()));
    let from = at.saturating_sub(120);
    let show = |s: &str| {
        s.get(from..(at + 200).min(s.len()))
            .unwrap_or_default()
            .to_owned()
    };
    format!("tree:    {}\nreparse: {}", show(want), show(got))
}

/// Why `printer` is unstable on a tree built without a parse, or `None`.
fn tree_instability(printer: &dyn Fn(&File) -> String, tree: &File) -> Option<String> {
    let once = printer(tree);
    let reparsed = parse(file_id(), &once);
    if !reparsed.is_ok() {
        return Some(format!(
            "printed tree does not parse:\n{once}\n{:?}",
            reparsed.errors
        ));
    }
    let (want, got) = (strip(tree), strip(&reparsed.file));
    if want != got {
        return Some(format!(
            "parse(print(t)) != t for:\n{once}\nfirst difference:\n{}",
            first_difference(&want, &got)
        ));
    }
    let twice = printer(&reparsed.file);
    (once != twice).then(|| format!("print(print(t)) != print(t) for:\n{once}\n--\n{twice}"))
}

// ---- fixtures ----

fn fixtures() -> Vec<(String, String)> {
    let dir = format!(
        "{}/src/grl/parse/tests/fixtures",
        env!("CARGO_MANIFEST_DIR")
    );
    let mut out: Vec<(String, String)> = std::fs::read_dir(&dir)
        .unwrap_or_else(|e| panic!("{dir}: {e}"))
        .filter_map(Result::ok)
        .filter(|e| e.path().extension().is_some_and(|x| x == "grl"))
        .map(|e| {
            let text = std::fs::read_to_string(e.path()).expect("fixture reads");
            (e.file_name().to_string_lossy().into_owned(), text)
        })
        .collect();
    out.sort();
    out
}

/// The whole-rule `grl` blocks of grl-spec.md (excerpts with a bare `...` line are skipped).
fn spec_rules() -> Vec<String> {
    let path = format!(
        "{}/../../docs/design/grl-spec.md",
        env!("CARGO_MANIFEST_DIR")
    );
    let text = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("{path}: {e}"));
    let mut blocks = Vec::new();
    let mut cur: Option<String> = None;
    for line in text.lines() {
        match (&mut cur, line.trim_end()) {
            (None, "```grl") => cur = Some(String::new()),
            (Some(b), "```") => {
                blocks.push(std::mem::take(b));
                cur = None;
            }
            (Some(b), l) => {
                b.push_str(l);
                b.push('\n');
            }
            (None, _) => {}
        }
    }
    blocks
        .into_iter()
        .filter(|b| b.trim_start().starts_with("rule ") && !b.lines().any(|l| l.trim() == "..."))
        .collect()
}

/// Every construct the fixtures leave out: all header and knob types, dotted fields, `count`,
/// ranges, `any`, `reaches`, every fix form, every example input and awkward escapes.
const KITCHEN_SINK: &str = r#"
rule KIT001 "kitchen-sink" {
  lang [rust, python]
  polarity Pn
  severity advisory
  scope repo
  must_measure
  needs diff, lease
  rollup directory
  knob depth: int = 12 "max depth"
  knob names: list<list<string>> = [["a"], ["b", "c"]] "names"
  knob pat: regex = /todo/i "pattern"
  knob ratio: float = -0.75 "ratio"
  knob caps: vocab = vocab("clock", "rng") "capabilities"
  knob flag: bool = true "a { brace } and \{ escaped \} text"

  find e: element(.tag = "img", kind = "x") inside (function | method) where e.line > 3 + 2 * 4 - 1
  find d: directive "todo" under "src/" calls g
  find s: `$X.unwrap()` as roles
  find t: rust`if $C { $F($$$A) }` as call certainly calls (call | function)
  find u: diff.changed
  where not (a or b) and any { x is public, exists y.z }
  where some k: key(path = "/jobs/*") directly inside e where k.value ~ /a\/b/im
  where n in 1..9 and count(c: call inside f where c.line > 1) >= 2
  where f reaches g via calls, imports within knob.depth
  where f has attr "role" or q matches ["*.rs", "*.{yml,yaml}"]
  where resolve(f, 1)
  where x is `$A + $B` as roles and y has attr "k"
  def has_alt(l) = no x: attribute(name = "alt") inside l
  some x: call before y adjoins z
  no w: file in unit f possibly resolves to g
  report e "missing {e.name} \{literal\} \"q\" \\ done"
  report d "x" when d.line == 1
  note d "see {d.file.path}\nsecond line"
  fix before e -> `<img alt="">` [maybe-incorrect]
  fix s -> ``a `b` c`` [machine]
  fix delete s [has-placeholders]
  fix host rename(e, "a") [machine]
  fix manual "do it by hand {d.name}"
  unresolved when e.observed because "might be {e.tag}"

  example fire rust "named" """
    fn f() { x.unwrap() }   //~ warn
        indented more

    after a blank line
  """
  example clean """
    a
  """
  example known-gap python {
    file "src/a.py" """
      x = 1
    """
    config """
      [a]
      b = 1
    """
    model """
      grimble = "2";
    """
    diff ["a.rs", "b.rs"]
    lease ["src/**"]
    expect "line 3: warn"
    fixed """
      y
    """
  }
  example unresolved { }
  example notapplicable markdown """
  """

  explain """
    Text.

    ## Remedy
      indented
  """
}

rule KIT002 "second" {
  lang -
  find x: file
  report x "r"
  example fire """
    a
  """
  explain """
    x
    ## Remedy
    y
  """
}
"#;

// ---- the real printer ----

// frob:tests crates/gob-plan/src/grl/print.rs::print
#[test]
fn every_fixture_is_a_fixed_point_and_round_trips() {
    let all = fixtures();
    assert!(all.len() >= 11, "found only {} fixtures", all.len());
    for (name, src) in &all {
        assert_eq!(instability(&real, src), None, "{name}");
    }
}

// frob:tests crates/gob-plan/src/grl/print.rs::print
#[test]
fn every_whole_rule_in_the_spec_is_a_fixed_point_and_round_trips() {
    let rules = spec_rules();
    assert!(rules.len() >= 10, "found only {} spec rules", rules.len());
    for src in &rules {
        assert_eq!(instability(&real, src), None, "{src}");
    }
}

// frob:tests crates/gob-plan/src/grl/print.rs::print
#[test]
fn the_kitchen_sink_is_a_fixed_point_and_round_trips() {
    assert_eq!(instability(&real, KITCHEN_SINK), None);
}

// frob:tests crates/gob-plan/src/grl/print.rs::print
#[test]
fn dotted_fields_print_bare_and_quoted_star_prints_bare() {
    let src = "rule T001 \"t\" {\n lang \"*\"\n find e: element(.tag = \"img\", .kind = \"x\")\n report e \"m\"\n example fire \"\"\"\n a\n \"\"\"\n explain \"\"\"\n x\n ## Remedy\n y\n \"\"\"\n}\n";
    let text = real(src);
    assert!(
        text.contains("find e: element(tag = \"img\", kind = \"x\")"),
        "{text}"
    );
    assert!(text.contains("  lang *\n"), "{text}");
    assert!(!text.contains(".tag"), "{text}");
}

// frob:tests crates/gob-plan/src/grl/print.rs::print
#[test]
fn the_layout_is_the_documented_canonical_one() {
    let text = real(KITCHEN_SINK);
    assert!(text.starts_with("rule KIT001 \"kitchen-sink\" {\n  lang [rust, python]\n"));
    assert!(text.contains("\n\n  find e: "), "headers, blank, clauses");
    assert!(text.contains("\n\n  example fire rust \"named\" \"\"\"\n    fn f()"));
    assert!(
        text.contains("\n  }\n"),
        "input braces close at example indent"
    );
    assert!(text.ends_with("}\n"));
    assert!(!text.contains("  \n"), "no trailing whitespace");
}

// frob:tests crates/gob-plan/src/grl/print.rs::print_rule
#[test]
fn print_rule_is_the_text_print_writes_for_that_rule() {
    let file = parse_clean(KITCHEN_SINK);
    let by_rule: Vec<String> = file.rules.iter().map(gob_plan::grl::print_rule).collect();
    assert_eq!(by_rule.join("\n"), print(&file));
}

// ---- generators ----

fn sp() -> Span {
    Span::new(file_id(), TextRange::empty(TextSize::new(0)))
}

fn sn<T>(node: T) -> Spanned<T> {
    Spanned { node, span: sp() }
}

fn word(s: &str) -> Word {
    Word {
        text: s.to_owned(),
        span: sp(),
    }
}

fn strlit(s: String) -> StrLit {
    StrLit {
        value: s,
        span: sp(),
    }
}

const VARS: &[&str] = &["x", "y", "f", "d", "m", "c"];
const KINDS: &[&str] = &["function", "call", "file", "element", "heading", "import"];
const VERBS: &[&str] = &[
    "calls",
    "imports",
    "reads",
    "resolves to",
    "owned by",
    "peer of",
];
const FIELDS: &[&str] = &["name", "text", "path", "tag", "line", "file"];
const LANGS: &[&str] = &["rust", "python", "typescript", "markdown"];

fn pick(list: &'static [&'static str]) -> impl Strategy<Value = Word> {
    select(list).prop_map(word)
}

/// Pieces of plain string values: escapes, braces and the guarded brace `\{` (the parser's forms).
fn plain_value() -> impl Strategy<Value = String> {
    let piece = select(vec![
        "a", "b", " ", "*", "/", ".", "\"", "\\", "\n", "{x,y}", "\\{", "-",
    ]);
    proptest::collection::vec(piece, 0..6).prop_map(|v| v.concat())
}

/// Pieces of message text: any of `"` `\` newline and braces (the printer escapes them all).
fn text_value() -> impl Strategy<Value = String> {
    let piece = select(vec!["a", "b", " ", "{", "}", "\"", "\\", "\n", "x"]);
    proptest::collection::vec(piece, 1..5).prop_map(|v| v.concat())
}

fn lexed_snippet(src: &str) -> Snippet {
    let lexed = lex(file_id(), src).expect("snippet lexes");
    match lexed.tokens.into_iter().next().map(|t| t.kind) {
        Some(TokenKind::Snippet(s)) => s,
        other => panic!("not a snippet: {other:?}"),
    }
}

fn snippet() -> impl Strategy<Value = Snippet> {
    select(vec![
        "`dbg!($$$ARGS)`",
        "rust`$X.unwrap()`",
        "``a `b` c``",
        "`$_ + $A`",
        "`$$ cost`",
        "python`print($X)`",
    ])
    .prop_map(lexed_snippet)
}

fn regex() -> impl Strategy<Value = Regex> {
    select(vec![
        ("todo", false, false),
        ("a\\/b", true, false),
        ("^x[/]y$", false, true),
        ("\\bfix(me)?\\b", true, true),
    ])
    .prop_map(|(p, i, m)| Regex {
        pattern: p.to_owned(),
        ignore_case: i,
        multi_line: m,
    })
}

fn leaf_literal() -> impl Strategy<Value = LiteralKind> {
    prop_oneof![
        (0i128..1000).prop_map(LiteralKind::Int),
        (-50i128..0).prop_map(LiteralKind::Int),
        select(vec!["0.75", "-1.5", "2.0"]).prop_map(|d| LiteralKind::Decimal(d.to_owned())),
        plain_value().prop_map(LiteralKind::Str),
        regex().prop_map(LiteralKind::Regex),
        any::<bool>().prop_map(LiteralKind::Bool),
    ]
}

/// Any literal, including constructor calls (knob defaults and field values).
fn literal() -> BoxedStrategy<Literal> {
    leaf_literal()
        .prop_map(sn)
        .prop_recursive(2, 8, 3, |inner| {
            prop_oneof![
                proptest::collection::vec(inner.clone(), 0..3)
                    .prop_map(|v| sn(LiteralKind::List(v))),
                (
                    select(vec!["vocab", "set"]),
                    proptest::collection::vec(inner, 0..3)
                )
                    .prop_map(|(n, args)| sn(LiteralKind::Call {
                        name: word(n),
                        args
                    })),
            ]
        })
        .boxed()
}

/// A literal that may stand alone as a term: a top-level call would read back as a term call.
fn term_literal() -> BoxedStrategy<Literal> {
    prop_oneof![
        3 => leaf_literal().prop_map(sn),
        1 => proptest::collection::vec(literal(), 0..3).prop_map(|v| sn(LiteralKind::List(v))),
    ]
    .boxed()
}

fn path_of(first: &'static [&'static str]) -> impl Strategy<Value = Path> {
    (
        select(first),
        proptest::collection::vec(select(FIELDS), 0..3),
    )
        .prop_map(|(head, rest)| {
            let mut segments = vec![word(head)];
            segments.extend(rest.into_iter().map(word));
            Path {
                segments,
                span: sp(),
            }
        })
}

fn path_term() -> impl Strategy<Value = Term> {
    path_of(VARS).prop_map(|p| sn(TermKind::Path(p)))
}

/// Paths, literals: terms that need no care in any position.
fn simple_term() -> BoxedStrategy<Term> {
    prop_oneof![
        3 => path_term(),
        1 => term_literal().prop_map(|l| sn(TermKind::Literal(l))),
    ]
    .boxed()
}

fn call() -> impl Strategy<Value = Call> {
    (
        select(vec!["resolve", "slug", "has_alt"]),
        proptest::collection::vec(simple_term(), 0..3),
    )
        .prop_map(|(n, args)| Call {
            name: word(n),
            args,
            span: sp(),
        })
}

fn primary_term() -> BoxedStrategy<Term> {
    prop_oneof![
        4 => simple_term(),
        1 => pick(FIELDS).prop_map(|w| sn(TermKind::Knob(w))),
        1 => call().prop_map(|c| sn(TermKind::Call(c))),
    ]
    .boxed()
}

/// A term with the only grouping the parser can make: `*` chains under left-leaning `+`/`-`.
fn term() -> BoxedStrategy<Term> {
    let mul_chain = proptest::collection::vec(primary_term(), 1..3).prop_map(|v| {
        let mut it = v.into_iter();
        let first = it.next().expect("one");
        it.fold(first, |lhs, rhs| {
            sn(TermKind::Binary {
                op: ArithOp::Mul,
                lhs: Box::new(lhs),
                rhs: Box::new(rhs),
            })
        })
    });
    (
        mul_chain.clone(),
        proptest::collection::vec((select(vec![ArithOp::Add, ArithOp::Sub]), mul_chain), 0..3),
    )
        .prop_map(|(first, rest)| {
            rest.into_iter().fold(first, |lhs, (op, rhs)| {
                sn(TermKind::Binary {
                    op,
                    lhs: Box::new(lhs),
                    rhs: Box::new(rhs),
                })
            })
        })
        .boxed()
}

fn field_eq() -> impl Strategy<Value = FieldEq> {
    (pick(FIELDS), literal()).prop_map(|(name, value)| FieldEq {
        name,
        value,
        span: sp(),
    })
}

fn cast() -> impl Strategy<Value = Option<Cast>> {
    prop_oneof![
        2 => Just(None),
        1 => Just(Some(sn(CastKind::Roles))),
        1 => pick(KINDS).prop_map(|w| Some(sn(CastKind::Kind(w)))),
    ]
}

/// A shape; `bare` allows the plain `KIND` form that only a source may take.
fn shape(bare: bool) -> BoxedStrategy<Shape> {
    let kind_fields =
        (pick(KINDS), proptest::collection::vec(field_eq(), 1..3)).prop_map(|(kind, fields)| {
            sn(ShapeKind::Kind {
                kind,
                fields,
                arg: None,
            })
        });
    let kind_arg = plain_value().prop_map(|v| {
        sn(ShapeKind::Kind {
            kind: word("directive"),
            fields: Vec::new(),
            arg: Some(strlit(v)),
        })
    });
    let snip =
        (snippet(), cast()).prop_map(|(snippet, cast)| sn(ShapeKind::Snippet { snippet, cast }));
    let plain_kind = pick(KINDS)
        .prop_map(|kind| {
            sn(ShapeKind::Kind {
                kind,
                fields: Vec::new(),
                arg: None,
            })
        })
        .boxed();
    let leaf = prop_oneof![kind_fields, kind_arg, snip].boxed();
    let alt_leaf = prop_oneof![leaf.clone(), plain_kind.clone()];
    let alt = proptest::collection::vec(alt_leaf, 1..3).prop_map(|v| sn(ShapeKind::Alt(v)));
    if bare {
        prop_oneof![3 => leaf, 2 => plain_kind, 1 => alt].boxed()
    } else {
        prop_oneof![3 => leaf, 1 => alt].boxed()
    }
}

fn object() -> BoxedStrategy<Object> {
    prop_oneof![
        3 => simple_term().prop_map(Object::Term),
        1 => shape(false).prop_map(Object::Shape),
    ]
    .boxed()
}

fn rel() -> BoxedStrategy<Rel> {
    prop_oneof![
        (any::<bool>(), any::<bool>(), object()).prop_map(|(directly, inside, object)| sn(
            RelKind::Containment {
                directly,
                dir: if inside {
                    Containment::Inside
                } else {
                    Containment::Has
                },
                object,
            }
        )),
        object().prop_map(|object| sn(RelKind::InUnit { object })),
        simple_term().prop_map(|term| sn(RelKind::Under { term })),
        (
            select(vec![Position::Before, Position::After, Position::Adjoins]),
            object()
        )
            .prop_map(|(position, object)| sn(RelKind::Position { position, object })),
        (
            select(vec![
                None,
                Some(Certainty::Certainly),
                Some(Certainty::Possibly)
            ]),
            pick(VERBS),
            object()
        )
            .prop_map(|(certainty, verb, object)| sn(RelKind::Verb {
                certainty,
                verb,
                object
            })),
        (
            object(),
            proptest::collection::vec(pick(VERBS), 1..3),
            proptest::option::of(simple_term())
        )
            .prop_map(|(target, via, within)| sn(RelKind::Reaches {
                target,
                via,
                within
            })),
    ]
    .boxed()
}

fn source() -> BoxedStrategy<Source> {
    prop_oneof![
        4 => shape(true).prop_map(Source::Shape),
        1 => path_of(&["config", "diff", "lease", "model"])
            .prop_map(|mut p| {
                if p.segments.len() < 2 {
                    p.segments.push(word("changed"));
                }
                Source::Side(p)
            }),
    ]
    .boxed()
}

/// A binding whose filter (when present) is drawn from `filter`.
fn binding(filter: BoxedStrategy<Cond>) -> BoxedStrategy<Binding> {
    (
        pick(VARS),
        source(),
        proptest::collection::vec(rel(), 0..3),
        proptest::option::of(filter),
    )
        .prop_map(|(name, source, rels, filter)| Binding {
            name,
            source,
            rels,
            filter,
            span: sp(),
        })
        .boxed()
}

fn cond_atom() -> BoxedStrategy<Cond> {
    let cmp = select(vec![
        CmpOp::Eq,
        CmpOp::Ne,
        CmpOp::Lt,
        CmpOp::Le,
        CmpOp::Gt,
        CmpOp::Ge,
    ]);
    let regex_rhs = prop_oneof![
        regex().prop_map(|r| sn(TermKind::Literal(sn(LiteralKind::Regex(r))))),
        path_term(),
    ];
    let in_rhs = prop_oneof![
        term(),
        (simple_term(), simple_term()).prop_map(|(lo, hi)| sn(TermKind::Range {
            lo: Box::new(lo),
            hi: Box::new(hi)
        })),
    ];
    prop_oneof![
        (simple_term(), rel()).prop_map(|(subject, r)| sn(CondKind::Rel {
            subject,
            rel: Box::new(r)
        })),
        (cmp, term(), term()).prop_map(|(op, lhs, rhs)| sn(CondKind::Cmp { op, lhs, rhs })),
        (simple_term(), regex_rhs).prop_map(|(lhs, rhs)| sn(CondKind::RegexMatch { lhs, rhs })),
        (simple_term(), simple_term()).prop_map(|(lhs, rhs)| sn(CondKind::GlobMatch { lhs, rhs })),
        (simple_term(), in_rhs).prop_map(|(lhs, rhs)| sn(CondKind::In { lhs, rhs })),
        (path_term(), select(vec!["public", "async", "function"])).prop_map(|(subject, t)| sn(
            CondKind::Is {
                subject,
                test: word(t)
            }
        )),
        (path_term(), snippet(), any::<bool>()).prop_map(|(subject, snippet, roles)| sn(
            CondKind::IsSnippet {
                subject,
                snippet,
                roles
            }
        )),
        (path_term(), plain_value()).prop_map(|(subject, a)| sn(CondKind::HasAttr {
            subject,
            attr: strlit(a)
        })),
        call().prop_map(|c| sn(CondKind::DefCall(c))),
        simple_term().prop_map(|t| sn(CondKind::Exists(t))),
        path_term().prop_map(|t| sn(CondKind::Flag(t))),
    ]
    .boxed()
}

fn cond() -> BoxedStrategy<Cond> {
    cond_atom()
        .prop_recursive(3, 20, 3, |inner| {
            prop_oneof![
                proptest::collection::vec(inner.clone(), 2..4).prop_map(|v| sn(CondKind::Or(v))),
                proptest::collection::vec(inner.clone(), 2..4).prop_map(|v| sn(CondKind::And(v))),
                inner.clone().prop_map(|c| sn(CondKind::Not(Box::new(c)))),
                proptest::collection::vec(inner.clone(), 1..3).prop_map(|v| sn(CondKind::Any(v))),
                (any::<bool>(), binding(inner)).prop_map(|(some, b)| sn(CondKind::Quant {
                    quant: if some { Quant::Some } else { Quant::No },
                    binding: Box::new(b)
                })),
            ]
        })
        .boxed()
}

fn message() -> impl Strategy<Value = Message> {
    let part = prop_oneof![
        text_value().prop_map(|value| MessagePart::Text { value, span: sp() }),
        path_of(VARS).prop_map(|path| MessagePart::Interp { path, span: sp() }),
    ];
    proptest::collection::vec(part, 0..4).prop_map(|parts| {
        // The parser never yields two adjacent text parts.
        let mut merged: Vec<MessagePart> = Vec::new();
        for p in parts {
            match (merged.last_mut(), p) {
                (Some(MessagePart::Text { value, .. }), MessagePart::Text { value: more, .. }) => {
                    value.push_str(&more);
                }
                (_, p) => merged.push(p),
            }
        }
        Message {
            parts: merged,
            span: sp(),
        }
    })
}

fn applicability() -> impl Strategy<Value = Option<Applicability>> {
    select(vec![
        None,
        Some(ApplicabilityKind::Machine),
        Some(ApplicabilityKind::MaybeIncorrect),
        Some(ApplicabilityKind::HasPlaceholders),
    ])
    .prop_map(|k| k.map(|kind| Applicability { kind, span: sp() }))
}

fn fix() -> BoxedStrategy<Fix> {
    prop_oneof![
        (
            select(vec![None, Some(Placement::Before), Some(Placement::After)]),
            pick(VARS),
            snippet(),
            applicability()
        )
            .prop_map(|(placement, target, with, applicability)| Fix {
                kind: FixKind::Replace {
                    placement,
                    target,
                    with,
                    with_span: sp()
                },
                applicability
            }),
        (pick(VARS), applicability()).prop_map(|(target, applicability)| Fix {
            kind: FixKind::Delete { target },
            applicability
        }),
        (
            select(vec!["rename", "inline"]),
            proptest::collection::vec(simple_term(), 0..3),
            applicability()
        )
            .prop_map(|(n, args, applicability)| Fix {
                kind: FixKind::Host {
                    name: word(n),
                    args
                },
                applicability
            }),
        message().prop_map(|message| Fix {
            kind: FixKind::Manual { message },
            applicability: None
        }),
    ]
    .boxed()
}

fn clause() -> BoxedStrategy<Clause> {
    prop_oneof![
        binding(cond()).prop_map(|b| sn(ClauseKind::Find(b))),
        cond().prop_map(|c| sn(ClauseKind::Where(c))),
        (any::<bool>(), binding(cond())).prop_map(|(some, b)| sn(ClauseKind::Quant {
            quant: if some { Quant::Some } else { Quant::No },
            binding: b
        })),
        (
            select(vec!["has_alt", "is_ok"]),
            proptest::collection::vec(pick(VARS), 0..3),
            cond()
        )
            .prop_map(|(n, params, body)| sn(ClauseKind::Def(Def {
                name: word(n),
                params,
                body
            }))),
        (pick(VARS), message(), proptest::option::of(cond())).prop_map(
            |(target, message, when)| sn(ClauseKind::Report(Report {
                target,
                message,
                when
            }))
        ),
        (pick(VARS), message())
            .prop_map(|(target, message)| sn(ClauseKind::Note(Note { target, message }))),
        fix().prop_map(|f| sn(ClauseKind::Fix(f))),
        (cond(), message())
            .prop_map(|(when, because)| sn(ClauseKind::Unresolved(Unresolved { when, because }))),
    ]
    .boxed()
}

/// A `where` clause straight after an unfiltered `find`/`some`/`no` clause would read back as its
/// filter; one after a clause that merely ends in an open binding is guarded by the printer.
fn separate_where_clauses(clauses: Vec<Clause>) -> Vec<Clause> {
    let mut out: Vec<Clause> = Vec::new();
    for c in clauses {
        let unfiltered = out.last().is_some_and(|p| match &p.node {
            ClauseKind::Find(b) | ClauseKind::Quant { binding: b, .. } => b.filter.is_none(),
            _ => false,
        });
        if unfiltered && matches!(c.node, ClauseKind::Where(_)) {
            out.push(sn(ClauseKind::Note(Note {
                target: word("x"),
                message: Message {
                    parts: Vec::new(),
                    span: sp(),
                },
            })));
        }
        out.push(c);
    }
    out
}

fn type_ref() -> BoxedStrategy<TypeRef> {
    select(vec![
        TypeKind::Int,
        TypeKind::Float,
        TypeKind::String,
        TypeKind::Bool,
        TypeKind::Glob,
        TypeKind::Regex,
        TypeKind::Vocab,
    ])
    .prop_map(sn)
    .prop_recursive(2, 4, 1, |inner| {
        inner.prop_map(|t| sn(TypeKind::List(Box::new(t))))
    })
    .boxed()
}

fn header() -> BoxedStrategy<Header> {
    prop_oneof![
        prop_oneof![
            Just(LangSet::Any { quoted: false }),
            Just(LangSet::Nothing),
            pick(LANGS).prop_map(LangSet::One),
            proptest::collection::vec(pick(LANGS), 1..3).prop_map(LangSet::List),
        ]
        .prop_map(|l| sn(HeaderKind::Lang(l))),
        select(vec![
            Polarity::Pplus,
            Polarity::Pminus,
            Polarity::P0,
            Polarity::Pn,
            Polarity::Pc
        ])
        .prop_map(|p| sn(HeaderKind::Polarity(p))),
        select(vec![Severity::Error, Severity::Warn, Severity::Advisory])
            .prop_map(|s| sn(HeaderKind::Severity(s))),
        select(vec![Scope::File, Scope::Repo]).prop_map(|s| sn(HeaderKind::Scope(s))),
        Just(sn(HeaderKind::MustMeasure)),
        proptest::collection::vec(pick(&["diff", "lease", "config"]), 1..3)
            .prop_map(|v| sn(HeaderKind::Needs(v))),
        select(vec![Rollup::File, Rollup::Directory, Rollup::Unit])
            .prop_map(|r| sn(HeaderKind::Rollup(r))),
        (
            pick(&["depth", "names"]),
            type_ref(),
            literal(),
            plain_value()
        )
            .prop_map(|(name, ty, default, doc)| sn(HeaderKind::Knob(Knob {
                name,
                ty,
                default,
                doc: strlit(doc)
            }))),
    ]
    .boxed()
}

/// Block text a parse can produce: no blank-only lines and no common indentation left.
fn block() -> impl Strategy<Value = BlockLit> {
    let line = (
        0usize..3,
        select(vec!["a", "fn f() {}", "x = 1", "# c", "\"q\"", ""]),
    );
    proptest::collection::vec(line, 0..4).prop_map(|lines| {
        let lines: Vec<(usize, &str)> = lines
            .into_iter()
            .map(|(n, c)| if c.is_empty() { (0, "") } else { (n, c) })
            .collect();
        let least = lines
            .iter()
            .filter(|(_, c)| !c.is_empty())
            .map(|(n, _)| *n)
            .min()
            .unwrap_or(0);
        let value = lines
            .iter()
            .map(|(n, c)| {
                if c.is_empty() {
                    String::new()
                } else {
                    format!("{}{c}", " ".repeat(n - least))
                }
            })
            .collect::<Vec<_>>()
            .join("\n");
        BlockLit {
            value,
            body: sp(),
            span: sp(),
        }
    })
}

fn input() -> BoxedStrategy<Input> {
    prop_oneof![
        (plain_value(), block()).prop_map(|(p, text)| sn(InputKind::File {
            path: strlit(p),
            text
        })),
        block().prop_map(|b| sn(InputKind::Config(b))),
        block().prop_map(|b| sn(InputKind::Model(b))),
        proptest::collection::vec(plain_value().prop_map(strlit), 0..3)
            .prop_map(|v| sn(InputKind::Diff(v))),
        proptest::collection::vec(plain_value().prop_map(strlit), 0..3)
            .prop_map(|v| sn(InputKind::Lease(v))),
        plain_value().prop_map(|s| sn(InputKind::Expect(strlit(s)))),
        block().prop_map(|b| sn(InputKind::Fixed(b))),
    ]
    .boxed()
}

fn example() -> BoxedStrategy<Example> {
    let body = prop_oneof![
        block().prop_map(ExampleBody::Source),
        proptest::collection::vec(input(), 0..4).prop_map(ExampleBody::Inputs),
    ];
    (
        select(vec![
            ExpectKind::Fire,
            ExpectKind::Clean,
            ExpectKind::Unresolved,
            ExpectKind::NotApplicable,
            ExpectKind::KnownGap,
        ]),
        proptest::option::of(pick(LANGS)),
        proptest::option::of(plain_value().prop_map(strlit)),
        body,
    )
        .prop_map(|(kind, lang, name, body)| Example {
            expect: Expect { kind, span: sp() },
            lang,
            name,
            body,
            span: sp(),
        })
        .boxed()
}

fn rule() -> BoxedStrategy<Rule> {
    (
        pick(&["TODO001", "NOPE002", "COV003"]),
        plain_value(),
        proptest::collection::vec(header(), 0..4),
        proptest::collection::vec(clause(), 0..5),
        proptest::collection::vec(example(), 0..3),
        block(),
    )
        .prop_map(|(id, slug, headers, clauses, examples, text)| Rule {
            id,
            slug: strlit(slug),
            headers,
            clauses: separate_where_clauses(clauses),
            examples,
            explain: Some(Explain { text, span: sp() }),
            span: sp(),
        })
        .boxed()
}

fn file() -> BoxedStrategy<File> {
    proptest::collection::vec(rule(), 1..3)
        .prop_map(|rules| File { rules })
        .boxed()
}

fn config(cases: u32) -> Config {
    Config {
        cases,
        failure_persistence: None,
        ..Config::default()
    }
}

// frob:tests crates/gob-plan/src/grl/print.rs::print
#[test]
fn generated_trees_round_trip_and_print_to_a_fixed_point() {
    let mut runner = TestRunner::new(config(128));
    let result = runner.run(&file(), |tree| {
        prop_assert_eq!(tree_instability(&print, &tree), None);
        Ok(())
    });
    assert!(result.is_ok(), "{result:?}");
}

// ---- the broken-printer self-tests ----

/// A source with `n` minimal rules, the smallest family that still varies in size.
fn source_of(n: usize) -> String {
    let mut out = String::new();
    for i in 0..n {
        let _ = write!(
            out,
            "rule SRC{:03} \"s\" {{\n  find x: file\n  report x \"r\"\n  example fire \"\"\"\n    a\n  \"\"\"\n  explain \"\"\"\n    e\n    ## Remedy\n    y\n  \"\"\"\n}}\n",
            i + 1
        );
    }
    out
}

/// A broken printer: every pass appends one more rule, so it never reaches a fixed point.
fn grows(src: &str) -> String {
    format!("{}{}", real(src), source_of(1).replace("SRC001", "BRK001"))
}

/// A broken printer: writes `or` for `and`, so a tree with a conjunction does not round-trip.
fn swaps_and_for_or(tree: &File) -> String {
    print(tree).replace(" and ", " or ")
}

// frob:tests crates/gob-plan/src/grl/print.rs::print
#[test]
fn the_real_printer_is_stable_over_generated_sizes() {
    let mut runner = TestRunner::new(config(32));
    let result = runner.run(&(1usize..8), |n| {
        prop_assert_eq!(instability(&real, &source_of(n)), None);
        Ok(())
    });
    assert!(result.is_ok(), "{result:?}");
}

// frob:tests crates/gob-plan/src/grl/print.rs::print
#[test]
fn a_printer_that_never_settles_fails_with_a_shrunk_minimal_example() {
    let mut runner = TestRunner::new(config(32));
    let result = runner.run(&(1usize..8), |n| {
        prop_assert_eq!(instability(&grows, &source_of(n)), None);
        Ok(())
    });
    match result {
        Err(TestError::Fail(_, minimal)) => assert_eq!(
            minimal, 1,
            "proptest shrinks the failure to the smallest source"
        ),
        other => panic!("the growing printer must fail the property, got {other:?}"),
    }
}

// frob:tests crates/gob-plan/src/grl/print.rs::print
#[test]
fn a_printer_that_changes_the_tree_fails_with_a_shrunk_minimal_tree() {
    let mut runner = TestRunner::new_with_rng(
        config(512),
        TestRng::deterministic_rng(RngAlgorithm::ChaCha),
    );
    let result = runner.run(&file(), |tree| {
        prop_assert_eq!(tree_instability(&swaps_and_for_or, &tree), None);
        Ok(())
    });
    match result {
        Err(TestError::Fail(_, minimal)) => {
            assert_eq!(minimal.rules.len(), 1, "shrinks to a single rule");
            assert!(
                print(&minimal).contains(" and "),
                "the shrunk tree still holds the conjunction:\n{}",
                print(&minimal)
            );
        }
        other => panic!("the and-for-or printer must fail the property, got {other:?}"),
    }
}
