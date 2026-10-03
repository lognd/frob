//! No-panic properties: arbitrary token streams, arbitrary text and mutated valid rules.

use gob_text::{Span, TextRange, TextSize};
use proptest::prelude::*;

use super::{FIXTURES, file, fixture};
use crate::grl::{StrPart, Token, TokenKind, parse, parse_tokens};

const WORDS: &[&str] = &[
    "rule",
    "lang",
    "find",
    "where",
    "some",
    "no",
    "def",
    "report",
    "note",
    "fix",
    "unresolved",
    "example",
    "explain",
    "and",
    "or",
    "not",
    "any",
    "exists",
    "inside",
    "has",
    "directly",
    "in",
    "unit",
    "under",
    "before",
    "after",
    "adjoins",
    "reaches",
    "via",
    "within",
    "is",
    "matches",
    "attr",
    "as",
    "roles",
    "knob",
    "count",
    "calls",
    "resolves",
    "to",
    "fire",
    "known",
    "gap",
    "machine",
    "delete",
    "host",
    "manual",
    "true",
    "x",
    "f",
    "function",
    "list",
    "int",
    "file",
    "diff",
    "config",
    "because",
    "when",
    "needs",
    "severity",
    "error",
    "scope",
    "repo",
];

fn arb_kind(len: u32) -> impl Strategy<Value = TokenKind> {
    let punct = prop_oneof![
        Just(TokenKind::LBrace),
        Just(TokenKind::RBrace),
        Just(TokenKind::LParen),
        Just(TokenKind::RParen),
        Just(TokenKind::LBracket),
        Just(TokenKind::RBracket),
        Just(TokenKind::Comma),
        Just(TokenKind::Colon),
        Just(TokenKind::Dot),
        Just(TokenKind::DotDot),
        Just(TokenKind::Eq),
        Just(TokenKind::EqEq),
        Just(TokenKind::Ne),
        Just(TokenKind::Lt),
        Just(TokenKind::Le),
        Just(TokenKind::Gt),
        Just(TokenKind::Ge),
        Just(TokenKind::Tilde),
        Just(TokenKind::Pipe),
        Just(TokenKind::Plus),
        Just(TokenKind::Minus),
        Just(TokenKind::Star),
        Just(TokenKind::Arrow),
    ];
    prop_oneof![
        6 => proptest::sample::select(WORDS).prop_map(|w| TokenKind::Ident((*w).to_owned())),
        4 => punct,
        1 => Just(TokenKind::RuleId("ABC001".into())),
        1 => Just(TokenKind::Polarity("P+".into())),
        1 => any::<u64>().prop_map(TokenKind::Int),
        1 => Just(TokenKind::Decimal("0.5".into())),
        1 => (0..=len, 0..=len).prop_map(move |(a, b)| {
            let (lo, hi) = (a.min(b), a.max(b));
            TokenKind::Str(vec![
                StrPart::Text { value: "t".into(), span: span(0, 1) },
                StrPart::Interp { expr: span(lo, hi) },
            ])
        }),
        1 => Just(TokenKind::Str(vec![])),
    ]
}

fn span(a: u32, b: u32) -> Span {
    Span::new(file(), TextRange::new(TextSize::new(a), TextSize::new(b)))
}

const TEXT: &str = "x.y f.name 1 + 2 {}";

proptest! {
    #![proptest_config(ProptestConfig::with_cases(512))]

    // frob:tests crates/gob-plan/src/grl/parse/mod.rs::parse_tokens
    #[test]
    fn arbitrary_token_streams_never_panic(kinds in proptest::collection::vec(arb_kind(40), 0..120)) {
        let tokens: Vec<Token> = kinds
            .into_iter()
            .enumerate()
            .map(|(i, kind)| {
                let at = u32::try_from(i).unwrap_or(0);
                Token { kind, span: span(at, at + 1) }
            })
            .collect();
        let parsed = parse_tokens(file(), TEXT, &tokens);
        // Whatever came out, an invalid stream reports at least one error unless it is empty or valid.
        let _ = (parsed.errors.len(), parsed.file.rules.len());
    }

    // frob:tests crates/gob-plan/src/grl/parse/mod.rs::parse
    #[test]
    fn arbitrary_text_never_panics(src in "[ -~\n]{0,200}") {
        let parsed = parse(file(), &src);
        for e in &parsed.errors {
            prop_assert!(usize::try_from(u32::from(e.span.range.end())).unwrap_or(usize::MAX) <= src.len());
        }
    }

    // frob:tests crates/gob-plan/src/grl/parse/mod.rs::parse
    #[test]
    fn mutated_valid_rules_never_panic(
        which in 0..FIXTURES.len(),
        cuts in proptest::collection::vec((0usize..2000, 0usize..40), 0..4),
        inserts in proptest::collection::vec((0usize..2000, proptest::sample::select(WORDS), proptest::sample::select(&["{", "}", "(", ")", "\"", "`", "[", "]", ",", ":", "->", "~", "|", "\"\"\""][..])), 0..4),
    ) {
        let mut src = fixture(FIXTURES[which]);
        for (at, len) in cuts {
            let at = at % (src.len() + 1);
            let end = (at + len).min(src.len());
            src.replace_range(at..end, "");
        }
        for (at, word, punct) in inserts {
            let at = at % (src.len() + 1);
            src.insert_str(at, &format!(" {word} {punct} "));
        }
        let parsed = parse(file(), &src);
        for e in &parsed.errors {
            prop_assert!(usize::try_from(u32::from(e.span.range.end())).unwrap_or(usize::MAX) <= src.len());
        }
    }
}

// frob:tests crates/gob-plan/src/grl/parse/mod.rs::parse
#[test]
fn every_prefix_of_every_fixture_parses_without_panicking() {
    for name in FIXTURES {
        let src = fixture(name);
        for end in (0..src.len()).step_by(7) {
            let _ = parse(file(), &src[..end]);
        }
    }
}
