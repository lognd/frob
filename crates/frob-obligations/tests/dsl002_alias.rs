//! DSL002 over v1 ticket aliases: `--fix` rewrites each alias the ledger resolves to the ticket's ULID.
// frob:ticket 01M4FG41QM8F4BG9CTMJSMN4BH

mod common;

use frob_ledger::Ledger;
use frob_ledger::model::TicketType;
use frob_ledger::ops::NewTicket;
use frob_obligations::{Evaluation, InvariantsConfig};

/// File a ticket carrying the v1 `aliases`; returns its full ULID.
fn ticket(ledger: &Ledger, title: &str, aliases: &[&str]) -> String {
    let mut req = NewTicket::new(title, TicketType::Task);
    req.aliases = aliases.iter().map(|a| (*a).to_owned()).collect();
    ledger
        .new_ticket(req)
        .expect("ticket")
        .ticket
        .front
        .id
        .to_string()
}

/// Evaluate a one-file tree holding `text` against `ledger`.
fn evaluate(text: &str, ledger: &Ledger) -> Evaluation {
    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), &[("src/a.rs", text)]);
    let config = InvariantsConfig::load(dir.path()).expect("config");
    common::evaluate_tree(dir.path(), Some(ledger), &config, None)
}

/// Apply every DSL002 fix of `ev` to `text`, last edit first so offsets stay valid.
fn apply_fixes(ev: &Evaluation, text: &str) -> String {
    let mut edits: Vec<_> = ev
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "DSL002")
        .filter_map(|f| f.fix.as_ref())
        .flat_map(|x| x.edits.iter())
        .collect();
    edits.sort_by_key(|e| std::cmp::Reverse(u32::from(e.range.start())));
    let mut out = text.to_owned();
    for e in edits {
        out.replace_range(
            u32::from(e.range.start()) as usize..u32::from(e.range.end()) as usize,
            &e.replacement,
        );
    }
    out
}

fn count(ev: &Evaluation, rule: &str) -> usize {
    ev.findings
        .iter()
        .filter(|f| f.rule.as_str() == rule)
        .count()
}

// frob:tests crates/frob-obligations/src/refs.rs::dsl002_aliases
#[test]
fn fix_rewrites_resolving_aliases_and_leaves_the_rest_as_findings() {
    let t = common::tickets();
    let nine = ticket(&t.ledger, "Nine", &["T-0009"]);
    let thirty_eight = ticket(&t.ledger, "Thirty-eight", &["T-0038"]);
    let text = concat!(
        "// frob:ticket T-0009\nfn a() {}\n\n",
        "// frob:todo T-0038 note=\"later   please\"\nfn b() {}\n\n",
        "// frob:ticket T-7777\nfn c() {}\n\n",
        "const S: &str = \"// frob:ticket T-0009\";\n",
    );
    let ev = evaluate(text, &t.ledger);
    assert_eq!(
        count(&ev, "DSL002"),
        2,
        "the ticket alias and the todo alias"
    );
    assert_eq!(count(&ev, "REF001"), 1, "the unknown alias stays a finding");

    let fixed = apply_fixes(&ev, text);
    assert!(
        fixed.contains(&format!("// frob:ticket {nine}\n")),
        "{fixed}"
    );
    assert!(
        fixed.contains(&format!(
            "// frob:todo {thirty_eight} note=\"later   please\"\n"
        )),
        "{fixed}"
    );
    assert!(fixed.contains("// frob:ticket T-7777\n"), "{fixed}");
    assert!(
        fixed.contains("\"// frob:ticket T-0009\""),
        "string untouched"
    );

    let again = evaluate(&fixed, &t.ledger);
    assert_eq!(count(&again, "DSL002"), 0, "fix is idempotent");
    assert_eq!(count(&again, "REF001"), 1);
    assert_eq!(apply_fixes(&again, &fixed), fixed);
}

// frob:tests crates/frob-obligations/src/refs.rs::dsl002_aliases
#[test]
fn an_ambiguous_alias_is_reported_without_a_fix_and_no_ledger_decides_nothing() {
    let t = common::tickets();
    ticket(&t.ledger, "First", &["T-0500"]);
    ticket(&t.ledger, "Second", &["T-0500"]);
    let text = "// frob:ticket T-0500\nfn a() {}\n";
    let ev = evaluate(text, &t.ledger);
    let dsl: Vec<_> = ev
        .findings
        .iter()
        .filter(|f| f.rule.as_str() == "DSL002")
        .collect();
    assert_eq!(dsl.len(), 1);
    assert!(dsl[0].fix.is_none());

    let dir = tempfile::tempdir().expect("tempdir");
    common::write_tree(dir.path(), &[("src/a.rs", text)]);
    let config = InvariantsConfig::load(dir.path()).expect("config");
    let bare = common::evaluate_tree(dir.path(), None, &config, None);
    assert_eq!(count(&bare, "DSL002"), 0);
}
