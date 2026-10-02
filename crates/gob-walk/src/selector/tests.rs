//! Parser, printer and evaluator tests, including the grmb-spec 6 examples.

// frob:ticket 01M3Z713RETBN30XBC6CK11FBF

use proptest::prelude::*;

use super::*;

fn parse(s: &str) -> Selector {
    Selector::parse(s).unwrap_or_else(|e| panic!("{s}: {e:?}"))
}

fn node(expr: Expr) -> Node {
    Node {
        expr,
        span: Span::default(),
    }
}

#[test]
fn spec_examples_parse_and_print_canonically() {
    let cases = [
        (r#""crates/frob/**""#, r#""crates/frob/**""#),
        (
            r#""crates/frob-check/src/lib.rs::run""#,
            r#""crates/frob-check/src/lib.rs::run""#,
        ),
        (
            r#""crates/*/src/**"&lang(rust)&kind(function)"#,
            r#""crates/*/src/**" & lang(rust) & kind(function)"#,
        ),
        (
            r#"  "src/**" & !"src/gen/**" "#,
            r#""src/**" & !"src/gen/**""#,
        ),
        ("kind( function ,method )", "kind(function, method)"),
        ("attr(vis=pub)", "attr(vis = pub)"),
        ("attr(vis != private)", "attr(vis != private)"),
        (r#"attr(name ~ "get_*")"#, r#"attr(name ~ "get_*")"#),
        ("attr(age <= 30s)", "attr(age <= 30 s)"),
        ("attr(rate <= 5 req/s)", "attr(rate <= 5 req/s)"),
        ("attr(util <= 80 %)", "attr(util <= 80%)"),
        ("attr(size <= 4KiB)", "attr(size <= 4 KiB)"),
        ("attr(deprecated)", "attr(deprecated)"),
        ("!!lang(rust)", "!!lang(rust)"),
        (r#"!("a" | "b")"#, r#"!("a" | "b")"#),
        (r#"("a" | "b") & "c""#, r#"("a" | "b") & "c""#),
        (r#"("a" & "b") & "c""#, r#"("a" & "b") & "c""#),
        (r#""a" | "b" & "c""#, r#""a" | "b" & "c""#),
        (r#"(("a"))"#, r#""a""#),
    ];
    for (src, want) in cases {
        let s = parse(src);
        assert_eq!(s.to_string(), want, "{src}");
        assert_eq!(parse(&s.to_string()), s, "round trip of {src}");
    }
}

#[test]
fn precedence_is_not_then_and_then_or() {
    let s = parse(r#""a" | "b" & !"c""#);
    let Expr::Or(ops) = &s.root().expr else {
        panic!("or at the root")
    };
    assert!(matches!(ops[1].expr, Expr::And(_)));
    let Expr::And(inner) = &ops[1].expr else {
        unreachable!()
    };
    assert!(matches!(inner[1].expr, Expr::Not(_)));
}

#[test]
fn spans_cover_the_source_and_honor_the_base() {
    let text = r#""a" & lang(rust)"#;
    let s = Selector::parse_at(text, 100).unwrap();
    assert_eq!(
        s.root().span,
        Span {
            start: 100,
            end: 100 + text.len()
        }
    );
    let Expr::And(ops) = &s.root().expr else {
        panic!()
    };
    assert_eq!(
        ops[0].span,
        Span {
            start: 100,
            end: 103
        }
    );
    assert_eq!(
        ops[1].span,
        Span {
            start: 106,
            end: 100 + text.len()
        }
    );
}

#[test]
fn errors_carry_exact_positions() {
    let cases: [(&str, usize, usize, &str); 14] = [
        ("", 0, 0, "expected a glob string"),
        (r#""a" &"#, 5, 5, "expected a glob string"),
        (r#""a" "b""#, 4, 7, "unexpected"),
        ("lang(rust", 9, 9, "expected `)`"),
        ("foo(x)", 0, 3, "unknown predicate"),
        (r#""a"#, 0, 2, "unterminated string"),
        ("\"a\nb\"", 2, 3, "raw newline"),
        (r#""a\q""#, 2, 4, "unknown escape"),
        ("attr(x ~ 5)", 9, 10, "needs a string"),
        (r#"attr(x <= "s")"#, 10, 13, "needs a number"),
        ("attr(x <= 5 fortnights)", 11, 22, "closed unit table"),
        ("a < b", 2, 3, "must be written"),
        (r#""a/../b""#, 3, 4, ".."),
        (r#""ok" & "/abs""#, 8, 9, "leading"),
    ];
    for (src, start, end, needle) in cases {
        let errs = Selector::parse(src).unwrap_err();
        let e = &errs[0];
        assert_eq!((e.span.start, e.span.end), (start, end), "{src}: {e}");
        assert!(e.message.contains(needle), "{src}: {e}");
        let shifted = Selector::parse_at(src, 7).unwrap_err();
        assert_eq!(shifted[0].span.start, start + 7, "{src}");
    }
}

#[test]
fn glob_error_offsets_map_through_escapes() {
    // The glob text is `a\"/..`; the `..` segment starts after the escape at source byte 6.
    let src = r#""a\"/..""#;
    let e = &Selector::parse(src).unwrap_err()[0];
    assert!(e.message.contains(".."));
    assert_eq!(e.span.start, 5);
}

#[test]
fn string_escapes_round_trip() {
    let s = parse(r#""we\"ird\\name\u{e9}.rs""#);
    let Expr::Glob(g) = &s.root().expr else {
        panic!()
    };
    assert_eq!(g.path(), "we\"ird\\name\u{e9}.rs");
    assert_eq!(parse(&s.to_string()), s);
}

#[test]
fn literal_selectors() {
    assert!(parse(r#""a/b.rs::T.run""#).literal().is_some());
    assert!(parse(r#""a/*.rs""#).literal().is_none());
    assert!(parse(r#""a/b.rs" & lang(rust)"#).literal().is_none());
}

struct Fixed {
    glob: Tri,
    lang: Tri,
    kind: Tri,
    attr: Tri,
}

impl Leaves for Fixed {
    fn glob(&self, _: &Glob) -> Tri {
        self.glob
    }
    fn lang(&self, _: &str) -> Tri {
        self.lang
    }
    fn kind(&self, _: &[String]) -> Tri {
        self.kind
    }
    fn attr(&self, _: &AttrPred) -> Tri {
        self.attr
    }
}

#[test]
fn kleene_combinators_and_specificity_rows() {
    let l = Fixed {
        glob: Tri::Yes,
        lang: Tri::Yes,
        kind: Tri::Unknown,
        attr: Tri::No,
    };
    let s = parse(r#""src/**" & lang(rust) & kind(f)"#);
    let rows = s.rows(&l);
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].truth, Tri::Unknown);
    assert_eq!(rows[0].spec.components(), [1, 1, -1, 0, 0, 2]);

    assert_eq!(parse("attr(x) | lang(rust)").truth(&l), Tri::Yes);
    assert_eq!(parse("attr(x) & lang(rust)").truth(&l), Tri::No);
    assert_eq!(parse("!attr(x)").truth(&l), Tri::Yes);
    assert_eq!(parse("!kind(f)").truth(&l), Tri::Unknown);
    assert!(parse("attr(x) & lang(rust)").rows(&l).is_empty());
}

#[test]
fn or_keeps_both_a_must_row_and_a_more_specific_may_row() {
    let l = Fixed {
        glob: Tri::Yes,
        lang: Tri::Yes,
        kind: Tri::Unknown,
        attr: Tri::No,
    };
    let rows = parse(r#""a/b.rs" | "src/**" & kind(f)"#).rows(&l);
    // Both globs match with the same fixed leaf truth, so the file glob (Must, level 2) dominates.
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].truth, Tri::Yes);
}

fn glob_text() -> impl Strategy<Value = String> {
    prop::sample::select(vec![
        "src/**",
        "crates/*/src/**",
        "a/b.rs",
        "a/b.rs::T.run",
        "a/b.rs::T[Trait].*",
        "docs/",
        "{a,b}/x?.rs",
        "w\"ei\\rd.rs",
        "uni\u{e9}/**",
        "tab\t.rs",
    ])
    .prop_map(str::to_owned)
}

fn value() -> impl Strategy<Value = (Cmp, Value)> {
    prop_oneof![
        Just((Cmp::Eq, Value::Ident("pub".into()))),
        Just((Cmp::Ne, Value::Str("q\"x".into()))),
        Just((Cmp::Eq, Value::Number("42".into()))),
        Just((Cmp::Match, Value::Str("get_*".into()))),
        Just((
            Cmp::Le,
            Value::Quantity {
                number: "30".into(),
                unit: "s".into()
            }
        )),
        Just((
            Cmp::Le,
            Value::Quantity {
                number: "5".into(),
                unit: "req/s".into()
            }
        )),
        Just((
            Cmp::Le,
            Value::Quantity {
                number: "1.5".into(),
                unit: "%".into()
            }
        )),
        Just((Cmp::Le, Value::Number("7".into()))),
    ]
}

fn leaf_expr() -> impl Strategy<Value = Expr> {
    prop_oneof![
        glob_text().prop_map(|t| Expr::Glob(Glob::parse(&t).unwrap())),
        prop::sample::select(vec!["rust", "python", "markdown"])
            .prop_map(|l| Expr::Lang(l.to_owned())),
        prop::collection::vec(
            prop::sample::select(vec!["function", "method", "type"]),
            1..3
        )
        .prop_map(|k| Expr::Kind(k.into_iter().map(str::to_owned).collect())),
        ("[a-z_][a-z0-9_]{0,6}", prop::option::of(value()))
            .prop_map(|(name, test)| { Expr::Attr(AttrPred { name, test }) }),
    ]
}

fn expr() -> impl Strategy<Value = Expr> {
    leaf_expr().prop_recursive(4, 24, 3, |inner| {
        prop_oneof![
            inner.clone().prop_map(|e| Expr::Not(Box::new(node(e)))),
            prop::collection::vec(inner.clone(), 2..4)
                .prop_map(|v| Expr::And(v.into_iter().map(node).collect())),
            prop::collection::vec(inner, 2..4)
                .prop_map(|v| Expr::Or(v.into_iter().map(node).collect())),
        ]
    })
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(512))]

    #[test]
    fn parse_of_print_is_identity(e in expr()) {
        let s = Selector::new(node(e));
        let printed = s.to_string();
        let back = Selector::parse(&printed).map_err(|e| TestCaseError::fail(format!("{printed}: {e:?}")))?;
        prop_assert_eq!(&back, &s, "printed as {}", printed);
        prop_assert_eq!(back.to_string(), printed);
    }

    #[test]
    fn parser_never_panics(text in "\\PC{0,40}") {
        let _ = Selector::parse(&text);
    }
}
