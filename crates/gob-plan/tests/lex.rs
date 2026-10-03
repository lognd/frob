//! Lexer behaviour: the acceptance examples, each token kind, errors, and a no-panic property.

use gob_plan::grl::{LexErrorKind, Lexed, MetaKind, StrPart, TokenKind, lex, lex_range};
use gob_text::{FileInterner, TextRange};
use proptest::prelude::*;

fn file() -> gob_text::FileId {
    FileInterner::new().intern("rules/T.grl")
}

fn ok(src: &str) -> Lexed {
    lex(file(), src).expect("source lexes")
}

fn kinds(src: &str) -> Vec<TokenKind> {
    ok(src).tokens.into_iter().map(|t| t.kind).collect()
}

fn err(src: &str) -> gob_plan::grl::LexError {
    lex(file(), src).expect_err("source must not lex")
}

fn id(s: &str) -> TokenKind {
    TokenKind::Ident(s.into())
}

// frob:tests gob_plan::grl::lex
#[test]
fn acceptance_one_comment_snippets_block_regex() {
    let src = "# a comment\n\
               find d: `dbg!($$$ARGS)`\n\
               find e: ``a `b` c``\n\
               explain \"\"\"\n    first\n      second\n    \"\"\"\n\
               where c.text ~ /re/i\n";
    let lexed = ok(src);
    assert_eq!(lexed.comments.len(), 1);
    assert_eq!(
        &src[lexed.comments[0].span.range.to_usize_range()],
        "# a comment"
    );
    let toks: Vec<_> = lexed.tokens.iter().map(|t| &t.kind).collect();
    let TokenKind::Snippet(one) = toks[3] else {
        panic!("expected snippet, got {:?}", toks[3]);
    };
    assert_eq!(one.text, "dbg!($$$ARGS)");
    assert_eq!(one.ticks, 1);
    assert_eq!(one.metavars.len(), 1);
    assert_eq!(one.metavars[0].kind, MetaKind::Seq);
    assert_eq!(one.metavars[0].name.as_deref(), Some("ARGS"));
    assert_eq!(&src[one.metavars[0].span.range.to_usize_range()], "$$$ARGS");
    let TokenKind::Snippet(two) = toks[7] else {
        panic!("expected snippet, got {:?}", toks[7]);
    };
    assert_eq!((two.ticks, two.text.as_str()), (2, "a `b` c"));
    let TokenKind::Block(block) = toks[9] else {
        panic!("expected block, got {:?}", toks[9]);
    };
    assert_eq!(block.value, "first\n  second");
    let TokenKind::Regex(re) = toks.last().copied().unwrap() else {
        panic!("expected regex");
    };
    assert_eq!(re.pattern, "re");
    assert!(re.ignore_case && !re.multi_line);
    // Spans address the real text.
    let t = &lexed.tokens[3];
    assert_eq!(&src[t.span.range.to_usize_range()], "`dbg!($$$ARGS)`");
}

// frob:tests gob_plan::grl::lex
#[test]
fn acceptance_two_non_ascii_name_is_a_located_error() {
    let src = "find caf\u{e9}: function";
    let e = err(src);
    assert!(matches!(
        e.kind,
        LexErrorKind::NonAscii { ch: '\u{e9}', .. }
    ));
    assert_eq!(&src[e.span.range.to_usize_range()], "\u{e9}");
    assert!(e.to_string().contains("not plain ASCII"), "{e}");
    assert!(e.help().is_some());
    assert!(matches!(err("\u{3b1}").kind, LexErrorKind::NonAscii { .. }));
    // A non-alphanumeric symbol (found by the property test) is an error, not a panic.
    assert!(matches!(
        err("\u{1d200}").kind,
        LexErrorKind::NonAscii { word: None, .. }
    ));
}

// frob:tests gob_plan::grl::lex
#[test]
fn every_token_kind() {
    use TokenKind as T;
    assert_eq!(kinds("find max_depth"), vec![id("find"), id("max_depth")]);
    assert_eq!(kinds("TODO001"), vec![T::RuleId("TODO001".into())]);
    assert_eq!(
        kinds("P+ P- P0 Pn Pc"),
        ["P+", "P-", "P0", "Pn", "Pc"]
            .map(|s| T::Polarity(s.into()))
            .to_vec()
    );
    assert_eq!(
        kinds("12 0.75 1..3"),
        vec![
            T::Int(12),
            T::Decimal("0.75".into()),
            T::Int(1),
            T::DotDot,
            T::Int(3)
        ]
    );
    assert_eq!(
        kinds("{ } ( ) [ ] , : . .. = == != < <= > >= ~ | + - * ->"),
        vec![
            T::LBrace,
            T::RBrace,
            T::LParen,
            T::RParen,
            T::LBracket,
            T::RBracket,
            T::Comma,
            T::Colon,
            T::Dot,
            T::DotDot,
            T::Eq,
            T::EqEq,
            T::Ne,
            T::Lt,
            T::Le,
            T::Gt,
            T::Ge,
            T::Tilde,
            T::Pipe,
            T::Plus,
            T::Minus,
            T::Star,
            T::Arrow
        ]
    );
}

#[test]
fn strings_escapes_and_interpolation() {
    let src = r#""a \"q\" \\ \n {d.name} b {f("x}")} \{lit\}""#;
    let toks = kinds(src);
    let [TokenKind::Str(parts)] = toks.as_slice() else {
        panic!("{toks:?}")
    };
    let text = |p: &StrPart| match p {
        StrPart::Text { value, .. } => value.clone(),
        StrPart::Interp { expr } => format!("<{}>", &src[expr.range.to_usize_range()]),
    };
    let got: Vec<String> = parts.iter().map(text).collect();
    assert_eq!(
        got,
        vec!["a \"q\" \\ \n ", "<d.name>", " b ", "<f(\"x}\")>", " {lit}"]
    );
    assert_eq!(kinds("\"\""), vec![TokenKind::Str(vec![])]);
}

#[test]
fn interpolation_expression_relexes() {
    let src = "\"x {a.b} y\"";
    let lexed = ok(src);
    let TokenKind::Str(parts) = &lexed.tokens[0].kind else {
        panic!()
    };
    let StrPart::Interp { expr } = &parts[1] else {
        panic!()
    };
    let inner = lex_range(file(), src, expr.range).unwrap();
    assert_eq!(inner.tokens.len(), 3);
    assert_eq!(inner.tokens[0].span.range.start(), 4u32.into());
}

#[test]
fn block_string_dedent_rules() {
    let b = |s: &str| match kinds(s).pop().unwrap() {
        TokenKind::Block(b) => b.value,
        other => panic!("{other:?}"),
    };
    assert_eq!(b("\"\"\"\n  a\n\n    b\n  \"\"\""), "a\n\n  b");
    assert_eq!(b("\"\"\"x \"y\" `z` {w}\"\"\""), "x \"y\" `z` {w}");
    assert_eq!(b("\"\"\"\r\n\ta\r\n\t\"\"\""), "a");
    assert_eq!(b("\"\"\"\"\"\""), "");
}

#[test]
fn snippets_tags_dollars_and_metavars() {
    let src = "rust`$X.unwrap($_, $$$, $$5 $$$$ $A_1)`";
    let toks = kinds(src);
    let [TokenKind::Snippet(s)] = toks.as_slice() else {
        panic!("{toks:?}")
    };
    assert_eq!(s.lang.as_ref().unwrap().name, "rust");
    let names: Vec<_> = s
        .metavars
        .iter()
        .map(|m| (m.kind, m.name.as_deref()))
        .collect();
    assert_eq!(
        names,
        vec![
            (MetaKind::One, Some("X")),
            (MetaKind::One, None),
            (MetaKind::Seq, None),
            (MetaKind::One, Some("A_1")),
        ]
    );
    assert_eq!(s.dollars.len(), 3);
    assert_eq!(s.text, "$X.unwrap($_, $$$, $$5 $$$$ $A_1)");
    // Multi-line, non-ASCII text is fine inside a snippet.
    assert!(matches!(kinds("`caf\u{e9}\nx`")[0], TokenKind::Snippet(_)));
    // A space before the backtick means no tag.
    assert_eq!(kinds("rust `x`").len(), 2);
}

#[test]
fn regex_flags_and_classes() {
    let t = kinds(r"/a\/b[/]c/im");
    let [TokenKind::Regex(r)] = t.as_slice() else {
        panic!()
    };
    assert_eq!(r.pattern, r"a\/b[/]c");
    assert!(r.ignore_case && r.multi_line);
}

#[test]
fn comments_are_dropped_but_kept() {
    let lexed = ok("a # one `not a snippet\nb #two\r\n# three");
    assert_eq!(lexed.tokens.len(), 2);
    assert_eq!(lexed.comments.len(), 3);
}

#[test]
fn error_messages_and_spans() {
    let cases: &[(&str, &str, &str)] = &[
        ("x = \"open", "this string is never closed", "\"open"),
        ("x \"a\\tb\"", "`\\t` is not an escape", "\\t"),
        (
            "`never",
            "this snippet is never closed (it needs 1 closing backtick)",
            "`",
        ),
        ("``a `b`", "needs 2 closing backticks", "``"),
        ("`a $ b`", "a lone `$` in a snippet", "$"),
        ("`$x`", "`$x` is not uppercase", "$x"),
        ("\"\"\"never", "this block string is never closed", "\"\"\""),
        ("/abc", "this regular expression is never closed", "/abc"),
        ("/a/x", "`x` is not a regex flag", "x"),
        ("/a/ii", "given twice", "i"),
        ("//", "is empty", "//"),
        ("\"{\"", "never closed", "{"),
        ("\"{}\"", "needs an expression", "{}"),
        ("fooBar", "`fooBar` is not a valid name", "fooBar"),
        ("Foo", "`Foo` is not a valid name or rule id", "Foo"),
        ("TODO12", "rule id", "TODO12"),
        ("12ab", "`12ab` is not a valid number", "12ab"),
        ("99999999999999999999", "too large", "99999999999999999999"),
        ("a @ b", "`@` is not part of the rule language", "@"),
        ("a ! b", "`!`", "!"),
        ("/caf\u{e9}/", "not plain ASCII", "\u{e9}"),
    ];
    for (src, needle, at) in cases {
        let e = lex(file(), src).expect_err(src);
        assert!(e.to_string().contains(needle), "{src}: {e}");
        assert_eq!(&src[e.span.range.to_usize_range()], *at, "{src}: {e}");
    }
}

#[test]
fn bad_range_is_an_error() {
    let r = lex_range(file(), "ab", TextRange::new(0u32.into(), 9u32.into()));
    assert_eq!(r.unwrap_err().kind, LexErrorKind::BadRange);
}

/// Tokens and comments are ordered, disjoint, and the gaps between them are ASCII whitespace.
fn assert_tiles(src: &str, lexed: &Lexed) {
    let mut at = 0usize;
    for r in lexed.covered() {
        let (s, e) = (r.start().to_usize(), r.end().to_usize());
        assert!(
            s >= at && e >= s && e <= src.len(),
            "overlap or overflow in {src:?}"
        );
        assert!(
            src[at..s]
                .chars()
                .all(|c| matches!(c, ' ' | '\t' | '\n' | '\r')),
            "non-whitespace gap {:?} in {src:?}",
            &src[at..s]
        );
        at = e;
    }
    assert!(
        src[at..]
            .chars()
            .all(|c| matches!(c, ' ' | '\t' | '\n' | '\r')),
        "non-whitespace tail in {src:?}"
    );
}

fn check_input(src: &str) {
    match lex(file(), src) {
        Ok(lexed) => assert_tiles(src, &lexed),
        Err(e) => {
            let (s, t) = (
                e.span.range.start().to_usize(),
                e.span.range.end().to_usize(),
            );
            assert!(s <= t && t <= src.len(), "error span outside input: {e}");
            assert!(src.is_char_boundary(s) && src.is_char_boundary(t));
            let _ = (e.to_string(), e.help());
        }
    }
}

proptest! {
    #[test]
    fn arbitrary_text_never_panics_and_tiles(src in any::<String>()) {
        check_input(&src);
    }

    #[test]
    fn grammar_flavoured_text_never_panics_and_tiles(
        src in proptest::collection::vec(
            prop_oneof![
                Just("`"), Just("``"), Just("$"), Just("$$"), Just("$$$"), Just("\""),
                Just("\"\"\""), Just("{"), Just("}"), Just("#"), Just("/"), Just("\\"),
                Just("["), Just("]"), Just(" "), Just("\n"), Just("\r\n"), Just("a"), Just("_"),
                Just("Z"), Just("7"), Just("."), Just(".."), Just("-"), Just("->"), Just("<="),
                Just("!"), Just("~"), Just("P"), Just("i"), Just("\u{e9}"), Just("X1"),
                Just("TODO001"), Just("rust"),
            ],
            0..40,
        ).prop_map(|v| v.concat())
    ) {
        check_input(&src);
    }
}
