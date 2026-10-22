//! UNITY302: Rigidbody forces and moves outside `FixedUpdate`.

// frob:ticket 01M4D94ZPDYBATXNCVY3XRQ6RM

use gob_languages::Language;
use grimble_lints::res::Certainty;
use grimble_lints::unity_physics::scan;

fn hits(body: &str) -> Vec<Certainty> {
    let src = format!("class P : MonoBehaviour {{ Rigidbody rb; {body} }}");
    scan(Language::CSharp, &src)
        .expect("fixture parses")
        .iter()
        .map(|f| f.certainty)
        .collect()
}

// frob:tests crates/grimble-lints/src/unity_physics.rs::scan
#[test]
fn add_force_in_update_fires_and_in_fixed_update_is_clean() {
    assert_eq!(
        hits("void Update() { rb.AddForce(Vector3.up); }"),
        [Certainty::Certain]
    );
    let found = scan(
        Language::CSharp,
        "class P { Rigidbody rb; void Update() { rb.AddForce(v); } }",
    )
    .expect("fixture parses");
    assert_eq!(found[0].rule, "UNITY302");
    assert!(hits("void FixedUpdate() { rb.AddForce(Vector3.up); }").is_empty());
}

// frob:tests crates/grimble-lints/src/unity_physics.rs::scan
#[test]
fn helper_called_from_update_is_followed_but_coroutines_are_not() {
    assert_eq!(
        hits("void Update() { Push(); } void Push() { rb.AddTorque(t); }"),
        [Certainty::Certain]
    );
    assert!(
        hits("void Update() { StartCoroutine(Push()); } IEnumerator Push() { yield return new WaitForFixedUpdate(); rb.AddForce(v); }")
            .is_empty()
    );
}

// frob:tests crates/grimble-lints/src/unity_physics.rs::scan
#[test]
fn one_shot_impulse_under_edge_trigger_is_exempt() {
    assert!(
        hits("void Update() { if (Input.GetKeyDown(KeyCode.Space)) rb.AddForce(v, ForceMode.Impulse); }")
            .is_empty()
    );
    assert_eq!(
        hits("void Update() { rb.AddForce(v, ForceMode.Impulse); }"),
        [Certainty::Certain]
    );
}

// frob:tests crates/grimble-lints/src/unity_physics.rs::scan
#[test]
fn transform_moves_need_a_body_and_no_kinematic() {
    assert_eq!(
        hits("void LateUpdate() { transform.position += v; transform.Translate(v); }").len(),
        2
    );
    assert!(
        hits("void Awake() { rb.isKinematic = true; } void Update() { transform.Translate(v); }")
            .is_empty()
    );
    let no_body = "class P { void Update() { transform.Translate(v); } }";
    assert!(
        scan(Language::CSharp, no_body)
            .expect("fixture parses")
            .is_empty()
    );
}

// frob:tests crates/grimble-lints/src/unity_physics.rs::scan
#[test]
fn unresolved_receivers_are_unknown_or_skipped() {
    assert_eq!(
        hits("void Update() { body.AddForce(v); }"),
        [Certainty::Unknown]
    );
    assert!(hits("void Update() { body.MovePosition(v); }").is_empty());
    assert!(hits("void Update() { Vector3 other = v; other.AddForce(v); }").is_empty());
    assert_eq!(
        hits("void Update() { var b = GetComponent<Rigidbody>(); b.MovePosition(v); }"),
        [Certainty::Certain]
    );
}
