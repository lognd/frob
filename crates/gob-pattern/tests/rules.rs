//! Level-2 rule files over U terms (frob:ticket 01M3Z714QT3QXEAJAK9JDDEB70).

use gob_ir::{Location, NodeId, NodeSpec, Operator, Term, TermBuilder};
use gob_pattern::{PatternError, RuleFile};
use gob_text::FileInterner;

const NO_PRINT: &str = r#"
id = "GPOL001"
alias = "no-print-in-lib"
language = "*"
severity = "warn"
message = "use the logger, not print"
rule = { kind = "call", callee = "print", not = { inside = { kind = "function", role = "cli" } } }
"#;

/// A function (role `impl`) calling `print`, built for `lang`; returns the term and the call.
fn fixture(lang: &str, role: &str, callee: &str) -> (Term, NodeId) {
    let mut files = FileInterner::new();
    let f = files.intern("a.src");
    let loc = |a, b| Location::text(f, a, b);
    let mut b = TermBuilder::new("a.src", lang);
    let head = b
        .node(
            NodeSpec::new(Operator::reference(callee), loc(0, 5)).lang(lang),
            &[],
        )
        .unwrap();
    let call = b
        .node(
            NodeSpec::new(Operator::apply("call"), loc(0, 9)).lang(lang),
            &[head],
        )
        .unwrap();
    let func = b
        .node(
            NodeSpec::new(Operator::unit("function", role), loc(0, 20))
                .named("f")
                .lang(lang),
            &[call],
        )
        .unwrap();
    (b.finish(func).unwrap(), call)
}

#[test]
fn one_rule_file_fires_in_rust_and_python() {
    let rule = RuleFile::parse(NO_PRINT).unwrap();
    for lang in ["rust", "python"] {
        let (term, call) = fixture(lang, "impl", "print");
        assert_eq!(rule.find(&term), vec![call], "{lang}");
    }
}

#[test]
fn not_inside_and_other_callee_do_not_fire() {
    let rule = RuleFile::parse(NO_PRINT).unwrap();
    assert!(rule.find(&fixture("python", "cli", "print").0).is_empty());
    assert!(rule.find(&fixture("python", "impl", "log").0).is_empty());
}

#[test]
fn language_restriction_and_has() {
    let text = NO_PRINT.replace("\"*\"", "\"python\"");
    let rule = RuleFile::parse(&text).unwrap();
    assert!(rule.find(&fixture("rust", "impl", "print").0).is_empty());
    let has = RuleFile::parse(&NO_PRINT.replace(
        r#"rule = { kind = "call", callee = "print", not = { inside = { kind = "function", role = "cli" } } }"#,
        r#"rule = { kind = "function", has = { kind = "call", callee = "print" } }"#,
    ))
    .unwrap();
    let (term, _) = fixture("rust", "impl", "print");
    assert_eq!(has.find(&term), vec![term.root()]);
}

#[test]
fn compile_errors_are_typed() {
    let bad_id = NO_PRINT.replace("GPOL001", "X1");
    assert_eq!(
        RuleFile::parse(&bad_id),
        Err(PatternError::BadId("X1".into()))
    );
    let pat = NO_PRINT.replace("kind = \"call\"", "pattern = \"print($$$A)\"");
    assert_eq!(
        RuleFile::parse(&pat),
        Err(PatternError::PatternNeedsLanguage)
    );
    assert!(matches!(
        RuleFile::parse(&NO_PRINT.replace("callee", "calee")),
        Err(PatternError::Malformed(_))
    ));
    let empty = NO_PRINT.replace(r#"{ kind = "call", callee = "print", not = { inside = { kind = "function", role = "cli" } } }"#, "{}");
    assert_eq!(RuleFile::parse(&empty), Err(PatternError::EmptyRule));
}
