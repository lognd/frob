//! TOKENS001's comparison: a generated file as it should be against the bytes on disk.
//!
//! The expected bytes are a side input outside the ingested styles (like GEN001's): the host
//! renders them from the spec, and the rule only compares.

// frob:ticket 01M43ATBY4CHA4FYVC7BWK6MXR

use std::path::PathBuf;

/// One generated file: where it lives, what the exporter would write and what is there now.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GeneratedFile {
    /// Absolute path of the generated file.
    pub path: PathBuf,
    /// The bytes the exporter produces from the current spec.
    pub expected: String,
    /// The bytes on disk, `None` when the file does not exist.
    pub actual: Option<String>,
}

/// Why `file` is stale, `None` when it matches byte for byte.
pub fn drift(file: &GeneratedFile) -> Option<String> {
    let Some(actual) = &file.actual else {
        return Some("is missing".to_owned());
    };
    if *actual == file.expected {
        return None;
    }
    let line = actual
        .lines()
        .zip(file.expected.lines())
        .position(|(a, e)| a != e)
        .unwrap_or_else(|| actual.lines().count().min(file.expected.lines().count()))
        + 1;
    Some(format!("differs from the generated output at line {line}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn file(expected: &str, actual: Option<&str>) -> GeneratedFile {
        GeneratedFile {
            path: PathBuf::from("tokens.css"),
            expected: expected.to_owned(),
            actual: actual.map(str::to_owned),
        }
    }

    // frob:tests crates/crunk-rules/src/tokens_drift.rs::drift
    #[test]
    fn drift_names_missing_stale_and_clean() {
        assert_eq!(drift(&file("a\n", Some("a\n"))), None);
        assert_eq!(drift(&file("a\n", None)).as_deref(), Some("is missing"));
        let stale = drift(&file("a\nb\n", Some("a\nc\n"))).expect("stale");
        assert!(stale.ends_with("line 2"), "{stale}");
        let shorter = drift(&file("a\nb\n", Some("a\n"))).expect("stale");
        assert!(shorter.ends_with("line 2"), "{shorter}");
    }
}
