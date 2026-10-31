//! The phase lint profile: alpha structure only, beta A11Y and HUMAN001, live metrics too.

// frob:ticket 01M5XCYCP797Z6M8WPBW7FAD5W

use std::path::Path;

use crunk_rules::phase_profile::{Skip, report, runs};
use crunk_spec::{DEFAULT_PHASE, Phase, ResolvedPhase, SpecErrorKind, read_phase};

const A11Y: [&str; 3] = ["A11Y001", "A11Y002", "A11Y010"];
const STRUCTURE: [&str; 3] = ["TOKEN001", "ORG001", "COMP001"];
const LIVE: [&str; 2] = ["METRIC001", "EXPERIMENT001"];

fn spec_with(lint: &str) -> crunk_spec::DesignSpec {
    let text = crunk_spec::presets::DEFAULT.replace("[lint]", &format!("[lint]\n{lint}"));
    crunk_spec::parse_spec(&text, Path::new("crunk.toml"), Path::new("/proj")).unwrap()
}

fn declared(phase: Phase) -> ResolvedPhase {
    ResolvedPhase {
        phase,
        defaulted: false,
    }
}

fn all_ids() -> Vec<&'static str> {
    [&A11Y[..], &STRUCTURE, &LIVE, &["HUMAN001", "COLOR001"]].concat()
}

#[test]
fn alpha_runs_only_structure_and_lists_human_and_a11y_as_not_applicable() {
    let spec = spec_with("");
    let r = report(&spec, declared(Phase::Alpha), all_ids());
    for id in STRUCTURE {
        assert!(!r.not_applicable.iter().any(|n| n == id), "{id} must run");
    }
    for id in A11Y.iter().chain(&["HUMAN001", "COLOR001"]) {
        assert!(
            r.not_applicable.iter().any(|n| n == id),
            "{id} must be skipped"
        );
    }
    assert_eq!(
        runs(&spec, Phase::Alpha, "HUMAN001"),
        Err(Skip::TooEarly(Phase::Beta))
    );
}

#[test]
fn beta_runs_a11y_and_human001_but_not_metrics() {
    let spec = spec_with("");
    let r = report(&spec, declared(Phase::Beta), all_ids());
    assert_eq!(r.not_applicable, LIVE);
}

#[test]
fn live_runs_everything() {
    let spec = spec_with("");
    let r = report(&spec, declared(Phase::Live), all_ids());
    assert!(r.not_applicable.is_empty());
    assert_eq!(r.lines().len(), 1);
}

#[test]
fn explicit_lint_setting_overrides_the_profile() {
    let spec = spec_with("COLOR001 = \"warn\"");
    assert_eq!(runs(&spec, Phase::Alpha, "COLOR001"), Ok(()));
    assert!(runs(&spec, Phase::Alpha, "COLOR002").is_err());
}

#[test]
fn absent_phase_defaults_to_beta_and_the_envelope_says_so() {
    let r = read_phase("[project]\n", Path::new("crunk.toml")).unwrap();
    assert_eq!(r.phase, DEFAULT_PHASE);
    assert!(r.defaulted);
    assert!(r.note().contains("defaulting to beta"));
    let spec = spec_with("");
    let lines = report(&spec, r, ["A11Y001"]).lines();
    assert!(lines[0].contains("defaulting to beta"));
}

#[test]
fn declared_phase_is_read() {
    let r = read_phase("phase = \"alpha\"\n", Path::new("crunk.toml")).unwrap();
    assert_eq!(r.phase, Phase::Alpha);
    assert!(!r.defaulted);
}

#[test]
fn unknown_phase_is_a_located_error_listing_the_four_values() {
    let err = read_phase("# c\n\nphase = \"gamma\"\n", Path::new("crunk.toml")).unwrap_err();
    assert_eq!(err.kind(), SpecErrorKind::Invalid);
    assert_eq!(err.location().map(|l| l.line), Some(3));
    let text = err.to_string();
    assert!(text.contains("discovery, alpha, beta, live"), "{text}");
}
