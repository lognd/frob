//! Ambient-source vocabularies: the callee names that read the clock, randomness, the
//! environment, files, the network, stdio or exit the process (the classes NEAT013 sweeps).
//!
//! The names are read from the shared registry (`gob_ir::registry`); this module holds none.

// frob:ticket 01M539NQGFCK3VJGRBM3H6CT56

pub use gob_ir::registry::AMBIENT_CLASSES;

/// Whether `name` is a registered ambient-source callee of `lang` (any ambient class).
pub fn is_ambient_name(lang: &str, name: &str) -> bool {
    let hit = AMBIENT_CLASSES.iter().any(|class| {
        gob_ir::registry::callee_names(lang, class)
            .iter()
            .any(|(_, pattern)| gob_ir::registry::callee_matches(pattern, name))
    });
    tracing::trace!(lang, name, hit, "ambient name lookup");
    hit
}

#[cfg(test)]
mod tests {
    use super::is_ambient_name;

    // frob:tests crates/gob-symbols/src/ambient.rs::is_ambient_name
    #[test]
    fn python_clock_and_rng_names_are_ambient_and_helpers_are_not() {
        assert!(is_ambient_name("python", "time.time"));
        assert!(is_ambient_name("python", "random.randint"));
        assert!(!is_ambient_name("python", "helper"));
        assert!(!is_ambient_name("lua", "time.time"));
        assert!(is_ambient_name("python", "open"));
        assert!(is_ambient_name("python", "requests.get"));
    }
}
