//! The de-slop epic end to end: a generated landing page with the default indigo, emoji bullets and
//! three identical icon cards is reported by the SLOP rules and by the paired CRAFT presence rules,
//! each finding carrying evidence, and the T0 run lists the layout tell as not run, never clean.

// frob:ticket 01M4CXT3N608HMB1A77VTT4YXX

use std::path::Path;

use crunk_check::{CheckOptions, Tier, run, run_to_tier};

fn write(root: &Path, rel: &str, text: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, text).expect("write");
}

/// A project that chose nothing: a Tailwind indigo accent, no scales, no state roles, no voice file.
fn landing_page() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    write(
        dir.path(),
        "crunk.toml",
        concat!(
            "[project]
css_root = \"styles\"
tokens_file = \"tokens.css\"
root_font_size = 16

",
            "[palette]
ink = \"#1a1a1a\"
paper = \"#fafaf7\"

",
            "[scales]
spacing = [0, 4, 8]
font_sizes = [16]
radii = []

",
            "[typography]
families = [\"Inter\"]
weights = [400, 700]

",
            "[org]
buckets = [\"base\"]
class_case = \"kebab\"
component_prefix = true
tokens_only_custom_props = true
",
        ),
    );
    write(
        dir.path(),
        "styles/a.css",
        ".cta { background: #6366f1; color: #ffffff; }\nli::before { content: \"\u{1f680}\"; }\n",
    );
    write(
        dir.path(),
        "design/scenes/page.scene.html",
        concat!(
            "<section data-id=\"features\" style=\"display:flex;width:900px\">\n",
            "<div data-id=\"a\" style=\"width:300px;height:200px\"><svg data-id=\"a-i\" style=\"width:24px;height:24px\"></svg><h3 data-id=\"a-h\" data-copy=\"a.h\">Fast</h3><p data-id=\"a-p\">Quick.</p></div>\n",
            "<div data-id=\"b\" style=\"width:300px;height:200px\"><svg data-id=\"b-i\" style=\"width:24px;height:24px\"></svg><h3 data-id=\"b-h\">Safe</h3><p data-id=\"b-p\">Sound.</p></div>\n",
            "<div data-id=\"c\" style=\"width:300px;height:200px\"><svg data-id=\"c-i\" style=\"width:24px;height:24px\"></svg><h3 data-id=\"c-h\">Free</h3><p data-id=\"c-p\">Open.</p></div>\n",
            "</section>\n",
        ),
    );
    dir
}

// frob:tests crates/crunk-check/src/lib.rs::run
// frob:tests crates/crunk-check/src/lib.rs::run_to_tier
#[test]
fn a_generated_landing_page_reports_the_slop_findings_and_the_missing_craft_decisions() {
    let dir = landing_page();
    let found = run(dir.path(), &CheckOptions::default()).expect("run");
    let by = |id: &str| -> Vec<(String, String)> {
        found
            .report
            .findings
            .iter()
            .filter(|f| f.rule.as_str() == id)
            .map(|f| {
                let file = f
                    .span
                    .and_then(|s| found.report.files.path(s.file))
                    .unwrap_or("")
                    .to_owned();
                (file, f.message.clone())
            })
            .collect()
    };

    let indigo = by("SLOP001");
    assert!(
        indigo.iter().any(|(file, _)| file == "styles/a.css"),
        "{indigo:?}"
    );
    let emoji = by("SLOP040");
    assert!(
        emoji.iter().any(|(file, _)| file == "styles/a.css"),
        "{emoji:?}"
    );
    let cards = by("SLOP020");
    assert!(
        cards
            .iter()
            .any(|(file, _)| file == "design/scenes/page.scene.html"),
        "{cards:?}"
    );
    for (rule, hits) in [
        ("SLOP001", &indigo),
        ("SLOP040", &emoji),
        ("SLOP020", &cards),
    ] {
        assert!(hits.iter().all(|(_, m)| !m.is_empty()), "{rule} evidence");
    }

    // The paired presence rules say which decisions are missing.
    let scales = by("CRAFT006");
    assert!(
        scales.iter().all(|(file, _)| file == "crunk.toml") && !scales.is_empty(),
        "{scales:?}"
    );
    assert!(
        scales.iter().any(|(_, m)| m.contains("no radius policy")),
        "{scales:?}"
    );
    let roles = by("CRAFT008");
    assert!(
        roles.iter().all(|(file, _)| file == "crunk.toml") && !roles.is_empty(),
        "{roles:?}"
    );
    assert!(
        roles.iter().any(|(_, m)| m.contains("no `danger` role")),
        "{roles:?}"
    );
    assert!(
        !by("CRAFT013").is_empty(),
        "scene copy key without voice file"
    );

    // At T0 the layout tell is listed as not run, never reported clean.
    let t0 = run_to_tier(dir.path(), &CheckOptions::default(), Tier::T0).expect("run T0");
    let not_run = t0
        .not_run
        .iter()
        .find(|n| n.rule == "SLOP020")
        .expect("SLOP020 listed as not run");
    assert_eq!(not_run.tier, Tier::T1);
}
