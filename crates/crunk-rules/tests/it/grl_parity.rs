//! Parity of the GRL-generated LAYER001 and ORG002 (`packs/crunk-core/generated`) with the
//! hand-written Rust rules, on the fixtures of `org_rules.rs`: same files, same lines. The one
//! divergence (`_` separators in LAYER001) is pinned by its own test.

// frob:ticket 01M71T80ZZPW5Z00CKF3ANQ2X3

use crate::support;

use crunk_rules::grl_rules::{GrlOutcome, run_layer001, run_org002};
use crunk_rules::rules::{layer001::Layer001, org002::Org002};
use gob_rules::{Emitted, RepoRule, run_repo};

/// `(path, line)` of each finding of `R` over `host`, the line read off the one source `text`.
fn rust_lines<R: RepoRule<support::Project> + Default>(
    host: &support::Project,
    text: &str,
) -> Vec<(String, u32)> {
    let emitted: Vec<Emitted> = run_repo::<R, support::Project>(&R::default(), host);
    let mut found: Vec<(String, u32)> = emitted
        .into_iter()
        .map(|e| {
            let at = e.offset.unwrap_or(0).min(text.len());
            let line = 1 + u32::try_from(text[..at].matches('\n').count()).unwrap();
            (e.path.unwrap_or_default(), line)
        })
        .collect();
    found.sort();
    found
}

/// `(path, line)` of each finding of a GRL outcome.
fn grl_lines(outcome: GrlOutcome) -> Vec<(String, u32)> {
    let GrlOutcome::Findings(found) = outcome else {
        panic!("rule was inapplicable: {outcome:?}");
    };
    let mut lines: Vec<(String, u32)> = found.into_iter().map(|f| (f.path, f.line)).collect();
    lines.sort();
    lines
}

fn with_org(replacement: &str) -> String {
    support::DEFAULT_SPEC
        .replace("class_case = \"kebab\"\n", "")
        .replace("component_prefix = true\n", "")
        .replace("tokens_only_custom_props = true\n", "")
        .replace("[org]\n", &format!("[org]\n{replacement}\n"))
}

fn layer_parity(text: &str) -> Vec<(String, u32)> {
    let host = support::project("styles/app.css", text, None);
    let grl = grl_lines(run_layer001(&host).expect("GRL LAYER001 runs"));
    assert_eq!(grl, rust_lines::<Layer001>(&host, text), "{text}");
    grl
}

// frob:tests crates/crunk-rules/src/grl_rules.rs::run_layer001
#[test]
fn grl_layer001_matches_rust_and_skips_auto() {
    let found = layer_parity(".a { z-index: 99; }\n.b { z-index: auto; }\n.c { z-index: 200; }\n");
    assert_eq!(found, [("styles/app.css".to_owned(), 1)]);
}

// frob:tests crates/crunk-rules/src/grl_rules.rs::run_layer001
#[test]
fn grl_layer001_underscore_integers_diverge_from_rust() {
    // KNOWN GAP (blocks retiring the Rust LAYER001): the GRL predicate `is integer` parses with
    // Rust `i64::from_str`, so `1_0` is not an integer there; the Rust rule reads `_` separators
    // like Python and fires. This test pins the divergence until the predicate learns `_`.
    let text = ".a { z-index: 1_0; }\n.b { z-index: 1_00; }\n";
    let host = support::project("styles/app.css", text, None);
    let grl = grl_lines(run_layer001(&host).expect("GRL LAYER001 runs"));
    assert!(grl.is_empty(), "{grl:?}");
    assert_eq!(
        rust_lines::<Layer001>(&host, text),
        [("styles/app.css".to_owned(), 1)]
    );
}

// frob:tests crates/crunk-rules/src/grl_rules.rs::run_layer001
#[test]
fn grl_layer001_is_inapplicable_without_layers() {
    let no_layers = support::DEFAULT_SPEC
        .lines()
        .filter(|l| {
            !l.starts_with("base = ")
                && !l.starts_with("dropdown")
                && !l.starts_with("overlay")
                && !l.starts_with("toast")
                && *l != "[layers]"
        })
        .collect::<Vec<_>>()
        .join("\n");
    let host = support::project_with_spec(&no_layers, "styles/a.css", ".a { z-index: 99; }\n");
    assert!(Layer001.inapplicable(&host).is_some());
    assert!(matches!(
        run_layer001(&host),
        Ok(GrlOutcome::Inapplicable(why)) if why.contains("layers")
    ));
}

// frob:tests crates/crunk-rules/src/grl_rules.rs::run_org002
// frob:tests crates/gob-plan/src/exec/message.rs::render_message
#[test]
fn grl_org002_matches_rust_and_locates_the_line() {
    let text = ".card { margin: 0; }\n.Card_Title { margin: 0; }\n";
    let host = support::project("styles/components/card.css", text, None);
    let outcome = run_org002(&host).expect("GRL ORG002 runs");
    let GrlOutcome::Findings(found) = &outcome else {
        panic!("{outcome:?}");
    };
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].line, 2);
    assert_eq!(
        found[0].message,
        "class 'Card_Title' violates the configured [org] class_case"
    );
    assert_eq!(grl_lines(outcome), rust_lines::<Org002>(&host, text));
}

// frob:tests crates/crunk-rules/src/grl_rules.rs::run_org002
#[test]
fn grl_org002_honours_snake_case() {
    let text = ".card_title { margin: 0; }\n.card-title { margin: 0; }\n";
    let host = support::project_with_spec(
        &with_org("class_case = \"snake\""),
        "styles/components/card.css",
        text,
    );
    let grl = grl_lines(run_org002(&host).expect("GRL ORG002 runs"));
    assert_eq!(grl, [("styles/components/card.css".to_owned(), 2)]);
    assert_eq!(grl, rust_lines::<Org002>(&host, text));
}

// frob:tests crates/crunk-rules/src/grl_rules.rs::run_org002
#[test]
fn grl_org002_ignores_model_and_org_ignore() {
    let text = ".Card_Title { margin: 0; }\n";
    let host = support::project_with_spec(
        &with_org("model = \"utility-first\"\nignore = [\"styles/**\"]"),
        "styles/components/card.css",
        text,
    );
    let grl = grl_lines(run_org002(&host).expect("GRL ORG002 runs"));
    assert_eq!(grl.len(), 1);
    assert_eq!(grl, rust_lines::<Org002>(&host, text));
}
