//! The spawn allowlist and path resolution.

use std::path::PathBuf;

use crate::ExecError;

/// A program frob may spawn; nothing outside this enum can be executed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Program {
    /// The `git` binary.
    Git,
    /// The `cargo` binary.
    Cargo,
    /// A repo hook script at the given path.
    Hook {
        /// Path to the hook executable.
        path: PathBuf,
    },
    /// A sibling goblin binary (for example `grimble`), next to the current
    /// executable or on `PATH`.
    Sibling {
        /// Binary name.
        name: String,
    },
    /// A configured external tool found on `PATH`.
    Tool {
        /// Binary name.
        name: String,
    },
}

impl Program {
    /// Short human-readable label used in logs and errors.
    pub fn label(&self) -> String {
        match self {
            Self::Git => "git".to_owned(),
            Self::Cargo => "cargo".to_owned(),
            Self::Hook { path } => format!("hook:{}", path.display()),
            Self::Sibling { name } | Self::Tool { name } => name.clone(),
        }
    }

    /// Resolve to an executable path.
    ///
    /// # Errors
    /// [`ExecError::NotAllowed`] for an empty or path-like name, and
    /// [`ExecError::NotFound`] when the program cannot be located.
    pub fn resolve(&self) -> Result<PathBuf, ExecError> {
        match self {
            Self::Git => which_name("git"),
            Self::Cargo => which_name("cargo"),
            Self::Hook { path } => {
                if path.is_file() {
                    Ok(path.clone())
                } else {
                    Err(ExecError::NotFound {
                        program: self.label(),
                    })
                }
            }
            Self::Tool { name } => bare_name(name).and_then(which_name),
            Self::Sibling { name } => crate::discover::find_sibling(name).map(|s| s.path),
        }
    }
}

/// Reject empty names and names containing path separators.
pub(crate) fn bare_name(name: &str) -> Result<&str, ExecError> {
    if name.is_empty() || name.contains(['/', '\\']) {
        return Err(ExecError::NotAllowed {
            program: name.to_owned(),
        });
    }
    Ok(name)
}

/// `PATH` lookup mapping failure to [`ExecError::NotFound`].
fn which_name(name: &str) -> Result<PathBuf, ExecError> {
    which::which(name).map_err(|_| ExecError::NotFound {
        program: name.to_owned(),
    })
}
