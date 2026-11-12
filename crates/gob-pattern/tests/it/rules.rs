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
    let mut b = TermBuilder::new("a.src", lang);
    let head = b
        .node(
            NodeSpec::new(Operator::reference(callee), Location::text(f, 0, 5)).lang(lang),
            &[],
        )
        .unwrap();
    let call = b
        .node(
            NodeSpec::new(Operator::apply("call"), Location::text(f, 0, 9)).lang(lang),
            &[head],
        )
        .unwrap();
    let func = b
        .node(
            NodeSpec::new(Operator::unit("function", role), Location::text(f, 0, 20))
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
}

#[test]
fn language_restriction_and_has_part_2() {
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
}

#[test]
fn compile_errors_are_typed_part_2() {
    let pat = NO_PRINT.replace("kind = \"call\"", "pattern = \"print($$$A)\"");
    assert_eq!(
        RuleFile::parse(&pat),
        Err(PatternError::PatternNeedsLanguage)
    );
    assert!(matches!(
        RuleFile::parse(&NO_PRINT.replace("callee", "calee")),
        Err(PatternError::Malformed(_))
    ));
}

#[test]
fn compile_errors_are_typed_part_3() {
    let empty = NO_PRINT.replace(r#"{ kind = "call", callee = "print", not = { inside = { kind = "function", role = "cli" } } }"#, "{}");
    assert_eq!(RuleFile::parse(&empty), Err(PatternError::EmptyRule));
}

/// Two siblings under a function: a `print` call then a `log` call.
fn two_calls() -> (Term, NodeId, NodeId) {
    let mut files = FileInterner::new();
    let f = files.intern("a.src");
    let mut b = TermBuilder::new("a.src", "python");
    let mut call = |name: &str, at: u32| {
        let head = b
            .node(
                NodeSpec::new(Operator::reference(name), Location::text(f, at, at + 3))
                    .lang("python"),
                &[],
            )
            .unwrap();
        b.node(
            NodeSpec::new(Operator::apply("call"), Location::text(f, at, at + 5)).lang("python"),
            &[head],
        )
        .unwrap()
    };
    let first = call("print", 0);
    let second = call("log_it", 10);
    let func = b
        .node(
            NodeSpec::new(Operator::unit("function", "impl"), Location::text(f, 0, 30))
                .named("f")
                .lang("python"),
            &[first, second],
        )
        .unwrap();
    (b.finish(func).unwrap(), first, second)
}

fn rule_with(table: &str) -> RuleFile {
    RuleFile::parse(&NO_PRINT.replace(
        r#"{ kind = "call", callee = "print", not = { inside = { kind = "function", role = "cli" } } }"#,
        table,
    ))
    .unwrap()
}

// frob:tests crates/gob-pattern/src/lib.rs::matches
#[test]
fn follows_precedes_and_regex_constrain_siblings() {
    let (term, first, second) = two_calls();
    let follows = rule_with(r#"{ kind = "call", follows = { kind = "call", callee = "print" } }"#);
    assert_eq!(follows.find(&term), vec![second]);
    let precedes = rule_with(r#"{ kind = "call", precedes = { kind = "call" } }"#);
    assert_eq!(precedes.find(&term), vec![first]);
    let regex = rule_with(r#"{ kind = "ref", regex = "^log_" }"#);
    assert_eq!(regex.find(&term).len(), 1);
    let both = rule_with(
        r#"{ kind = "call", follows = { kind = "call" }, has = { kind = "ref", regex = "^print$" } }"#,
    );
    assert!(both.find(&term).is_empty());
}

// frob:tests crates/gob-pattern/src/lib.rs::parse
#[test]
fn bad_regex_and_stray_constraints_are_typed_errors() {
    let bad = NO_PRINT.replace(r#"callee = "print""#, r#"regex = "(""#);
    assert!(matches!(
        RuleFile::parse(&bad),
        Err(PatternError::BadRegex { .. })
    ));
    let stray = NO_PRINT.replace(
        r#"callee = "print""#,
        r#"constraints = { X = { kind = "identifier" } }"#,
    );
    assert_eq!(
        RuleFile::parse(&stray),
        Err(PatternError::ConstraintsWithoutPattern)
    );
}
