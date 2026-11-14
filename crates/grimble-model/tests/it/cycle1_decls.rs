//! Cycle 1 declaration spellings (grmb-spec 3.2, 4, 11.5, 12.5): the accept side only.

// frob:ticket 01M6BYK3M8ZM6K3P9V3M7Y61ZQ

use grimble_model::parse::parse_file;

const H: &str = "grimble = \"2\";\nmodule m;\n";

fn clean(body: &str) {
    let src = format!("{H}{body}");
    let f = parse_file("m.grmb", src.as_bytes());
    assert!(f.diags.is_empty(), "{:?}\n{src}", f.diags);
    assert_eq!(f.holes, 0, "{src}");
}

/// Parses a bridged (pre-cycle-1) spelling: no holes, and exactly `n` MDL012 diagnostics.
fn bridged(body: &str, n: usize) {
    let src = format!("{H}{body}");
    let f = parse_file("m.grmb", src.as_bytes());
    assert_eq!(f.holes, 0, "{src}");
    let mdl012 = f.diags.iter().filter(|d| d.rule == "MDL012").count();
    assert_eq!(mdl012, n, "{:?}\n{src}", f.diags);
    assert_eq!(f.diags.len(), n, "{:?}\n{src}", f.diags);
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn use_item_is_accepted_with_mount_and_outside() {
    clean("use \"a.grmb\";\nuse \"b.grmb\" as lib outside;\n");
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn verified_by_is_accepted_on_a_node_selector_and_manual() {
    clean("node n : trusted {\n  verified_by \"tests/t.rs\";\n}\n");
    clean("node n : trusted {\n  verified_by manual because=\"audited\";\n}\n");
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn verified_by_manual_is_accepted_on_actor_and_step() {
    clean(
        "actor a : person {\n  verified_by manual because=\"x\";\n}\nstep a.go : { ok } {\n  verified_by manual because=\"y\";\n}\n",
    );
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn step_colon_outcome_open_and_idempotent_are_accepted() {
    clean("step system.a : open { ok, e } idempotent;\n");
    clean("step system.b : closed { ok(P), e };\n");
    clean("step system.c : { ok } idempotent idempotent;\n");
    bridged("step system.d -> { ok };\n", 1);
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn arm_fat_arrow_and_bridged_arrow_are_accepted() {
    clean("scenario s {\n  system.a => {\n    ok => end ok;\n    e => end err(e);\n  }\n}\n");
    bridged(
        "scenario s {\n  system.a => {\n    ok => end ok;\n    e -> end err(e);\n  }\n}\n",
        1,
    );
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn retry_forms_are_accepted() {
    clean(
        "scenario s {\n  system.a => {\n    ok => end ok;\n    e => retry max 3 within 30 s;\n  }\n}\n",
    );
    clean(
        "scenario s {\n  system.a => {\n    ok => end ok;\n    e => retry system.a max 3 within 30 s else end err(e);\n  }\n}\n",
    );
    clean("scenario s {\n  system.a => {\n    ok => end ok;\n    e => retry;\n  }\n}\n");
}

#[test]
// frob:tests crates/grimble-model/src/parse.rs::parse_file
fn bare_retry_with_no_matched_element_is_a_hole() {
    let src = format!("{H}scenario s {{\n  retry max 3;\n}}\n");
    let f = parse_file("m.grmb", src.as_bytes());
    assert!(!f.diags.is_empty());
}
