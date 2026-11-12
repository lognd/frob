//! Guards the recorded text-shaping spike result (~HKN808M): parley agrees with
//! Chromium within tolerance, beats cosmic-text on agreement, and both are
//! deterministic. The measurements live in notes/research/text-shaping-spike.

use std::path::PathBuf;

use serde_json::Value;

/// Parity tolerance in px the solver may assume against Chromium.
const TOLERANCE_PX: f64 = 0.05;

fn results() -> Value {
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../notes/research/text-shaping-spike/results.json");
    let text = std::fs::read_to_string(&p).expect("results.json is committed with the spike");
    serde_json::from_str(&text).expect("results.json is valid JSON")
}

/// Largest absolute width delta of `lib` against Chromium, skipping the empty string.
fn max_delta(r: &Value, lib: &str) -> f64 {
    let fonts = r["fonts"].as_array().expect("fonts");
    let mut max = 0.0f64;
    for (i, f) in fonts.iter().enumerate() {
        let ours = r[lib]["widths"][f.as_str().expect("name")]
            .as_array()
            .expect("widths");
        let theirs = r["chrome"][format!("F{i}")]
            .as_array()
            .expect("chrome widths");
        assert_eq!(ours.len(), 200, "{lib} measured the full corpus");
        assert_eq!(theirs.len(), 200, "chromium measured the full corpus");
        for (a, b) in ours.iter().zip(theirs).skip(1) {
            max = max.max((a.as_f64().expect("f") - b.as_f64().expect("f")).abs());
        }
    }
    max
}

// frob:ticket 01M4CXRCXEYE7GZSYRPHKN808M
#[test]
fn spike_records_parley_within_tolerance_of_chromium() {
    let r = results();
    assert_eq!(r["choice"], "parley");
    assert!(max_delta(&r, "parley") < TOLERANCE_PX);
}

// frob:ticket 01M4CXRCXEYE7GZSYRPHKN808M
#[test]
fn spike_shows_cosmic_text_drifts_and_both_are_deterministic() {
    let r = results();
    assert!(max_delta(&r, "cosmic-text") > TOLERANCE_PX);
    assert_eq!(r["parley"]["deterministic"], true);
    assert_eq!(r["cosmic-text"]["deterministic"], true);
}
