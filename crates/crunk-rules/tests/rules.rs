//! The rule pages of `src/rules/*.md` as an mdtest corpus, and the registry/family checks that
//! need the generated index.

// frob:ticket 01M43ATASM383KB9130JY79XVV

use crunk_rules::family::{CheckTier, FAMILIES, Gate, family, gate_severity, is_waivable};
use crunk_rules::registry::{catalog_mismatches, entries, render_markdown, unknown_families};
use crunk_rules::rules::{
    INDEX, color001::Color001, color002::Color002, contrast001::Contrast001, layer001::Layer001,
    org001::Org001, org002::Org002, org003::Org003, org004::Org004, org005::Org005,
    radius001::Radius001, size001::Size001, space001::Space001, type001::Type001, type002::Type002,
    type003::Type003, waive001::Waive001,
};
use gob_rules::{RuleDecl, Severity, run_file};
use gob_text::FileInterner;

mod support;

struct Host;
impl crunk_rules::CrunkHost for Host {}

fn runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> {
    match case.rule.as_str() {
        "WAIVE001" => waive_runner(case),
        _ => project_runner(case),
    }
}

fn project_runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> {
    // frob:tests crates/crunk-rules/src/rules/color001.rs::Color001
    // frob:tests crates/crunk-rules/src/rules/color002.rs::Color002
    // frob:tests crates/crunk-rules/src/rules/contrast001.rs::Contrast001
    // frob:tests crates/crunk-rules/src/rules/space001.rs::Space001
    // frob:tests crates/crunk-rules/src/rules/type001.rs::Type001
    // frob:tests crates/crunk-rules/src/rules/type002.rs::Type002
    // frob:tests crates/crunk-rules/src/rules/type003.rs::Type003
    // frob:tests crates/crunk-rules/src/rules/radius001.rs::Radius001
    // frob:tests crates/crunk-rules/src/rules/size001.rs::Size001
    // frob:tests crates/crunk-rules/src/rules/layer001.rs::Layer001
    // frob:tests crates/crunk-rules/src/rules/org001.rs::Org001
    // frob:tests crates/crunk-rules/src/rules/org002.rs::Org002
    // frob:tests crates/crunk-rules/src/rules/org003.rs::Org003
    // frob:tests crates/crunk-rules/src/rules/org004.rs::Org004
    // frob:tests crates/crunk-rules/src/rules/org005.rs::Org005
    let host = support::project(&case.file_name, &case.text, case.config.as_deref());
    match case.rule.as_str() {
        "COLOR001" => support::run::<Color001>(&host),
        "COLOR002" => support::run::<Color002>(&host),
        "CONTRAST001" => support::run::<Contrast001>(&host),
        "SPACE001" => support::run::<Space001>(&host),
        "TYPE001" => support::run::<Type001>(&host),
        "TYPE002" => support::run::<Type002>(&host),
        "TYPE003" => support::run::<Type003>(&host),
        "RADIUS001" => support::run::<Radius001>(&host),
        "SIZE001" => support::run::<Size001>(&host),
        "LAYER001" => support::run::<Layer001>(&host),
        "ORG001" => support::run::<Org001>(&host),
        "ORG002" => support::run::<Org002>(&host),
        "ORG003" => support::run::<Org003>(&host),
        "ORG004" => support::run::<Org004>(&host),
        "ORG005" => support::run::<Org005>(&host),
        other => unreachable!("no runner for {other}"),
    }
}

fn waive_runner(case: &gob_mdtest::Case) -> Vec<gob_rules::Finding> {
    // frob:tests crates/crunk-rules/src/rules/waive001.rs::Waive001
    let mut files = FileInterner::new();
    let file = files.intern(&case.file_name);
    run_file::<Waive001, Host>(&Waive001, &Host, &case.text)
        .into_iter()
        .map(|e| e.into_finding(Waive001::DEF, Some(file), &case.file_name))
        .collect()
}

gob_mdtest::mdtest!(dir = "src/rules", runner = runner);

// frob:tests crates/crunk-rules/src/registry.rs::entries
#[test]
fn the_registry_lists_id_family_severity_fixable_and_doc() {
    let listed = entries(&[&INDEX]);
    let ids: Vec<&str> = listed.iter().map(|e| e.id).collect();
    assert_eq!(
        ids,
        [
            "COLOR001",
            "COLOR002",
            "CONTRAST001",
            "LAYER001",
            "ORG001",
            "ORG002",
            "ORG003",
            "ORG004",
            "ORG005",
            "RADIUS001",
            "SIZE001",
            "SPACE001",
            "TYPE001",
            "TYPE002",
            "TYPE003",
            "WAIVE001"
        ]
    );
    let e = listed
        .iter()
        .find(|e| e.id == "WAIVE001")
        .expect("WAIVE001");
    assert_eq!(
        (e.id, e.slug, e.family),
        ("WAIVE001", "waiver-without-reason", "WAIVE")
    );
    assert_eq!(e.severity, Severity::Error);
    assert!(!e.fixable);
    assert_eq!(e.tiers, [CheckTier::T0]);
    assert!(
        e.summary.starts_with("Flags a `crunk:waive` comment"),
        "{}",
        e.summary
    );
}

// frob:tests crates/crunk-rules/src/registry.rs::unknown_families
#[test]
fn every_declared_family_has_a_metadata_row() {
    assert_eq!(unknown_families(&[&INDEX]), Vec::<&str>::new());
}

// frob:tests crates/crunk-rules/src/registry.rs::catalog_mismatches
#[test]
fn declared_severities_agree_with_the_spec_catalog() {
    assert!(catalog_mismatches(&[&INDEX]).is_empty());
}

// frob:tests crates/crunk-rules/src/family.rs::family
#[test]
fn family_prefixes_are_unique_and_every_catalog_prefix_has_a_row() {
    let mut seen = std::collections::BTreeSet::new();
    for f in FAMILIES {
        assert!(seen.insert(f.prefix), "duplicate family {}", f.prefix);
    }
    for row in crunk_spec::catalog::CATALOG {
        assert!(
            family(row.prefix).is_some(),
            "catalog family {} has no row",
            row.prefix
        );
    }
}

// frob:tests crates/crunk-rules/src/family.rs::gate_severity
#[test]
fn the_release_gate_raises_human_and_leaves_others_alone() {
    let human = family("HUMAN").expect("HUMAN row");
    assert_eq!(human.release_severity, Some(Severity::Error));
    let waive = waive_def();
    assert_eq!(gate_severity(waive, Gate::Check), Severity::Error);
    assert_eq!(gate_severity(waive, Gate::Release), Severity::Error);
}

// frob:tests crates/crunk-rules/src/family.rs::is_waivable
#[test]
fn only_declaration_level_families_are_waivable() {
    assert!(is_waivable("COLOR001"));
    assert!(is_waivable("SPACE001"));
    assert!(!is_waivable("ORG002"));
    assert!(!is_waivable("WAIVE001"));
    assert!(!is_waivable("NOPE001"));
}

// frob:tests crates/crunk-rules/src/registry.rs::render_markdown
#[test]
fn the_registry_page_names_every_rule_and_family() {
    let page = render_markdown(&[&INDEX]);
    assert!(
        page.contains("| COLOR001 | color-off-palette | COLOR | error | error | no | T0, T2 |")
    );
    assert!(
        page.contains("| WAIVE001 | waiver-without-reason | WAIVE | error | error | no | T0 |")
    );
    assert!(page.contains("| HUMAN | T0 | no | error |"));
}

fn waive_def() -> &'static gob_rules::RuleDef {
    INDEX
        .metas
        .iter()
        .copied()
        .find(|d| d.id == "WAIVE001")
        .expect("WAIVE001 is declared")
}

fn spec_with(lint: &str) -> crunk_spec::DesignSpec {
    let text = crunk_spec::presets::preset("default")
        .expect("default preset")
        .replace("[lint]", &format!("[lint]\n{lint}"));
    crunk_spec::parse_spec(
        &text,
        std::path::Path::new("crunk.toml"),
        std::path::Path::new("."),
    )
    .expect("spec")
}

// frob:tests crates/crunk-rules/src/lint.rs::severity_of
#[test]
fn lint_levels_map_onto_pipeline_severities() {
    let waive = waive_def();
    assert_eq!(
        crunk_rules::lint::severity_of(&spec_with(""), waive),
        Some(Severity::Error)
    );
    assert_eq!(
        crunk_rules::lint::severity_of(&spec_with("WAIVE001 = \"warn\""), waive),
        Some(Severity::Warn)
    );
    assert_eq!(
        crunk_rules::lint::severity_of(&spec_with("WAIVE001 = \"off\""), waive),
        None
    );
}

// frob:tests crates/crunk-rules/src/rules/mod.rs::bind
#[test]
fn bind_yields_one_bound_rule_per_declaration() {
    let bound = crunk_rules::rules::bind::<dyn crunk_rules::CrunkHost>();
    let ids: Vec<&str> = bound.iter().map(|b| b.def.id).collect();
    assert_eq!(ids.len(), 16);
    assert!(ids.contains(&"SPACE001"));
}
