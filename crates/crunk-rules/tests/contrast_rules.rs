//! CONTRAST001 beyond the rule page: the measured ratio in the message, per-role floors, the
//! location and applicability.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

mod support;

use crunk_rules::contrast::measure_roles;
use crunk_rules::mode::Mode;
use crunk_rules::rules::contrast001::Contrast001;
use crunk_values::Color;

fn spec_with(ink: &str, role: &str) -> String {
    crunk_spec::presets::preset("default")
        .expect("default preset")
        .replace("ink = \"#1a1a1a\"", &format!("ink = \"{ink}\""))
        .replace("paper = \"#fafaf7\"", "paper = \"#ffffff\"")
        .replace("body = [\"ink\", \"paper\"]", role)
}

// frob:tests crates/crunk-rules/src/rules/contrast001.rs::Contrast001
#[test]
fn a_pair_just_below_the_floor_fires_with_the_measured_ratio() {
    let ink = "#797979";
    let ratio = Color::parse(ink)
        .expect("ink")
        .contrast_ratio(Color::parse("#ffffff").expect("paper"));
    assert!((4.3..4.5).contains(&ratio), "fixture ratio {ratio}");
    let host = support::project(
        "crunk.toml",
        &spec_with(ink, "body = [\"ink\", \"paper\"]"),
        None,
    );
    let found = support::run::<Contrast001>(&host);
    assert_eq!(found.len(), 1, "{found:?}");
    let want = format!("role \"body\" (ink/paper) contrast {ratio:.2} is below the 4.5 floor");
    assert_eq!(found[0].message, want);
}

// frob:tests crates/crunk-rules/src/rules/contrast001.rs::Contrast001
#[test]
fn a_role_with_its_own_lower_floor_is_judged_against_it() {
    let host = support::project(
        "crunk.toml",
        &spec_with(
            "#797979",
            "body = { pair = [\"ink\", \"paper\"], floor = 3.0 }",
        ),
        None,
    );
    assert!(support::run::<Contrast001>(&host).is_empty());
}

// frob:tests crates/crunk-rules/src/contrast/mod.rs::measure_roles
#[test]
fn measure_roles_reports_ratio_and_floor_per_role() {
    let host = support::project(
        "crunk.toml",
        &spec_with("#000000", "body = [\"ink\", \"paper\"]"),
        None,
    );
    let measured = measure_roles(&host.spec, Mode::DEFAULT);
    assert_eq!(measured.len(), 1);
    assert!(
        (measured[0].ratio - 21.0).abs() < 0.01,
        "{}",
        measured[0].ratio
    );
    assert!(!measured[0].fails());
    assert!((measured[0].floor - 4.5).abs() < f64::EPSILON);
}

// frob:tests crates/crunk-rules/src/rules/contrast001.rs::Contrast001
#[test]
fn the_finding_sits_at_the_start_of_the_spec() {
    let host = support::project(
        "crunk.toml",
        &spec_with("#999999", "body = [\"ink\", \"paper\"]"),
        None,
    );
    let found = support::run::<Contrast001>(&host);
    let span = found[0].span.expect("located in crunk.toml");
    assert_eq!(span.range.start().to_usize(), 0);
}
