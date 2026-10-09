//! TW001-TW005 and TOKENS001 beyond the rule pages: the utility grammar, the messages, Unresolved
//! utilities, and the tokens drift messages.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

mod support;

use crunk_rules::rules::{
    tokens001::Tokens001, tw001::Tw001, tw002::Tw002, tw003::Tw003, tw004::Tw004, tw005::Tw005,
};
use crunk_rules::tailwind::{
    TailwindFacts, alpha_parts, arbitrary_prefix, category_split, split_family_stem, strip_alpha,
};
use crunk_rules::tokens_drift::drift_message;
use crunk_tokens::export::Status;
use gob_rules::{RepoRule, Severity};

struct Silent<'a>(&'a support::Project, &'a TailwindFacts);
impl crunk_rules::CrunkHost for Silent<'_> {
    fn spec(&self) -> Option<&crunk_spec::DesignSpec> {
        Some(&self.0.spec)
    }
    fn styles(&self) -> Option<&crunk_ingest::ProjectStyles> {
        Some(&self.0.styles)
    }
    fn tailwind(&self) -> Option<&TailwindFacts> {
        Some(self.1)
    }
}

fn tsx(classes: &str, config: Option<&str>) -> support::Project {
    support::project(
        "src/Card.tsx",
        &format!("export const Card = () => <div className=\"{classes}\" />;\n"),
        config,
    )
}

// frob:tests crates/crunk-rules/src/tailwind/mod.rs::arbitrary_prefix
#[test]
fn the_arbitrary_form_is_a_dashed_prefix_then_a_bracket() {
    assert_eq!(arbitrary_prefix("p-[13px]"), Some("p"));
    assert_eq!(arbitrary_prefix("-z-[5]"), Some("-z"));
    assert_eq!(arbitrary_prefix("min-w-[10px]"), Some("min-w"));
    assert_eq!(arbitrary_prefix("p-4"), None);
    assert_eq!(arbitrary_prefix("p-[]"), None);
    assert_eq!(arbitrary_prefix("P-[1px]"), None);
}

// frob:tests crates/crunk-rules/src/tailwind/mod.rs::alpha_parts
// frob:tests crates/crunk-rules/src/tailwind/mod.rs::strip_alpha
#[test]
fn an_alpha_modifier_is_a_trailing_slash_and_digits() {
    assert_eq!(alpha_parts("bg-x/50"), Some(("bg-x", "50")));
    assert_eq!(alpha_parts("w-1/2"), Some(("w-1", "2")));
    assert_eq!(alpha_parts("bg-x/"), None);
    assert_eq!(alpha_parts("bg-x/a"), None);
    assert_eq!(strip_alpha("bg-black/10"), "bg-black");
    assert_eq!(strip_alpha("bg-black"), "bg-black");
}

// frob:tests crates/crunk-rules/src/tailwind/mod.rs::category_split
// frob:tests crates/crunk-rules/src/tailwind/mod.rs::split_family_stem
#[test]
fn family_stems_keep_compound_prefixes_and_negation_whole() {
    assert_eq!(category_split("bg-red-500"), Some(("bg", "red-500")));
    assert_eq!(category_split("flex"), None);
    assert_eq!(
        split_family_stem("min-h-9"),
        Some(("min-h".to_owned(), "9"))
    );
    assert_eq!(split_family_stem("-z-10"), Some(("-z".to_owned(), "10")));
    assert_eq!(split_family_stem("p-4"), Some(("p".to_owned(), "4")));
    assert_eq!(split_family_stem("flex"), None);
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn tw001_messages_name_the_neighbours_the_token_and_the_layers() {
    let f = support::run::<Tw001>(&tsx("p-[13px] bg-[#123456] z-[99] max-h-[32dvh]", None));
    let messages: Vec<&str> = f.iter().map(|f| f.message.as_str()).collect();
    assert!(messages.contains(&"arbitrary value 'p-[13px]' is off the scale; between var(--space-12) and var(--space-16)"), "{messages:?}");
    assert!(
        messages.iter().any(|m| m.starts_with(
            "arbitrary value 'bg-[#123456]' is not a palette color; nearest is var(--color-"
        ) || m.contains("nearest is --color-")
            || m.contains("not a palette color")),
        "{messages:?}"
    );
    assert!(
        messages.contains(
            &"arbitrary value 'z-[99]' is z-index 99, not among declared layers [0, 100, 200, 300]"
        ),
        "{messages:?}"
    );
    assert!(
        messages
            .iter()
            .any(|m| m.contains("'max-h' is a governed scale family")),
        "{messages:?}"
    );
    assert_eq!(f[0].severity, Severity::Error);
}

// frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
#[test]
fn a_utility_tailwind_did_not_answer_for_is_unresolved_not_clean() {
    let host = tsx("p-[13px]", None);
    let silent = TailwindFacts::new(
        &host.spec,
        indexmap::IndexMap::default(),
        Vec::new(),
        Some("static mode requested".to_owned()),
    );
    let wrapped = Silent(&host, &silent);
    let emitted = gob_rules::run_repo::<Tw001, Silent<'_>>(&Tw001, &wrapped);
    assert_eq!(emitted.len(), 1);
    let mut files = gob_text::FileInterner::new();
    let finding = emitted
        .into_iter()
        .next()
        .expect("one")
        .into_located_finding(<Tw001 as gob_rules::RuleDecl>::DEF, &mut files);
    assert!(
        finding
            .message
            .contains("unresolved-by-tailwind (static mode requested)"),
        "{}",
        finding.message
    );
}

// frob:tests crates/crunk-rules/src/rules/tw002.rs::Tw002
#[test]
fn tw002_is_inapplicable_without_a_tailwind_config() {
    assert!(Tw002.inapplicable(&tsx("p-4", None)).is_some());
    assert!(
        Tw002
            .inapplicable(&tsx("p-4", Some("tw-theme-plain")))
            .is_none()
    );
    let f = support::run::<Tw002>(&tsx("p-4", Some("tw-theme-broken")));
    assert_eq!(f.len(), 1, "{f:?}");
    assert_eq!(
        f[0].message,
        "tailwind theme entry 'brand' maps to var(--color-missing) which is not an exported token"
    );
}

// frob:tests crates/crunk-rules/src/rules/tw003.rs::Tw003
#[test]
fn tw003_names_the_entry_its_mapping_and_warns() {
    let f = support::run::<Tw003>(&tsx("bg-brand/50", Some("tw-theme-plain")));
    assert_eq!(f.len(), 1, "{f:?}");
    assert_eq!(f[0].severity, Severity::Warn);
    assert!(
        f[0].message
            .contains("tw_theme entry 'brand' maps to '#2f6fed'")
    );
}

// frob:tests crates/crunk-rules/src/rules/tw004.rs::Tw004
#[test]
fn tw004_names_the_default_colour_and_the_nearest_token() {
    let f = support::run::<Tw004>(&tsx("bg-red-500", None));
    assert_eq!(f.len(), 1, "{f:?}");
    assert!(f[0].message.starts_with("utility 'bg-red-500' resolves to Tailwind's default color 'red-500' (#ef4444), not the project theme; nearest is "), "{}", f[0].message);
}

// frob:tests crates/crunk-rules/src/rules/tw005.rs::Tw005
#[test]
fn tw005_spares_a_default_key_that_lands_on_the_declared_scale() {
    let f = support::run::<Tw005>(&tsx("p-5 p-3 inset-0 z-10 text-center", None));
    let messages: Vec<&str> = f.iter().map(|f| f.message.as_str()).collect();
    assert_eq!(messages.len(), 2, "{messages:?}");
    assert!(
        messages
            .iter()
            .any(|m| m.contains("'p-5'") && m.contains("spacing scale (key '5')"))
    );
    assert!(
        messages
            .iter()
            .any(|m| m.contains("'z-10'") && m.contains("zIndex scale"))
    );
}

// frob:tests crates/crunk-rules/src/tokens_drift.rs::drift_message
#[test]
fn drift_messages_name_the_status_and_the_banner_only_case() {
    assert_eq!(
        drift_message(Status::Missing, false),
        "tokens file missing; run `crunk tokens` to regenerate"
    );
    assert_eq!(
        drift_message(Status::Drifted, false),
        "tokens file drifted; run `crunk tokens` to regenerate"
    );
    assert!(
        drift_message(Status::Drifted, true).contains("only the generated banner line differs")
    );
}

// frob:tests crates/crunk-rules/src/tokens_drift.rs::check
// frob:tests crates/crunk-rules/src/tokens_drift.rs::findings
#[test]
fn tokens001_names_the_drifted_file() {
    let host = support::project("styles/app.css", ".a { margin: 0; }\n", None);
    let f = support::run::<Tokens001>(&host);
    assert!(
        f.iter()
            .any(|f| f.message == "tokens file drifted; run `crunk tokens` to regenerate"),
        "{f:?}"
    );
    let current = support::project(
        "styles/app.css",
        ".a { margin: 0; }\n",
        Some("tokens-current"),
    );
    assert!(support::run::<Tokens001>(&current).is_empty());
}

// frob:tests crates/crunk-rules/src/tailwind/mod.rs::scale_and_token
// frob:tests crates/crunk-rules/src/tailwind/mod.rs::unresolved_message
// frob:tests crates/crunk-rules/src/tailwind/mod.rs::TailwindFacts.class
// frob:tests crates/crunk-rules/src/tailwind/mod.rs::TailwindFacts.fingerprint
#[test]
fn facts_answer_per_utility_and_fingerprint_stably() {
    let host = tsx("p-[13px]", None);
    let (scale, token) = crunk_rules::tailwind::scale_and_token(&host.spec, "rounded", 8.0);
    assert_eq!(scale, host.spec.scales.radii);
    assert_eq!(token, "--radius-8");
    assert!(matches!(
        host.tailwind.class("p-[13px]"),
        crunk_rules::tailwind::ClassState::Valid(_)
    ));
    assert!(matches!(
        host.tailwind.class("not-asked"),
        crunk_rules::tailwind::ClassState::Unresolved(_)
    ));
    assert_eq!(host.tailwind.fingerprint(), host.tailwind.fingerprint());
    assert_eq!(
        crunk_rules::tailwind::unresolved_message("x", "why"),
        "utility 'x' is unresolved-by-tailwind (why); skipped rather than guessed from its name"
    );
}
