//! LAYER001 and ORG001-005 beyond the rule pages: messages, locations, the config switches that
//! make a rule inapplicable, and the class-name judgments.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

mod support;

use crunk_rules::org::{bem_segments, carries_prefix, case_name, case_ok};
use crunk_rules::rules::{
    layer001::Layer001, org001::Org001, org002::Org002, org003::Org003, org004::Org004,
    org005::Org005,
};
use crunk_rules::sheets::line_offset;
use crunk_spec::table::ClassCase;
use gob_rules::RepoRule;

fn css(file: &str, text: &str) -> support::Project {
    support::project(file, text, None)
}

fn with_org(replacement: &str) -> String {
    support::DEFAULT_SPEC
        .replace("class_case = \"kebab\"\n", "")
        .replace("component_prefix = true\n", "")
        .replace("tokens_only_custom_props = true\n", "")
        .replace("[org]\n", &format!("[org]\n{replacement}\n"))
}

// frob:tests crates/crunk-rules/src/org/mod.rs::bem_segments
#[test]
fn bem_names_split_on_double_separators_only() {
    assert_eq!(bem_segments("card__title--big"), ["card", "title", "big"]);
    assert_eq!(bem_segments("card-title"), ["card-title"]);
    assert_eq!(bem_segments("card_title"), ["card_title"]);
    assert_eq!(bem_segments("__x"), ["x"]);
}

// frob:tests crates/crunk-rules/src/org/mod.rs::case_ok
#[test]
fn the_three_case_grammars_match_the_python_patterns() {
    assert!(case_ok("card-title", ClassCase::Kebab));
    assert!(case_ok("card__title--big-2", ClassCase::Kebab));
    assert!(!case_ok("Card", ClassCase::Kebab));
    assert!(!case_ok("card_title", ClassCase::Kebab));
    assert!(!case_ok("-card", ClassCase::Kebab));
    assert!(case_ok("card_title", ClassCase::Snake));
    assert!(!case_ok("card-title", ClassCase::Snake));
    assert!(case_ok("cardTitle", ClassCase::Camel));
    assert!(!case_ok("CardTitle", ClassCase::Camel));
    assert!(!case_ok("card-title", ClassCase::Camel));
}

// frob:tests crates/crunk-rules/src/org/mod.rs::carries_prefix
#[test]
fn a_component_class_is_the_name_or_its_element_or_modifier() {
    assert!(carries_prefix("card", "card"));
    assert!(carries_prefix("card__title", "card"));
    assert!(carries_prefix("card--wide", "card"));
    assert!(!carries_prefix("card-wide", "card"));
    assert!(!carries_prefix("cards", "card"));
    assert!(!carries_prefix("title", "card"));
}

// frob:tests crates/crunk-rules/src/rules/layer001.rs::Layer001
#[test]
fn layer001_names_the_declared_layers_and_skips_auto() {
    let found = support::run::<Layer001>(&css(
        "styles/app.css",
        ".a { z-index: 99; }\n.b { z-index: auto; }\n.c { z-index: 200; }\n",
    ));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(
        found[0].message,
        "z-index 99 is not among declared layers [0, 100, 200, 300]"
    );
}

// frob:tests crates/crunk-rules/src/rules/layer001.rs::Layer001
#[test]
fn layer001_is_inapplicable_without_layers() {
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
    assert!(
        Layer001
            .inapplicable(&host)
            .is_some_and(|why| why.contains("layers")),
        "no layers declared"
    );
}

// frob:tests crates/crunk-rules/src/rules/org001.rs::Org001
#[test]
fn org001_names_the_stray_path_and_is_silent_under_utility_first() {
    let host = css("styles/misc/stray.css", ".a { margin: 0; }\n");
    let found = support::run::<Org001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(
        found[0].message,
        "styles/misc/stray.css is outside every declared org bucket"
    );
    assert!(Org001.inapplicable(&host).is_none());
    let utility = support::project_with_spec(
        &with_org("model = \"utility-first\""),
        "styles/misc/stray.css",
        ".a { margin: 0; }\n",
    );
    assert!(Org001.inapplicable(&utility).is_some());
}

// frob:tests crates/crunk-rules/src/rules/org002.rs::Org002
#[test]
fn org002_honours_class_case_and_locates_the_line() {
    let found = support::run::<Org002>(&css(
        "styles/components/card.css",
        ".card { margin: 0; }\n.Card_Title { margin: 0; }\n",
    ));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].message, "class 'Card_Title' violates kebab case");
    let snake = support::project_with_spec(
        &with_org("class_case = \"snake\""),
        "styles/components/card.css",
        ".card_title { margin: 0; }\n.card-title { margin: 0; }\n",
    );
    let found = support::run::<Org002>(&snake);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(found[0].message, "class 'card-title' violates snake case");
}

// frob:tests crates/crunk-rules/src/rules/org003.rs::Org003
#[test]
fn org003_flags_a_foreign_class_and_respects_its_switches() {
    let host = css(
        "styles/components/card.css",
        ".card__title { margin: 0; }\n.title { margin: 0; }\n",
    );
    let found = support::run::<Org003>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(
        found[0].message,
        "class 'title' does not carry the component prefix 'card'"
    );
    let off = support::project_with_spec(
        &with_org("component_prefix = false"),
        "styles/components/card.css",
        ".title { margin: 0; }\n",
    );
    assert!(Org003.inapplicable(&off).is_some());
}

// frob:tests crates/crunk-rules/src/rules/org004.rs::Org004
#[test]
fn org004_flags_definitions_outside_tokens_only() {
    let host = css(
        "styles/components/card.css",
        ".card { --gap: 4px; margin: var(--gap); }\n",
    );
    let found = support::run::<Org004>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(
        found[0].message,
        "custom property '--gap' defined outside the tokens file"
    );
    let off = support::project_with_spec(
        &with_org("tokens_only_custom_props = false"),
        "styles/components/card.css",
        ".card { --gap: 4px; }\n",
    );
    assert!(Org004.inapplicable(&off).is_some());
}

// frob:tests crates/crunk-rules/src/rules/org005.rs::Org005
#[test]
fn org005_names_the_file_and_the_css_root() {
    let found = support::run::<Org005>(&css("legacy/old.css", ".old { margin: 0; }\n"));
    assert_eq!(found.len(), 1, "{found:?}");
    assert_eq!(
        found[0].message,
        "legacy/old.css is a CSS file outside styles (css_root); add a matching glob to [org].ignore to exempt it"
    );
    let ignored = support::project_with_spec(
        &with_org("ignore = [\"legacy/**\"]"),
        "legacy/old.css",
        ".old { margin: 0; }\n",
    );
    assert!(support::run::<Org005>(&ignored).is_empty());
}

// frob:tests crates/crunk-rules/src/org/mod.rs::case_name
#[test]
fn case_names_are_the_crunk_toml_spellings() {
    assert_eq!(case_name(ClassCase::Kebab), "kebab");
    assert_eq!(case_name(ClassCase::Snake), "snake");
    assert_eq!(case_name(ClassCase::Camel), "camel");
}

// frob:tests crates/crunk-rules/src/sheets.rs::line_offset
#[test]
fn a_line_maps_to_the_offset_it_starts_at() {
    let text = "a\nbb\nccc\n";
    assert_eq!(line_offset(text, 1), 0);
    assert_eq!(line_offset(text, 2), 2);
    assert_eq!(line_offset(text, 3), 5);
    assert_eq!(line_offset(text, 9), text.len());
}
