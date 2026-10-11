//! One parse per source: a `where` that starts a line is a clause, and `any { }` items that end
//! in `reaches ... via` are separate items (grl-spec.md section 5).

// frob:ticket 01M48TKSG9SCKND40YXK0FVJFM

use gob_plan::grl::ast::{ClauseKind, CondKind, File, RelKind};
use gob_plan::grl::{parse, print};
use gob_text::FileInterner;

fn parse_ok(body: &str) -> File {
    let src = format!(
        "rule T001 \"t\" {{\n  lang *\n  {body}\n  explain \"\"\"\n    Why.\n    ## Remedy\n    Fix.\n  \"\"\"\n}}\n"
    );
    let p = parse(FileInterner::new().intern("rules/T.grl"), &src);
    assert!(p.is_ok(), "{:?}\n{src}", p.errors);
    p.file
}

// frob:tests crates/gob-plan/src/grl/parse/cond.rs::binding
#[test]
fn a_where_on_its_own_line_is_a_clause_and_one_on_the_binding_line_is_its_filter() {
    let f = parse_ok("find f: function\n  where f.public\n  report f \"x\"");
    let clauses = &f.rules[0].clauses;
    assert!(matches!(&clauses[0].node, ClauseKind::Find(b) if b.filter.is_none()));
    assert!(matches!(clauses[1].node, ClauseKind::Where(_)));

    let f = parse_ok("find f: function where f.public\n  report f \"x\"");
    assert!(matches!(&f.rules[0].clauses[0].node, ClauseKind::Find(b) if b.filter.is_some()));

    let f = parse_ok("find f: function where no t: test\n  where f.public\n  report f \"x\"");
    let c = &f.rules[0].clauses;
    assert_eq!(
        c.len(),
        3,
        "the second where is a clause, not no t's filter"
    );
    assert!(matches!(&c[0].node, ClauseKind::Find(b)
        if matches!(&b.filter, Some(x) if matches!(&x.node, CondKind::Quant { binding, .. } if binding.filter.is_none()))));
}

// frob:tests crates/gob-plan/src/grl/parse/cond.rs::via_list
#[test]
fn reaches_via_inside_any_parses_each_item_separately() {
    let f = parse_ok(
        "find f: function\n  where any { f reaches g via calls, f reaches h via (calls, imports) within 3 }\n  report f \"x\"",
    );
    let ClauseKind::Where(c) = &f.rules[0].clauses[1].node else {
        panic!("a where clause");
    };
    let CondKind::Any(items) = &c.node else {
        panic!("an any");
    };
    assert_eq!(items.len(), 2);
    let verbs: Vec<usize> = items
        .iter()
        .map(|i| match &i.node {
            CondKind::Rel { rel, .. } => match &rel.node {
                RelKind::Reaches { via, .. } => via.len(),
                _ => 0,
            },
            _ => 0,
        })
        .collect();
    assert_eq!(verbs, [1, 2]);
}

// frob:tests crates/gob-plan/src/grl/print.rs::print
#[test]
fn a_parenthesised_via_list_round_trips_in_every_position() {
    let src = "find f: function\n  where any { f reaches g via (calls, imports), f reaches h via calls }\n  where f reaches g via (calls, imports) within 2\n  report f \"x\"";
    let f = parse_ok(src);
    let printed = print(&f);
    assert!(printed.contains("via (calls, imports),"), "{printed}");
    let again = parse(FileInterner::new().intern("rules/T.grl"), &printed);
    assert!(again.is_ok(), "{printed}");
    assert_eq!(print(&again.file), printed);
}
