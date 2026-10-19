// frob:ticket 01M3ZX7VDVTM9DJCW5228YRZ8Z
//! Trust review prompt tests (security.md 2.3).
use std::io::Cursor;

use gob_trust::prompt::{
    Decision, Delta, EffectLine, Presence, ReviewFacts, presence, render, review,
};

fn facts(effects: Vec<EffectLine>, subprocess: bool) -> ReviewFacts {
    ReviewFacts {
        pack: "demo-pack".into(),
        tree_digest: "abc123".into(),
        effects,
        binaries: vec![("tool".into(), 4096)],
        on_protected_branch: true,
        reproduced: false,
        signed: false,
        last_author: "Ann\u{1b}[2J Dev".into(),
        subprocess,
    }
}

fn line(effect: &str, delta: Delta) -> EffectLine {
    EffectLine {
        effect: effect.into(),
        delta,
    }
}

// frob:tests crates/gob-trust/src/prompt.rs::presence
#[test]
fn non_tty_and_agent_sessions_are_not_human() {
    let none = |_: &str| None;
    assert_eq!(presence(false, true, none), Presence::NoTty);
    assert_eq!(presence(true, false, none), Presence::NoTty);
    assert_eq!(presence(true, true, none), Presence::Human);
    let agent = |k: &str| (k == "CLAUDECODE").then(|| "1".to_owned());
    assert_eq!(presence(true, true, agent), Presence::Agent);
}

// frob:tests crates/gob-trust/src/prompt.rs::render
#[test]
fn widening_is_shown_first_and_in_full_without_control_chars() {
    let f = facts(
        vec![
            line("fs.read src/**", Delta::Unchanged),
            line("net api.example.com", Delta::Added),
            line("env HOME", Delta::Added),
        ],
        false,
    );
    let text = render(&f);
    let lines: Vec<&str> = text.lines().collect();
    assert!(lines[1].starts_with("WIDENING"), "{text}");
    assert_eq!(lines[2], "  + net api.example.com");
    assert_eq!(lines[3], "  + env HOME");
    assert!(text.find("WIDENING").unwrap() < text.find("tree digest").unwrap());
    assert!(!text.contains('\u{1b}'), "control characters leaked");
    assert!(text.contains("binary: tool (4096 bytes)"));
    assert!(text.contains("reproduced: no"));
}

// frob:tests crates/gob-trust/src/prompt.rs::review
#[test]
fn widening_needs_the_pack_name_and_plain_yes_does_not_approve() {
    let f = facts(vec![line("net api.example.com", Delta::Added)], false);
    let mut out = Vec::new();
    let d = review(&f, &mut Cursor::new("yes\n"), &mut out).unwrap();
    assert_eq!(d, Decision::Deny);
    let d = review(&f, &mut Cursor::new("demo-pack\n"), &mut out).unwrap();
    assert_eq!(d, Decision::Approve);
    let shown = String::from_utf8(out).unwrap();
    assert!(shown.contains("Type the pack name"));
}

// frob:tests crates/gob-trust/src/prompt.rs::review
#[test]
fn subprocess_needs_the_name_and_plain_review_accepts_yes() {
    let sub = facts(vec![], true);
    let mut out = Vec::new();
    assert_eq!(
        review(&sub, &mut Cursor::new("yes\n"), &mut out).unwrap(),
        Decision::Deny
    );
    let plain = facts(vec![line("fs.read src/**", Delta::Unchanged)], false);
    assert_eq!(
        review(&plain, &mut Cursor::new("yes\n"), &mut out).unwrap(),
        Decision::Approve
    );
    assert_eq!(
        review(&plain, &mut Cursor::new(""), &mut out).unwrap(),
        Decision::Deny
    );
}
