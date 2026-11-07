//! Unity method discovery through the universal model.

// frob:ticket 01M6SNTWXQ02EDA6ZB70W3WZW0

use gob_languages::Language;
use tree_sitter::Node;

use crate::fn_spans;
use crate::res::ScanError;

/// The adapter path whose extension selects the C# universal-model fold.
const MODEL_PATH: &str = "unity.cs";

/// Byte spans of every method and function of the C# `text`, from the model.
pub(crate) fn method_spans(text: &str) -> Result<Vec<(usize, usize)>, ScanError> {
    fn_spans::function_spans(MODEL_PATH, text).map_err(ScanError::Model)
}

/// Method spans of `text` when it is C#; none for another language, which has no Unity scan.
pub(crate) fn spans_for(language: Language, text: &str) -> Result<Vec<(usize, usize)>, ScanError> {
    if language == Language::CSharp {
        method_spans(text)
    } else {
        Ok(Vec::new())
    }
}

/// Keep the `(name, method)` pairs the model also has a method unit over.
pub(crate) fn gated<'t>(
    methods: Vec<(String, Node<'t>)>,
    spans: &[(usize, usize)],
) -> Vec<(String, Node<'t>)> {
    methods
        .into_iter()
        .filter(|(name, m)| {
            let kept = fn_spans::covers(spans, m.start_byte(), m.end_byte());
            if !kept {
                tracing::trace!(method = %name, "unity: tree method has no model method unit");
            }
            kept
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{unity, unity_hot, unity_input, unity_physics};
    use gob_languages::Language;

    const HOT: &str = "using UnityEngine;\nclass A : MonoBehaviour {\n  void Update() { var c = GetComponent<Rigidbody>(); }\n}\n";
    const PAIR: &str = "using UnityEngine;\nclass A : MonoBehaviour {\n  void OnEnable() { ev += OnX; }\n  void OnX() {}\n}\n";
    const PHYS: &str = "using UnityEngine;\nclass A : MonoBehaviour {\n  Rigidbody rb;\n  void Update() { rb.AddForce(Vector3.up); }\n}\n";

    // frob:tests crates/grimble-lints/src/unity_model.rs::method_spans
    #[test]
    fn method_spans_cover_each_csharp_method() {
        assert!(!method_spans(HOT).expect("model").is_empty());
    }

    // frob:tests crates/grimble-lints/src/unity_model.rs::spans_for
    #[test]
    fn non_csharp_has_no_spans() {
        assert!(
            spans_for(Language::Rust, "fn f() {}")
                .expect("ok")
                .is_empty()
        );
    }

    // frob:tests crates/grimble-lints/src/unity_hot.rs::scan
    #[test]
    fn hot_lookup_is_found_through_the_model() {
        let found = unity_hot::scan(Language::CSharp, HOT).expect("scans");
        assert_eq!(found.len(), 1);
    }

    // frob:tests crates/grimble-lints/src/unity_physics.rs::scan
    #[test]
    fn per_frame_force_is_found_through_the_model() {
        let found = unity_physics::scan(Language::CSharp, PHYS).expect("scans");
        assert_eq!(found.len(), 1);
    }

    // frob:tests crates/grimble-lints/src/unity.rs::scan
    #[test]
    fn unpaired_acquire_is_found_through_the_model() {
        let sites = unity::scan(Language::CSharp, PAIR).expect("scans");
        assert_eq!(sites.len(), 1);
    }

    // frob:tests crates/grimble-lints/src/unity_hot.rs::scan
    #[test]
    fn every_adapter_language_scans_hot_without_error() {
        for language in Language::ALL {
            unity_hot::scan(language, "x = 1\n")
                .unwrap_or_else(|e| panic!("{}: {e}", language.name()));
        }
    }

    // frob:tests crates/grimble-lints/src/unity_physics.rs::scan
    #[test]
    fn every_adapter_language_scans_physics_without_error() {
        for language in Language::ALL {
            unity_physics::scan(language, "x = 1\n")
                .unwrap_or_else(|e| panic!("{}: {e}", language.name()));
        }
    }

    // frob:tests crates/grimble-lints/src/unity.rs::scan
    #[test]
    fn every_adapter_language_scans_pairs_without_error() {
        for language in Language::ALL {
            unity::scan(language, "x = 1\n").unwrap_or_else(|e| panic!("{}: {e}", language.name()));
        }
    }

    // frob:tests crates/grimble-lints/src/unity_input.rs::scan
    #[test]
    fn every_adapter_language_scans_input_without_error() {
        for language in Language::ALL {
            unity_input::scan(language, "x = 1\n", unity_input::InputHandler::InputSystem)
                .unwrap_or_else(|e| panic!("{}: {e}", language.name()));
        }
    }
}
