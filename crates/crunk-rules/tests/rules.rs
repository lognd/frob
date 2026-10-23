//! The rule pages of `src/rules/*.md` as an mdtest corpus, and the registry/family checks that
//! need the generated index.

// frob:ticket 01M43ATASM383KB9130JY79XVV

use crunk_rules::family::{CheckTier, FAMILIES, Gate, family, gate_severity, is_waivable};
use crunk_rules::registry::{catalog_mismatches, entries, render_markdown, unknown_families};
use crunk_rules::rules::{
    INDEX, bp001::Bp001, bp002::Bp002, bp003::Bp003, color001::Color001, color002::Color002,
    comp001::Comp001, comp002::Comp002, comp003::Comp003, comp004::Comp004, comp005::Comp005,
    comp006::Comp006, comp007::Comp007, comp008::Comp008, comp009::Comp009, content001::Content001,
    content002::Content002, content003::Content003, contrast001::Contrast001, craft006::Craft006,
    craft008::Craft008, craft010::Craft010, craft013::Craft013, export001::Export001,
    export002::Export002, gx001::Gx001, gx002::Gx002, gx003::Gx003, gx004::Gx004, gx005::Gx005,
    human001::Human001, human002::Human002, layer001::Layer001, layout001::Layout001,
    layout002::Layout002, layout003::Layout003, layout004::Layout004, layout005::Layout005,
    org001::Org001, org002::Org002, org003::Org003, org004::Org004, org005::Org005,
    radius001::Radius001, resp001::Resp001, scene001::Scene001, scene002::Scene002,
    scene003::Scene003, scene004::Scene004, size001::Size001, slop001::Slop001, slop003::Slop003,
    slop004::Slop004, slop010::Slop010, slop011::Slop011, slop014::Slop014, slop022::Slop022,
    slop040::Slop040, slop060::Slop060, space001::Space001, state001::State001, state002::State002,
    state003::State003, state006::State006, state007::State007, token002::Token002,
    token003::Token003, token004::Token004, token005::Token005, token006::Token006,
    token007::Token007, token008::Token008, token009::Token009, tokens001::Tokens001, tw001::Tw001,
    tw002::Tw002, tw003::Tw003, tw004::Tw004, tw005::Tw005, type001::Type001, type002::Type002,
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
    // frob:tests crates/crunk-rules/src/rules/comp001.rs::Comp001
    // frob:tests crates/crunk-rules/src/rules/comp002.rs::Comp002
    // frob:tests crates/crunk-rules/src/rules/comp003.rs::Comp003
    // frob:tests crates/crunk-rules/src/rules/comp004.rs::Comp004
    // frob:tests crates/crunk-rules/src/rules/comp005.rs::Comp005
    // frob:tests crates/crunk-rules/src/rules/comp006.rs::Comp006
    // frob:tests crates/crunk-rules/src/rules/comp007.rs::Comp007
    // frob:tests crates/crunk-rules/src/rules/comp008.rs::Comp008
    // frob:tests crates/crunk-rules/src/rules/comp009.rs::Comp009
    // frob:tests crates/crunk-rules/src/rules/contrast001.rs::Contrast001
    // frob:tests crates/crunk-rules/src/rules/craft006.rs::Craft006
    // frob:tests crates/crunk-rules/src/rules/craft008.rs::Craft008
    // frob:tests crates/crunk-rules/src/rules/craft010.rs::Craft010
    // frob:tests crates/crunk-rules/src/rules/space001.rs::Space001
    // frob:tests crates/crunk-rules/src/rules/type001.rs::Type001
    // frob:tests crates/crunk-rules/src/rules/type002.rs::Type002
    // frob:tests crates/crunk-rules/src/rules/type003.rs::Type003
    // frob:tests crates/crunk-rules/src/rules/radius001.rs::Radius001
    // frob:tests crates/crunk-rules/src/rules/size001.rs::Size001
    // frob:tests crates/crunk-rules/src/rules/layer001.rs::Layer001
    // frob:tests crates/crunk-rules/src/rules/layout001.rs::Layout001
    // frob:tests crates/crunk-rules/src/rules/layout002.rs::Layout002
    // frob:tests crates/crunk-rules/src/rules/layout003.rs::Layout003
    // frob:tests crates/crunk-rules/src/rules/layout004.rs::Layout004
    // frob:tests crates/crunk-rules/src/rules/layout005.rs::Layout005
    // frob:tests crates/crunk-rules/src/rules/state001.rs::State001
    // frob:tests crates/crunk-rules/src/rules/state002.rs::State002
    // frob:tests crates/crunk-rules/src/rules/state003.rs::State003
    // frob:tests crates/crunk-rules/src/rules/state006.rs::State006
    // frob:tests crates/crunk-rules/src/rules/state007.rs::State007
    // frob:tests crates/crunk-rules/src/rules/org001.rs::Org001
    // frob:tests crates/crunk-rules/src/rules/org002.rs::Org002
    // frob:tests crates/crunk-rules/src/rules/org003.rs::Org003
    // frob:tests crates/crunk-rules/src/rules/org004.rs::Org004
    // frob:tests crates/crunk-rules/src/rules/org005.rs::Org005
    // frob:tests crates/crunk-rules/src/rules/bp001.rs::Bp001
    // frob:tests crates/crunk-rules/src/rules/bp002.rs::Bp002
    // frob:tests crates/crunk-rules/src/rules/bp003.rs::Bp003
    // frob:tests crates/crunk-rules/src/rules/token002.rs::Token002
    // frob:tests crates/crunk-rules/src/rules/token003.rs::Token003
    // frob:tests crates/crunk-rules/src/rules/token004.rs::Token004
    // frob:tests crates/crunk-rules/src/rules/token005.rs::Token005
    // frob:tests crates/crunk-rules/src/rules/token006.rs::Token006
    // frob:tests crates/crunk-rules/src/rules/token007.rs::Token007
    // frob:tests crates/crunk-rules/src/rules/token008.rs::Token008
    // frob:tests crates/crunk-rules/src/rules/token009.rs::Token009
    // frob:tests crates/crunk-rules/src/rules/export001.rs::Export001
    // frob:tests crates/crunk-rules/src/rules/export002.rs::Export002
    // frob:tests crates/crunk-rules/src/rules/tokens001.rs::Tokens001
    // frob:tests crates/crunk-rules/src/rules/tw001.rs::Tw001
    // frob:tests crates/crunk-rules/src/rules/tw002.rs::Tw002
    // frob:tests crates/crunk-rules/src/rules/tw003.rs::Tw003
    // frob:tests crates/crunk-rules/src/rules/tw004.rs::Tw004
    // frob:tests crates/crunk-rules/src/rules/tw005.rs::Tw005
    // frob:tests crates/crunk-rules/src/rules/human001.rs::Human001
    // frob:tests crates/crunk-rules/src/rules/human002.rs::Human002
    // frob:tests crates/crunk-rules/src/rules/gx001.rs::Gx001
    // frob:tests crates/crunk-rules/src/rules/gx002.rs::Gx002
    // frob:tests crates/crunk-rules/src/rules/gx003.rs::Gx003
    // frob:tests crates/crunk-rules/src/rules/gx004.rs::Gx004
    // frob:tests crates/crunk-rules/src/rules/gx005.rs::Gx005
    // frob:tests crates/crunk-rules/src/rules/resp001.rs::Resp001
    // frob:tests crates/crunk-rules/src/rules/scene001.rs::Scene001
    // frob:tests crates/crunk-rules/src/rules/scene002.rs::Scene002
    // frob:tests crates/crunk-rules/src/rules/scene003.rs::Scene003
    // frob:tests crates/crunk-rules/src/rules/scene004.rs::Scene004
    // frob:tests crates/crunk-rules/src/rules/content001.rs::Content001
    // frob:tests crates/crunk-rules/src/rules/content002.rs::Content002
    // frob:tests crates/crunk-rules/src/rules/content003.rs::Content003
    // frob:tests crates/crunk-rules/src/rules/slop001.rs::Slop001
    // frob:tests crates/crunk-rules/src/rules/slop003.rs::Slop003
    // frob:tests crates/crunk-rules/src/rules/slop004.rs::Slop004
    // frob:tests crates/crunk-rules/src/rules/slop010.rs::Slop010
    // frob:tests crates/crunk-rules/src/rules/slop011.rs::Slop011
    // frob:tests crates/crunk-rules/src/rules/slop014.rs::Slop014
    // frob:tests crates/crunk-rules/src/rules/slop022.rs::Slop022
    // frob:tests crates/crunk-rules/src/rules/slop040.rs::Slop040
    // frob:tests crates/crunk-rules/src/rules/slop060.rs::Slop060
    let host = support::project(&case.file_name, &case.text, case.config.as_deref());
    match case.rule.as_str() {
        "COLOR001" => support::run::<Color001>(&host),
        "COLOR002" => support::run::<Color002>(&host),
        "COMP001" => support::run::<Comp001>(&host),
        "COMP002" => support::run::<Comp002>(&host),
        "COMP003" => support::run::<Comp003>(&host),
        "COMP004" => support::run::<Comp004>(&host),
        "COMP005" => support::run::<Comp005>(&host),
        "COMP006" => support::run::<Comp006>(&host),
        "COMP007" => support::run::<Comp007>(&host),
        "COMP008" => support::run::<Comp008>(&host),
        "COMP009" => support::run::<Comp009>(&host),
        "CONTRAST001" => support::run::<Contrast001>(&host),
        "CRAFT006" => support::run::<Craft006>(&host),
        "CRAFT008" => support::run::<Craft008>(&host),
        "CRAFT010" => support::run::<Craft010>(&host),
        "CRAFT013" => support::run::<Craft013>(&host),
        "SPACE001" => support::run::<Space001>(&host),
        "TYPE001" => support::run::<Type001>(&host),
        "TYPE002" => support::run::<Type002>(&host),
        "TYPE003" => support::run::<Type003>(&host),
        "RADIUS001" => support::run::<Radius001>(&host),
        "SIZE001" => support::run::<Size001>(&host),
        "SLOP001" => support::run::<Slop001>(&host),
        "SLOP003" => support::run::<Slop003>(&host),
        "SLOP004" => support::run::<Slop004>(&host),
        "SLOP010" => support::run::<Slop010>(&host),
        "SLOP011" => support::run::<Slop011>(&host),
        "SLOP014" => support::run::<Slop014>(&host),
        "SLOP022" => support::run::<Slop022>(&host),
        "SLOP040" => support::run::<Slop040>(&host),
        "SLOP060" => support::run::<Slop060>(&host),
        "LAYER001" => support::run::<Layer001>(&host),
        "LAYOUT001" => support::run::<Layout001>(&host),
        "LAYOUT002" => support::run::<Layout002>(&host),
        "LAYOUT003" => support::run::<Layout003>(&host),
        "LAYOUT004" => support::run::<Layout004>(&host),
        "LAYOUT005" => support::run::<Layout005>(&host),
        "STATE001" => support::run::<State001>(&host),
        "STATE002" => support::run::<State002>(&host),
        "STATE003" => support::run::<State003>(&host),
        "STATE006" => support::run::<State006>(&host),
        "STATE007" => support::run::<State007>(&host),
        "RESP001" => support::run::<Resp001>(&host),
        "SCENE001" => support::run::<Scene001>(&host),
        "SCENE002" => support::run::<Scene002>(&host),
        "SCENE003" => support::run::<Scene003>(&host),
        "SCENE004" => support::run::<Scene004>(&host),
        "CONTENT001" => support::run::<Content001>(&host),
        "CONTENT002" => support::run::<Content002>(&host),
        "CONTENT003" => support::run::<Content003>(&host),
        "ORG001" => support::run::<Org001>(&host),
        "ORG002" => support::run::<Org002>(&host),
        "ORG003" => support::run::<Org003>(&host),
        "ORG004" => support::run::<Org004>(&host),
        "ORG005" => support::run::<Org005>(&host),
        "BP001" => support::run::<Bp001>(&host),
        "BP002" => support::run::<Bp002>(&host),
        "BP003" => support::run::<Bp003>(&host),
        "TOKEN002" => support::run::<Token002>(&host),
        "TOKEN003" => support::run::<Token003>(&host),
        "TOKEN004" => support::run::<Token004>(&host),
        "TOKEN005" => support::run::<Token005>(&host),
        "TOKEN006" => support::run::<Token006>(&host),
        "TOKEN007" => support::run::<Token007>(&host),
        "TOKEN008" => support::run::<Token008>(&host),
        "TOKEN009" => support::run::<Token009>(&host),
        "EXPORT001" => support::run::<Export001>(&host),
        "EXPORT002" => support::run::<Export002>(&host),
        "TOKENS001" => support::run::<Tokens001>(&host),
        "GX001" => support::run::<Gx001>(&host),
        "GX002" => support::run::<Gx002>(&host),
        "GX003" => support::run::<Gx003>(&host),
        "GX004" => support::run::<Gx004>(&host),
        "GX005" => support::run::<Gx005>(&host),
        "HUMAN001" => support::run::<Human001>(&host),
        "HUMAN002" => support::run::<Human002>(&host),
        "TW001" => support::run::<Tw001>(&host),
        "TW002" => support::run::<Tw002>(&host),
        "TW003" => support::run::<Tw003>(&host),
        "TW004" => support::run::<Tw004>(&host),
        "TW005" => support::run::<Tw005>(&host),
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
#[allow(clippy::too_many_lines, reason = "one assertion per registry row")]
fn the_registry_lists_id_family_severity_fixable_and_doc() {
    let listed = entries(&[&INDEX]);
    let ids: Vec<&str> = listed.iter().map(|e| e.id).collect();
    assert_eq!(
        ids,
        [
            "BP001",
            "BP002",
            "BP003",
            "COLOR001",
            "COLOR002",
            "COMP001",
            "COMP002",
            "COMP003",
            "COMP004",
            "COMP005",
            "COMP006",
            "COMP007",
            "COMP008",
            "COMP009",
            "CONTENT001",
            "CONTENT002",
            "CONTENT003",
            "CONTRAST001",
            "CRAFT006",
            "CRAFT008",
            "CRAFT010",
            "CRAFT013",
            "EXPORT001",
            "EXPORT002",
            "GX001",
            "GX002",
            "GX003",
            "GX004",
            "GX005",
            "HUMAN001",
            "HUMAN002",
            "LAYER001",
            "LAYOUT001",
            "LAYOUT002",
            "LAYOUT003",
            "LAYOUT004",
            "LAYOUT005",
            "ORG001",
            "ORG002",
            "ORG003",
            "ORG004",
            "ORG005",
            "RADIUS001",
            "RESP001",
            "SCENE001",
            "SCENE002",
            "SCENE003",
            "SCENE004",
            "SIZE001",
            "SLOP001",
            "SLOP003",
            "SLOP004",
            "SLOP010",
            "SLOP011",
            "SLOP014",
            "SLOP022",
            "SLOP040",
            "SLOP060",
            "SPACE001",
            "STATE001",
            "STATE002",
            "STATE003",
            "STATE006",
            "STATE007",
            "TOKEN002",
            "TOKEN003",
            "TOKEN004",
            "TOKEN005",
            "TOKEN006",
            "TOKEN007",
            "TOKEN008",
            "TOKEN009",
            "TOKENS001",
            "TW001",
            "TW002",
            "TW003",
            "TW004",
            "TW005",
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

// frob:tests crates/crunk-rules/src/family.rs::gate_severity
#[test]
fn a_rules_own_release_severity_beats_the_family_and_the_default() {
    let advisory = gob_rules::RuleDef {
        id: "ZZZ001",
        family: "ZZZ",
        severity: Severity::Advisory,
        release_severity: Some(Severity::Error),
        ..gob_rules::RuleDef::POISONED
    };
    assert_eq!(gate_severity(&advisory, Gate::Check), Severity::Advisory);
    assert_eq!(gate_severity(&advisory, Gate::Release), Severity::Error);
    let human = gob_rules::RuleDef {
        family: "HUMAN",
        release_severity: Some(Severity::Warn),
        ..gob_rules::RuleDef::POISONED
    };
    assert_eq!(gate_severity(&human, Gate::Release), Severity::Warn);
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
    assert_eq!(ids.len(), 82);
    assert!(ids.contains(&"SPACE001"));
}

// frob:ticket 01M4CXRHCPXFBNQDX85QY70Q62
// frob:tests crates/crunk-rules/src/host.rs::missing_scene_inputs
// frob:tests crates/crunk-rules/src/host.rs::scene_subjects
// frob:tests crates/crunk-rules/src/host.rs::CrunkHost.scenes
// frob:tests crates/crunk-rules/src/scene_files.rs::SceneFile.is_content
// frob:tests crates/crunk-rules/src/scene_files.rs::rect
#[test]
fn scene_host_accessors_report_inputs_and_subjects() {
    use crunk_rules::CrunkHost as _;
    use crunk_rules::host::{missing_scene_inputs, scene_subjects};
    use crunk_rules::scene_files::rect;

    let without = support::project("css/a.css", "a { color: red; }", None);
    assert!(missing_scene_inputs(&without).is_some());
    assert_eq!(scene_subjects(&without), 0);

    let with = support::project("css/a.css", "a { color: red; }", Some("breakpoints-scenes"));
    assert!(missing_scene_inputs(&with).is_none());
    let facts = with.scenes().expect("scenes loaded");
    assert_eq!(scene_subjects(&with), facts.files.len());
    let file = &facts.files[0];
    let node = &file.solve.nodes[0];
    let (left, top, right, bottom) = rect(node);
    assert!(right >= left && bottom >= top);
    assert!(!file.is_content(node));
}

// frob:ticket 01M4CXR89ERNB60CEDG60E2DXH
// frob:tests crates/crunk-rules/src/host.rs::CrunkHost.screens
// frob:tests crates/crunk-rules/src/host.rs::missing_screen_inputs
// frob:tests crates/crunk-rules/src/host.rs::screen_subjects
#[test]
fn screen_host_accessors_report_inputs_and_subjects() {
    use crunk_rules::CrunkHost as _;
    use crunk_rules::host::{missing_screen_inputs, screen_subjects};

    let without = support::project("css/a.css", "a { color: red; }", None);
    let reason = missing_screen_inputs(&without).expect("no screen files");
    assert!(reason.contains("screen.toml"));
    assert_eq!(screen_subjects(&without), 0);
    let facts = without.screens().expect("screens loaded");
    assert!(facts.files.is_empty());
}
