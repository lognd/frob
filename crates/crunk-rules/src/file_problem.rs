//! A design file (component, screen or content) that could not be read or parsed, kept as a fact so
//! SPEC001 reports it instead of the file silently dropping out of every rule's input.

// frob:ticket 01M7ETK8WHHFV8590QXMH57TRZ

use std::fmt::Display;

/// One design file that did not load.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DesignFileProblem {
    /// The file, relative to the project root with forward slashes.
    pub path: String,
    /// What is wrong, as the reader or parser reports it.
    pub message: String,
}

impl DesignFileProblem {
    /// A problem for `path` described by `kind` (for example "component file invalid") and `err`.
    pub fn new(path: &str, kind: &str, err: &impl Display) -> Self {
        tracing::warn!(path, %err, "{kind}");
        Self {
            path: path.to_owned(),
            message: format!("{kind}: {err}"),
        }
    }
}

/// Feed `problems` into `hasher` so a broken file changes the repo digest.
pub fn hash_problems(hasher: &mut blake3::Hasher, problems: &[DesignFileProblem]) {
    for problem in problems {
        hasher.update(problem.path.as_bytes());
        hasher.update(b"\0");
        hasher.update(problem.message.as_bytes());
        hasher.update(b"\0");
    }
}
