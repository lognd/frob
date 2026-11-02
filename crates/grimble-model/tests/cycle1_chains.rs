//! Cycle 1 chain spellings (grmb-spec 2.2, 11.1, 14.1, 15.3): waypoint chains, `on page`,
//! actor `in node`, the `r#` escape and the whole-body `sorry`.

// frob:ticket 01M6BYK3QNNF0WHQW2Y0Q2TMVM

use grimble_model::fmt::format_file;
use grimble_model::parse::parse_file;

const H: &str = "grimble = \"2\";\nmodule m;\n";

fn clean(body: &str) {
    let src = format!("{H}{body}");
    let f = parse_file("m.grmb", src.as_bytes());
    assert!(f.diags.is_empty(), "{:?}\n{src}", f.diags);
    assert_eq!(f.holes, 0, "{src}");
}

fn printed(body: &str) -> String {
    let src = format!("{H}{body}");
    let f = parse_file("m.grmb", src.as_bytes());
    assert!(f.diags.is_empty(), "{:?}\n{src}", f.diags);
    format_file(&f).expect("formats")
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn waypoint_chains_with_outcome_maps_are_accepted() {
    clean(
        "impl a.b for s {\n  chain {\n    route r = \"POST /orders/{id}/pay\";\n    topic t = \"orders\";\n    call c = \"svc.py::f\" { E, 402 => d; _ => e; verified_by \"t.py\"; }\n  }\n}\n",
    );
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn on_page_actor_in_node_and_page_bodies_are_accepted() {
    clean("impl a.b for s {\n  on page p;\n  in node n;\n}\n");
    clean("page p {\n  entry;\n  from a, b;\n  ui x = \"f.tsx::X\";\n}\n");
    clean("actor a : human {\n  in node n;\n}\n");
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn raw_identifiers_are_plain_names_even_when_keywords() {
    clean("step r#step.go;\n");
    clean("actor r#node : human;\n");
    clean("impl a.b for s {\n  r#chain = \"x\";\n  chain { r#ui r#x = \"y\"; }\n}\n");
    clean("page r#customer;\n");
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn a_bare_keyword_is_still_not_a_name() {
    let f = parse_file("m.grmb", format!("{H}actor node : human;\n").as_bytes());
    assert!(f.diags.iter().any(|d| d.rule == "MDL000"), "{:?}", f.diags);
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn whole_body_sorry_is_accepted_on_scenario_impl_and_page() {
    clean("scenario s sorry;\n");
    clean(
        "scenario s realizes g.x sorry because=\"later\" ticket=\"T-1\" until=2027-01-01 owner=ops;\n",
    );
    clean("impl a.b for s sorry because=\"later\";\n");
    clean("page p sorry;\n");
    clean("scenario s {\n  sorry;\n}\n");
}

#[test]
// frob:tests crates/grimble-model/src/fmt.rs::format_file
fn whole_body_sorry_prints_as_a_single_line_and_is_stable() {
    for body in [
        "scenario s sorry;\n",
        "impl a.b for s sorry because = \"later\";\n",
        "page p sorry;\n",
    ] {
        let once = printed(body);
        assert!(once.ends_with(body), "{once}");
        assert_eq!(printed(&once[H.len()..]), once);
    }
    assert!(printed("scenario s {\n  sorry;\n}\n").ends_with("scenario s sorry;\n"));
}

#[test]
// frob:ticket 01M6D6ZWPQF3797CF5YCV4PB87
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn legacy_requires_page_is_mdl012_and_on_page_is_clean() {
    let legacy = parse_file(
        "m.grmb",
        format!("{H}impl a.b for s {{\n  requires page p;\n}}\n").as_bytes(),
    );
    let rules: Vec<&str> = legacy.diags.iter().map(|d| d.rule).collect();
    assert_eq!(rules, ["MDL012"], "{:?}", legacy.diags);
    clean("impl a.b for s {\n  on page p;\n}\n");
}

#[test]
// frob:ticket 01M6D6ZWPQF3797CF5YCV4PB87
// frob:tests crates/grimble-model/src/fmt/plan.rs::pclause_text
fn fmt_prints_on_page_for_both_spellings() {
    let legacy = parse_file(
        "m.grmb",
        format!("{H}impl a.b for s {{\n  requires page p;\n}}\n").as_bytes(),
    );
    let out = format_file(&legacy).expect("formats");
    assert!(
        out.contains("on page p;") && !out.contains("requires"),
        "{out}"
    );
    assert_eq!(printed("impl a.b for s {\n  on page p;\n}\n"), out);
}

#[test]
// frob:ticket 01M6D6ZWPQF3797CF5YCV4PB87
// frob:tests crates/grimble-model/src/fmt.rs::format_file
fn fmt_keeps_the_raw_escape_on_keyword_named_identifiers() {
    let out = printed(
        "actor r#node : human;\nstep r#size.go;\nimpl a.r#version for s {\n  on page r#shape;\n  in node r#node;\n}\npage r#customer;\n",
    );
    for want in [
        "actor r#node",
        "r#size.go",
        "a.r#version",
        "on page r#shape",
        "in node r#node",
        "page r#customer",
    ] {
        assert!(out.contains(want), "missing {want}\n{out}");
    }
    assert_eq!(printed(&out[H.len()..]), out, "fixed point");
}
