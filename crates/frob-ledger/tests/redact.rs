//! The redaction engine: local rules parse, match, replace and report without ever echoing a term.
// frob:ticket 01M42EZ8J63P84XFKTR2GXRW72

use frob_ledger::redact::{RuleSet, tick005};

const TERM: &str = "zorblax-7";

fn rules(extra: &str) -> RuleSet {
    RuleSet::from_toml(
        &format!("[[rule]]\npattern = \"{TERM}\"\nreplace = \"<private-host>\"\n{extra}"),
        "test",
    )
    .expect("rules")
}

/// A literal rule matches exactly, replaces with its label, and reports label and hash only.
// frob:tests crates/frob-ledger/src/redact.rs::RuleSet.first_private_hit
// frob:tests crates/frob-ledger/src/redact.rs::RuleSet.apply_private
#[test]
fn literal_rule_matches_and_replaces() {
    let r = rules("");
    let hit = r
        .first_private_hit(&format!("ran on {TERM} today"))
        .expect("hit");
    assert_eq!(hit.label, "<private-host>");
    assert_eq!(hit.hash.len(), 12);
    assert!(!hit.to_string().contains(TERM));
    assert!(r.first_private_hit("ran on ZORBLAX-7").is_none());
    assert_eq!(
        r.apply_private(&format!("a {TERM} b {TERM}")),
        "a <private-host> b <private-host>"
    );
}

/// Case-insensitive and regex rules work, and a literal's regex metacharacters are escaped.
// frob:tests crates/frob-ledger/src/redact.rs::RuleSet.from_toml
#[test]
fn flags_and_regex() {
    let ci = rules("case_sensitive = false\n");
    assert!(ci.first_private_hit("ZORBLAX-7").is_some());
    let re = RuleSet::from_toml(
        "[[rule]]\npattern = 'node-[0-9]+'\nreplace = \"<node>\"\nregex = true\n",
        "t",
    )
    .expect("re");
    assert_eq!(
        re.apply_private("on node-42 and node-7"),
        "on <node> and <node>"
    );
    let lit =
        RuleSet::from_toml("[[rule]]\npattern = \"a.c\"\nreplace = \"<x>\"\n", "t").expect("lit");
    assert!(lit.first_private_hit("abc").is_none());
}

/// Bad files fail without quoting any pattern, and a label that matches its own pattern is refused.
// frob:tests crates/frob-ledger/src/redact.rs::RuleSet.from_toml
#[test]
fn errors_never_echo_the_pattern() {
    let bad_regex = RuleSet::from_toml(
        "[[rule]]\npattern = 'zorblax-(7'\nreplace = \"<x>\"\nregex = true\n",
        "t",
    )
    .expect_err("regex");
    let bad_toml =
        RuleSet::from_toml("[[rule]]\npattern = \"zorblax-7\nreplace", "t").expect_err("toml");
    let selfy = RuleSet::from_toml(
        "[[rule]]\npattern = \"zorblax\"\nreplace = \"zorblax-x\"\n",
        "t",
    )
    .expect_err("self");
    let empty =
        RuleSet::from_toml("[[rule]]\npattern = \"\"\nreplace = \"x\"\n", "t").expect_err("empty");
    for e in [bad_regex, bad_toml, selfy, empty] {
        assert!(!e.to_string().contains("zorblax"), "{e}");
    }
}

/// Debug output of a rule set carries labels and hashes, never a term.
// frob:tests crates/frob-ledger/src/redact.rs::Rule
#[test]
fn debug_hides_terms() {
    let r = rules("");
    assert!(!format!("{r:?}").contains(TERM));
}

/// The built-in home-path rule shares detection with private rules and does not count as private.
// frob:tests crates/frob-ledger/src/redact.rs::RuleSet.with_home_path
#[test]
fn home_path_is_a_built_in_rule() {
    let r = RuleSet::empty().with_home_path();
    assert!(r.no_private());
    let hits = r.hits(b"in /home/ann/x");
    assert_eq!(hits.len(), 1);
    assert!(hits[0].builtin);
    assert!(r.first_private_hit("in /home/ann/x").is_none());
    assert_eq!(r.fingerprint(), "");
}

/// `TICK005` names the label and hash, never the term; no private rules means no finding.
// frob:tests crates/frob-ledger/src/redact.rs::tick005
#[test]
fn tick005_reports_label_not_term() {
    let r = rules("");
    let f = tick005("tickets/X/ticket.md", format!("x {TERM}").as_bytes(), &r);
    assert_eq!(f.len(), 1);
    assert_eq!(f[0].rule.as_str(), "TICK005");
    assert!(!format!("{:?}", f[0]).contains(TERM));
    assert!(tick005("p", TERM.as_bytes(), &RuleSet::empty().with_home_path()).is_empty());
}

/// Local rule files merge from the git common dir; the fingerprint changes with the rules.
// frob:tests crates/frob-ledger/src/redact.rs::RuleSet.load_local
#[test]
fn load_local_reads_the_common_dir_file() {
    let dir = tempfile::tempdir().expect("tmp");
    assert!(
        RuleSet::load_local(dir.path()).expect("none").no_private()
            || std::env::var_os("HOME").is_some()
    );
    std::fs::create_dir_all(dir.path().join("frob")).expect("mkdir");
    std::fs::write(
        dir.path().join("frob").join("privacy.toml"),
        format!("[[rule]]\npattern = \"{TERM}\"\nreplace = \"<h>\"\n"),
    )
    .expect("write");
    let r = RuleSet::load_local(dir.path()).expect("load");
    assert!(r.first_private_hit(TERM).is_some());
    assert!(!r.fingerprint().is_empty());
}
