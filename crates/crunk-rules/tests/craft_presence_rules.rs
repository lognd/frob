//! The CRAFT presence rules (001, 002, 003, 004, 005, 007, 009, 011, 012) beyond their pages:
//! each fires on a project lacking the presence it checks, stays quiet on one that has it, and
//! survives empty files, keywords hidden in comments and strings, and a project with no UI.

// frob:ticket 01M5HM3WE0PDTYAJ31B2C2A8A0

mod support;

use crunk_rules::rules::INDEX;
use crunk_rules::rules::craft001::Craft001;
use crunk_rules::rules::craft002::Craft002;
use crunk_rules::rules::craft003::Craft003;
use crunk_rules::rules::craft004::Craft004;
use crunk_rules::rules::craft005::Craft005;
use crunk_rules::rules::craft007::Craft007;
use crunk_rules::rules::craft009::Craft009;
use crunk_rules::rules::craft011::Craft011;
use crunk_rules::rules::craft012::Craft012;
use gob_rules::{RepoRule, RuleDecl, Severity};

const CSS: &str = "styles/app.css";
const SCENE: &str = "design/scenes/home.scene.html";
const COMPONENT: &str = "design/components/button.component.toml";

/// The messages `R` reports on a project holding `file` with `text`.
fn run<R: RepoRule<support::Project> + Default>(
    file: &str,
    text: &str,
    config: Option<&str>,
) -> Vec<String> {
    let host = support::project(file, text, config);
    support::run::<R>(&host)
        .into_iter()
        .map(|f| f.message)
        .collect()
}

fn component(states: &[&str]) -> String {
    let mut text = "name = \"button\"\n".to_owned();
    for id in states {
        text.push_str("\n[[states]]\nid = \"");
        text.push_str(id);
        text.push_str("\"\n");
    }
    text
}

const ALL_STATES: [&str; 7] = [
    "hover", "active", "disabled", "focus", "loading", "error", "empty",
];

// frob:tests crates/crunk-rules/src/rules/craft001.rs::Craft001
// frob:tests crates/crunk-rules/src/rules/craft005.rs::Craft005
#[test]
fn focus_and_press_fire_when_the_ui_never_styles_them() {
    let css = ".btn { color: #111111; }\n/* :focus-visible :active */\n.x::after { content: \":active\"; }\n";
    let focus = run::<Craft001>(CSS, css, None);
    let press = run::<Craft005>(CSS, css, None);
    assert_eq!(focus.len(), 1, "{focus:?}");
    assert_eq!(press.len(), 1, "{press:?}");
    let host = support::project(CSS, css, None);
    assert_eq!(
        support::run::<Craft001>(&host)[0].severity,
        Severity::Advisory
    );
}

// frob:tests crates/crunk-rules/src/craft.rs::state_styled
// frob:tests crates/crunk-rules/src/craft.rs::ui_sheets
// frob:tests crates/crunk-rules/src/rules/craft001.rs::Craft001
// frob:tests crates/crunk-rules/src/rules/craft005.rs::Craft005
#[test]
fn focus_and_press_are_quiet_when_styled_or_when_there_is_no_ui() {
    let styled = ".btn { color: red; }\n.btn:focus-visible { outline: 2px solid red; }\n.btn:active { transform: scale(0.9); }\n";
    assert!(run::<Craft001>(CSS, styled, None).is_empty());
    assert!(run::<Craft005>(CSS, styled, None).is_empty());
    let applied = ".btn { @apply focus-visible:ring active:scale-95; }\n";
    assert!(run::<Craft001>(CSS, applied, None).is_empty());
    assert!(run::<Craft005>(CSS, applied, None).is_empty());
    for empty in ["", ":root { --ink: #111111; }\n"] {
        assert!(run::<Craft001>(CSS, empty, None).is_empty());
        assert!(run::<Craft005>(CSS, empty, None).is_empty());
    }
    let empty_rule = ".btn { color: red; }\n.btn:active { }\n";
    assert_eq!(run::<Craft005>(CSS, empty_rule, None).len(), 1);
    let lookalike = ".btn { color: red; }\n.is-active { color: blue; }\n";
    assert_eq!(run::<Craft005>(CSS, lookalike, None).len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/craft002.rs::Craft002
#[test]
fn components_fire_per_missing_state_and_are_quiet_when_complete() {
    let found = run::<Craft002>(COMPONENT, &component(&["hover"]), None);
    assert_eq!(found.len(), 1, "{found:?}");
    for missing in ["active", "disabled", "focus", "loading", "error", "empty"] {
        assert!(found[0].contains(missing), "{missing}: {}", found[0]);
    }
    assert!(!found[0].contains("hover,"), "{}", found[0]);
    assert!(run::<Craft002>(COMPONENT, &component(&ALL_STATES), None).is_empty());
    let aliased = component(&[
        "hover",
        "pressed",
        "disabled",
        "focus-visible",
        "loading",
        "invalid",
        "empty",
    ]);
    assert!(run::<Craft002>(COMPONENT, &aliased, None).is_empty());
    assert_eq!(run::<Craft002>(COMPONENT, &component(&[]), None).len(), 1);
}

// frob:tests crates/crunk-rules/src/rules/craft003.rs::Craft003
#[test]
fn scenes_fire_on_two_moments_or_a_long_scene_with_none() {
    let two = "<div data-id=\"a\" data-moment></div>\n<div data-id=\"b\" data-moment></div>\n";
    assert_eq!(run::<Craft003>(SCENE, two, None).len(), 1);
    let one =
        "<div data-id=\"a\" data-moment></div>\n<div data-id=\"b\" data-moment=\"false\"></div>\n";
    assert!(run::<Craft003>(SCENE, one, None).is_empty());
    let long = "<div data-id=\"e\"></div>
"
    .repeat(30);
    assert_eq!(run::<Craft003>(SCENE, &long, None).len(), 1);
    let marked = format!("{long}<div data-id=\"m\" data-moment></div>\n");
    assert!(run::<Craft003>(SCENE, &marked, None).is_empty());
    assert!(run::<Craft003>(SCENE, "<div data-id=\"a\"></div>\n", None).is_empty());
    assert!(run::<Craft003>(SCENE, "", None).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/craft004.rs::Craft004
#[test]
fn fonts_fire_without_a_complete_face_and_are_quiet_for_system_stacks() {
    let bare = "body { font-family: \"Inter\", sans-serif; }\n";
    assert_eq!(run::<Craft004>(CSS, bare, None).len(), 1);
    let partial = "@font-face { font-family: \"Inter\"; src: url(a.woff2); }\nbody { font-family: \"Inter\"; }\n";
    assert!(!run::<Craft004>(CSS, partial, None).is_empty());
    let full = "@font-face { font-family: \"Inter\"; src: url(a.woff2); font-display: swap; unicode-range: U+0000-00FF; size-adjust: 100%; }\nbody { font-family: \"Inter\"; }\n";
    assert!(run::<Craft004>(CSS, full, None).is_empty());
    for quiet in [
        "body { font-family: system-ui, sans-serif; }\n",
        "body { font-family: var(--font-body); }\n",
        "/* font-family: Inter */\n.a { content: \"font-family: Inter\"; }\n",
        "",
    ] {
        assert!(run::<Craft004>(CSS, quiet, None).is_empty(), "{quiet}");
    }
}

// frob:tests crates/crunk-rules/src/rules/craft007.rs::Craft007
#[test]
fn shadows_fire_when_lit_from_another_side_and_are_quiet_when_alike() {
    let off = ".a { box-shadow: 0 4px 8px #00000033; }\n.b { box-shadow: 0 -4px 8px #00000033; }\n";
    assert_eq!(run::<Craft007>(CSS, off, None).len(), 1);
    let alike =
        ".a { box-shadow: 0 2px 4px #00000033; }\n.b { box-shadow: 0 8px 16px #00000033; }\n";
    assert!(run::<Craft007>(CSS, alike, None).is_empty());
    let skipped = ".a { box-shadow: 0 4px 8px #00000033; }\n.b { box-shadow: inset 0 -4px 8px #000; }\n.c { box-shadow: 0 0 12px #fff; }\n";
    assert!(run::<Craft007>(CSS, skipped, None).is_empty());
    assert!(run::<Craft007>(CSS, ".a { box-shadow: 0 -4px 8px #000; }\n", None).is_empty());
    assert!(run::<Craft007>(CSS, "", None).is_empty());
}

// frob:tests crates/crunk-rules/src/craft.rs::has_word
// frob:tests crates/crunk-rules/src/rules/craft009.rs::Craft009
#[test]
fn content_fires_on_stand_ins_and_bare_images_and_is_quiet_when_real() {
    let bare = "<img data-id=\"hero\" src=\"hero.png\">\n";
    assert_eq!(run::<Craft009>(SCENE, bare, None).len(), 2);
    let real =
        "<img data-id=\"hero\" src=\"h.png\" alt=\"A team\" data-provenance=\"studio shoot\">\n";
    assert!(run::<Craft009>(SCENE, real, None).is_empty());
    let blank = "<img data-id=\"hero\" src=\"h.png\" alt=\"\" data-provenance=\" \">\n";
    assert_eq!(run::<Craft009>(SCENE, blank, None).len(), 1);
    let empty_key = "<h1 data-id=\"h\" data-copy=\"\">Hi</h1>\n";
    assert_eq!(run::<Craft009>(SCENE, empty_key, None).len(), 1);
    let scene = "<h1 data-id=\"h\" data-copy=\"home.hero\">Hi</h1>\n";
    let placeholder = run::<Craft009>(SCENE, scene, Some("content-placeholder"));
    assert_eq!(placeholder.len(), 1, "{placeholder:?}");
    assert!(run::<Craft009>(SCENE, scene, Some("content-en")).is_empty());
    assert!(run::<Craft009>(SCENE, "", None).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/craft011.rs::Craft011
#[test]
fn rows_fire_when_flex_has_no_alignment_and_are_quiet_otherwise() {
    let row = |attrs: &str| {
        format!(
            "<div data-id=\"r\" {attrs}><svg data-id=\"i\"></svg><span data-id=\"l\">Save</span></div>\n"
        )
    };
    assert_eq!(
        run::<Craft011>(SCENE, &row("style=\"display: flex\""), None).len(),
        1
    );
    assert_eq!(
        run::<Craft011>(SCENE, &row("class=\"inline-flex gap-2\""), None).len(),
        1
    );
    assert!(
        run::<Craft011>(
            SCENE,
            &row("style=\"display:flex;align-items:center\""),
            None
        )
        .is_empty()
    );
    assert!(run::<Craft011>(SCENE, &row("class=\"flex items-center\""), None).is_empty());
    assert!(run::<Craft011>(SCENE, &row("class=\"stack\""), None).is_empty());
    let no_label = "<div data-id=\"r\" style=\"display:flex\"><svg data-id=\"i\"></svg></div>\n";
    assert!(run::<Craft011>(SCENE, no_label, None).is_empty());
    assert!(run::<Craft011>(SCENE, "", None).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/craft012.rs::Craft012
#[test]
fn coverage_fires_on_mostly_literal_styling_and_is_quiet_on_tokens() {
    let literal = ".c { color: #111111; }
"
    .repeat(12);
    let found = run::<Craft012>(CSS, &literal, None);
    assert_eq!(found.len(), 1, "{found:?}");
    assert!(found[0].contains("0 percent"), "{}", found[0]);
    let tokens = ".c { color: var(--ink); }
"
    .repeat(12);
    let covered = format!(":root {{ --ink: #111111; }}\n{tokens}");
    assert!(run::<Craft012>(CSS, &covered, None).is_empty());
    let undefined = run::<Craft012>(CSS, &tokens, None);
    assert!(
        undefined.is_empty(),
        "undefined vars are neither literal nor token: {undefined:?}"
    );
    let few = ".a { color: #111111; }\n.b { color: #222222; }\n";
    assert!(run::<Craft012>(CSS, few, None).is_empty());
    assert!(run::<Craft012>(CSS, "", None).is_empty());
}

// frob:tests crates/crunk-rules/src/rules/mod.rs::INDEX
#[test]
fn every_rule_has_a_registry_entry_and_a_documentation_page() {
    let defs = [
        <Craft001 as RuleDecl>::DEF,
        <Craft002 as RuleDecl>::DEF,
        <Craft003 as RuleDecl>::DEF,
        <Craft004 as RuleDecl>::DEF,
        <Craft005 as RuleDecl>::DEF,
        <Craft007 as RuleDecl>::DEF,
        <Craft009 as RuleDecl>::DEF,
        <Craft011 as RuleDecl>::DEF,
        <Craft012 as RuleDecl>::DEF,
    ];
    for def in defs {
        assert!(
            INDEX.metas.iter().any(|d| d.id == def.id),
            "{} not in INDEX",
            def.id
        );
        assert!(def.doc.contains(def.id), "{} has no page", def.id);
    }
}

// frob:tests crates/crunk-rules/src/rules/craft001.rs::Craft001
// frob:tests crates/crunk-rules/src/rules/craft003.rs::Craft003
#[test]
fn rules_report_inapplicable_inputs_by_name() {
    let host = support::project(CSS, ".a { color: red; }\n", None);
    assert_eq!(
        RepoRule::<support::Project>::inapplicable(&Craft001, &host),
        None
    );
    let reason = RepoRule::<support::Project>::inapplicable(&Craft003, &host);
    assert!(reason.is_some_and(|r| r.contains("scene")));
}
