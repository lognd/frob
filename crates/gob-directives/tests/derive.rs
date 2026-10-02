//! `#[derive(Directive)]` over every argument mode and supported type.

mod common;

use gob_directives::{ArgError, ArgKind, Directive, ScanConfig, all_directives};

/// Exercise every argument mode.
#[derive(Debug, PartialEq, Directive)]
#[directive(namespace = "demo", verb = "all-modes")]
struct AllModes {
    /// First word.
    #[arg(positional)]
    name: String,
    #[arg(positional)]
    count: Option<u32>,
    /// Remaining words.
    #[arg(list)]
    rest: Vec<String>,
    #[arg(key = "flag")]
    flag: bool,
    #[arg(key = "other", optional)]
    other: Option<String>,
}

fn scan(text: &str) -> gob_directives::ScanResult {
    let cfg = ScanConfig {
        namespaces: vec!["demo".into()],
        product: "frob".into(),
    };
    common::scan_with(&cfg, "src/a.rs", &format!("// demo:all-modes {text}\n"))
}

fn parse(text: &str) -> Result<AllModes, ArgError> {
    let r = scan(text);
    assert!(r.findings.is_empty(), "scanner rejected: {:?}", r.findings);
    AllModes::parse_args(&r.directives[0].args)
}

/// The PARSE001 message the scanner gives for `text`.
fn rejected(text: &str) -> String {
    let r = scan(text);
    assert_eq!(r.findings[0].rule.as_str(), "PARSE001");
    r.findings[0].message.clone()
}

#[test]
fn parses_every_mode() {
    let v = parse("n 7 a b flag=true other=x").unwrap();
    assert_eq!(
        v,
        AllModes {
            name: "n".into(),
            count: Some(7),
            rest: vec!["a".into(), "b".into()],
            flag: true,
            other: Some("x".into())
        }
    );
}

#[test]
fn optionals_may_be_absent() {
    let v = parse("n flag=false").unwrap();
    assert_eq!((v.count, v.other, v.rest.len()), (None, None, 0));
}

#[test]
fn constants_and_meta() {
    assert_eq!((AllModes::NAMESPACE, AllModes::VERB), ("demo", "all-modes"));
    let m = all_directives().find(|m| m.namespace == "demo").unwrap();
    assert_eq!(m.summary, "Exercise every argument mode.");
    let names: Vec<_> = m.args.iter().map(|a| a.name).collect();
    assert_eq!(names, ["name", "count", "rest", "flag", "other"]);
    assert_eq!(m.args[0].summary, "First word.");
    assert!(m.args[0].positional && !m.args[0].optional);
    assert!(m.args[1].optional && m.args[1].kind == ArgKind::U32);
    assert!(m.args[2].list);
    assert_eq!(m.args[3].key, Some("flag"));
    assert_eq!(m.args[3].kind, ArgKind::Bool);
}

#[test]
fn typed_errors() {
    assert!(rejected("n 7").contains("missing required argument `flag`"));
    assert!(rejected("n x flag=true").contains("invalid value \"x\" for `count`"));
    assert!(rejected("n flag=maybe").contains("`true` or `false`"));
    assert!(rejected("n flag=true flag=true").contains("more than once"));
    assert!(rejected("n flag=true zzz=1").contains("unknown argument `zzz=`"));
    assert!(rejected("").contains("missing required argument `name`"));
}
