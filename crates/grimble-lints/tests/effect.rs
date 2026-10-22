//! React effect cleanup (PAIR001 React vocabulary): `effect::scan` against real component text.

// frob:ticket 01M4D95REZP3PP4F2WD7ASNXV3

use gob_languages::Language;
use grimble_lints::effect::{Reason, Site, scan};
use grimble_lints::res::Certainty;

fn sites(src: &str) -> Vec<Site> {
    scan(Language::Tsx, src).expect("fixture parses")
}

fn reasons(src: &str) -> Vec<(&'static str, Certainty, Reason)> {
    sites(src)
        .iter()
        .map(|s| (s.pair, s.certainty, s.reason))
        .collect()
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn effect_interval_without_cleanup_fires() {
    let src = "function C() { useEffect(() => { const id = setInterval(tick, 1000); }, []); }";
    assert_eq!(
        reasons(src),
        [("set-interval", Certainty::Certain, Reason::NoCleanup)]
    );
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn returned_cleanup_clearing_interval_is_clean() {
    let src = "function C() { useEffect(() => { const id = setInterval(tick, 1000); \
               return () => clearInterval(id); }, []); }";
    assert!(sites(src).is_empty());
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn cleanup_returned_from_nested_function_does_not_count() {
    let src = "function C() { useEffect(() => { const id = setInterval(tick, 1); \
               const helper = () => { return () => clearInterval(id); }; }, []); }";
    assert_eq!(
        reasons(src),
        [("set-interval", Certainty::Certain, Reason::NoCleanup)]
    );
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn cleanup_clearing_a_different_handle_fires() {
    let src = "function C() { useEffect(() => { const a = setInterval(f, 1); const b = setInterval(g, 1); \
               return () => clearInterval(b); }, []); }";
    assert_eq!(
        reasons(src),
        [(
            "set-interval",
            Certainty::Certain,
            Reason::CleanupMissesAcquire
        )]
    );
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn conditional_return_is_unknown() {
    let src = "function C() { useEffect(() => { const id = setInterval(f, 1); \
               if (on) { return () => clearInterval(id); } }, []); }";
    assert_eq!(
        reasons(src),
        [(
            "set-interval",
            Certainty::Unknown,
            Reason::ConditionalCleanup
        )]
    );
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn async_effect_fires() {
    let src = "function C() { useEffect(async () => { const r = await fetch(u); }, []); }";
    assert_eq!(
        reasons(src),
        [("fetch", Certainty::Certain, Reason::AsyncEffect)]
    );
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn listener_removed_with_different_handler_fires() {
    let src = "function C() { useEffect(() => { window.addEventListener('resize', onA); \
               return () => window.removeEventListener('resize', onB); }, []); }";
    assert_eq!(
        reasons(src),
        [(
            "add-event-listener",
            Certainty::Certain,
            Reason::CleanupMissesAcquire
        )]
    );
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn listener_removed_with_same_handler_is_clean() {
    let src = "function C() { useEffect(() => { document.addEventListener('keydown', onKey); \
               return () => document.removeEventListener('keydown', onKey); }, []); }";
    assert!(sites(src).is_empty());
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn fetch_with_abort_or_ignore_flag_is_clean() {
    let abort = "function C() { useEffect(() => { const ctl = new AbortController(); \
                 fetch(u, { signal: ctl.signal }); return () => ctl.abort(); }, []); }";
    let flag = "function C() { useEffect(() => { let ignore = false; fetch(u); \
                return () => { ignore = true; }; }, []); }";
    assert!(sites(abort).is_empty());
    assert!(sites(flag).is_empty());
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn subscription_returned_directly_is_clean() {
    let src = "function C() { useEffect(() => { const unsub = store.subscribe(f); \
               return unsub; }, []); }";
    assert!(sites(src).is_empty());
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn unreadable_returned_cleanup_is_unknown() {
    let src = "function C() { useEffect(() => { const id = setInterval(f, 1); \
               return makeCleanup(id); }, []); }";
    assert_eq!(
        reasons(src),
        [("set-interval", Certainty::Unknown, Reason::OpaqueCleanup)]
    );
}

// frob:tests crates/grimble-lints/src/effect.rs::scan
#[test]
fn other_languages_yield_no_sites() {
    assert!(
        scan(Language::Python, "setInterval(f, 1)")
            .expect("ok")
            .is_empty()
    );
}
