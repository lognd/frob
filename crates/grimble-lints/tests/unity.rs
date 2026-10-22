//! Unity lifecycle pairing (PAIR001 Unity vocabulary): `unity::scan` against real C# class text.

// frob:ticket 01M4D955ZSR7MHM6TXXD49JJ4V

use gob_languages::Language;
use grimble_lints::res::Certainty;
use grimble_lints::unity::{Reason, Site, scan};

fn sites(body: &str) -> Vec<Site> {
    let src = format!("class P : MonoBehaviour {{ {body} }}");
    scan(Language::CSharp, &src).expect("fixture parses")
}

fn reasons(body: &str) -> Vec<(&'static str, Certainty, Reason)> {
    sites(body)
        .iter()
        .map(|s| (s.pair, s.certainty, s.reason))
        .collect()
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_event_without_unsubscribe_names_both_sites() {
    let body = "void OnEnable() { Health.Changed += Hit; } void OnDisable() { Other.Changed -= Hit; } void Hit() {}";
    let found = sites(body);
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].reason, Reason::TeardownMissesAcquire);
    assert_eq!(found[0].certainty, Certainty::Certain);
    assert!(found[0].teardown.is_some());
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_lambda_subscription_is_unresolved() {
    let body =
        "void OnEnable() { Health.Changed += () => Hit(); } void OnDisable() {} void Hit() {}";
    assert_eq!(
        reasons(body),
        [(
            "event-subscription",
            Certainty::Unknown,
            Reason::AnonymousHandler
        )]
    );
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_unsubscribe_in_ondisable_or_ondestroy_is_clean() {
    let a = "void OnEnable() { Health.Changed += Hit; } void OnDisable() { Health.Changed -= Hit; } void Hit() {}";
    let b = "void OnEnable() { Health.Changed += Hit; } void OnDestroy() { Health.Changed -= Hit; } void Hit() {}";
    assert!(sites(a).is_empty());
    assert!(sites(b).is_empty());
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_missing_teardown_is_certain() {
    let body = "void OnEnable() { GameManager.OnWin += Won; } void Won() {}";
    assert_eq!(
        reasons(body),
        [("event-subscription", Certainty::Certain, Reason::NoTeardown)]
    );
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_conditional_unsubscribe_is_unknown() {
    let body = "void OnEnable() { Health.Changed += Hit; } void OnDisable() { if (x) { Health.Changed -= Hit; } } void Hit() {}";
    assert_eq!(
        reasons(body),
        [(
            "event-subscription",
            Certainty::Unknown,
            Reason::ConditionalTeardown
        )]
    );
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_arithmetic_plus_equals_is_ignored() {
    let body = "void OnEnable() { score += bonus; } void OnDisable() {}";
    assert!(sites(body).is_empty());
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_register_callback_pairs_with_unregister() {
    let ok = "void OnEnable() { root.RegisterCallback<ClickEvent>(Clicked); } void OnDisable() { root.UnregisterCallback<ClickEvent>(Clicked); } void Clicked(ClickEvent e) {}";
    let bad = "void OnEnable() { root.RegisterCallback<ClickEvent>(Clicked); } void OnDisable() { root.UnregisterCallback<ClickEvent>(Other); } void Clicked(ClickEvent e) {}";
    assert!(sites(ok).is_empty());
    assert_eq!(reasons(bad).len(), 1);
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_input_action_enable_needs_disable() {
    let bad = "InputAction jump; void OnEnable() { jump.Enable(); } void OnDisable() {}";
    let ok =
        "InputAction jump; void OnEnable() { jump.Enable(); } void OnDisable() { jump.Disable(); }";
    assert_eq!(
        reasons(bad),
        [(
            "input-action-enable",
            Certainty::Certain,
            Reason::TeardownMissesAcquire
        )]
    );
    assert!(sites(ok).is_empty());
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_addressables_load_needs_release_of_handle() {
    let ok = "AsyncOperationHandle<Sprite> h; void Start() { h = Addressables.LoadAssetAsync<Sprite>(key); } void OnDestroy() { Addressables.Release(h); }";
    let bad =
        "void Start() { var h = Addressables.LoadAssetAsync<Sprite>(key); } void OnDestroy() {}";
    let unbound = "void Start() { Addressables.LoadAssetAsync<Sprite>(key); } void OnDestroy() {}";
    assert!(sites(ok).is_empty());
    assert_eq!(
        reasons(bad),
        [(
            "addressables-handle",
            Certainty::Certain,
            Reason::TeardownMissesAcquire
        )]
    );
    assert_eq!(
        reasons(unbound),
        [(
            "addressables-handle",
            Certainty::Unknown,
            Reason::UnboundHandle
        )]
    );
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_teardown_follows_helper_method() {
    let body = "void OnEnable() { Health.Changed += Hit; } void OnDisable() { Cleanup(); } void Cleanup() { Health.Changed -= Hit; } void Hit() {}";
    assert!(sites(body).is_empty());
}

// frob:tests crates/grimble-lints/src/unity.rs::scan
#[test]
fn unity_other_languages_yield_nothing() {
    assert!(
        scan(Language::Rust, "fn main() {}")
            .expect("parses")
            .is_empty()
    );
}
