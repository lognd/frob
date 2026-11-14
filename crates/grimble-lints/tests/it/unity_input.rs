//! UNITY301: legacy `Input` use under the Input System handler.

// frob:ticket 01M4D94ZPDYBATXNCVY3XRQ6RM

use gob_languages::Language;
use grimble_lints::res::Certainty;
use grimble_lints::unity_input::{InputHandler, active_input_handler, scan};

fn hits(handler: InputHandler, src: &str) -> Vec<Certainty> {
    scan(Language::CSharp, src, handler)
        .expect("fixture parses")
        .iter()
        .map(|f| f.certainty)
        .collect()
}

const SPACE: &str =
    "class P : MonoBehaviour { void Update() { if (Input.GetKey(KeyCode.Space)) Jump(); } }";

// frob:tests crates/grimble-lints/src/unity_input.rs::scan
// frob:tests crates/grimble-lints/src/unity_input.rs::active_input_handler
#[test]
fn input_system_handler_flags_legacy_get_key() {
    let settings = "PlayerSettings:\n  activeInputHandler: 1\n";
    let handler = active_input_handler(settings).expect("handler parses");
    assert_eq!(handler, InputHandler::InputSystem);
    let found = scan(Language::CSharp, SPACE, handler).expect("fixture parses");
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].rule, "UNITY301");
    assert_eq!(found[0].certainty, Certainty::Certain);
}

// frob:tests crates/grimble-lints/src/unity_input.rs::scan
#[test]
fn legacy_and_both_handlers_stay_quiet() {
    assert!(hits(InputHandler::Legacy, SPACE).is_empty());
    assert!(hits(InputHandler::Both, SPACE).is_empty());
}

// frob:tests crates/grimble-lints/src/unity_input.rs::active_input_handler
#[test]
fn handler_values_parse() {
    assert_eq!(
        active_input_handler("  activeInputHandler: 0"),
        Some(InputHandler::Legacy)
    );
    assert_eq!(
        active_input_handler("  activeInputHandler: 2"),
        Some(InputHandler::Both)
    );
    assert_eq!(active_input_handler("a: 1"), Some(InputHandler::Legacy));
    assert_eq!(active_input_handler("  activeInputHandler: 9"), None);
}

// frob:tests crates/grimble-lints/src/unity_input.rs::scan
#[test]
fn legacy_guard_branch_is_dead_under_input_system() {
    let src = "class P { void Update() {\n#if ENABLE_LEGACY_INPUT_MANAGER\n if (Input.GetKey(KeyCode.A)) {}\n#else\n if (Keyboard.current.aKey.isPressed) {}\n#endif\n} }";
    assert!(hits(InputHandler::InputSystem, src).is_empty());
    let unknown = "class P { void Update() {\n#if UNITY_EDITOR\n if (Input.GetKey(KeyCode.A)) {}\n#endif\n} }";
    assert_eq!(
        hits(InputHandler::InputSystem, unknown),
        [Certainty::Certain]
    );
}

// frob:tests crates/grimble-lints/src/unity_input.rs::scan
#[test]
fn user_declared_input_is_unknown() {
    let src = "class Input { public static bool GetKey(int k) => false; } class P { void Update() { Input.GetKey(1); } }";
    assert_eq!(hits(InputHandler::InputSystem, src), [Certainty::Unknown]);
}

// frob:tests crates/grimble-lints/src/unity_input.rs::scan
#[test]
fn qualified_member_reads_and_static_import_are_flagged() {
    let src = "using static UnityEngine.Input;\nclass P { void Update() { var p = UnityEngine.Input.mousePosition; var k = GetKeyDown(KeyCode.A); var a = Other.GetKey(1); } }";
    assert_eq!(hits(InputHandler::InputSystem, src).len(), 2);
}

// frob:tests crates/grimble-lints/src/unity_input.rs::scan
#[test]
fn compound_conditions_and_elif_are_evaluated() {
    let dead = "class P { void U() {\n#if ENABLE_LEGACY_INPUT_MANAGER && UNITY_EDITOR\n Input.GetKey(1);\n#elif !ENABLE_INPUT_SYSTEM\n Input.GetKey(2);\n#endif\n} }";
    assert!(hits(InputHandler::InputSystem, dead).is_empty());
    let live = "class P { void U() {\n#if (ENABLE_LEGACY_INPUT_MANAGER)\n x();\n#elif ENABLE_INPUT_SYSTEM\n Input.GetKey(2);\n#endif\n} }";
    assert_eq!(hits(InputHandler::InputSystem, live), [Certainty::Certain]);
}
