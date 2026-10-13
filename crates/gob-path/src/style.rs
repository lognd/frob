//! Path styles (Unix and Windows) and per-component validation, usable on any host.

use typed_path::{Utf8Component, Utf8Encoding, Utf8UnixEncoding, Utf8WindowsEncoding};

use crate::PathError;

/// Which path grammar to read a host path with.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PathStyle {
    /// `/` separators, case-sensitive.
    Unix,
    /// Drive letters, UNC, `\` and `/` separators, case-insensitive.
    Windows,
}

/// A host path split into its anchor (prefix and root) and its normal names.
pub(crate) struct Split {
    pub anchor: String,
    pub names: Vec<String>,
}

impl PathStyle {
    /// The style of the machine this binary runs on.
    pub const fn host() -> Self {
        if cfg!(windows) {
            Self::Windows
        } else {
            Self::Unix
        }
    }

    /// The separator this style writes.
    pub const fn sep(self) -> char {
        match self {
            Self::Unix => '/',
            Self::Windows => '\\',
        }
    }

    /// Split `s` into anchor and names; `None` when it contains a `..` component.
    pub(crate) fn split(self, s: &str) -> Option<Split> {
        match self {
            Self::Unix => split_with::<Utf8UnixEncoding>(s, false),
            Self::Windows => split_with::<Utf8WindowsEncoding>(s, true),
        }
    }

    /// Whether two names are the same file name under this style.
    pub(crate) fn same(self, a: &str, b: &str) -> bool {
        match self {
            Self::Unix => a == b,
            Self::Windows => a.to_lowercase() == b.to_lowercase(),
        }
    }
}

fn split_with<E: Utf8Encoding>(s: &str, fold: bool) -> Option<Split> {
    let mut anchor = String::new();
    let mut names = Vec::new();
    for c in E::components(s) {
        if c.is_parent() {
            return None;
        } else if c.is_normal() {
            names.push(c.as_str().to_owned());
        } else if c.as_str() != "." {
            anchor.push_str(c.as_str());
        }
    }
    if fold {
        anchor = anchor.to_lowercase().replace('/', "\\");
    }
    Some(Split { anchor, names })
}

const RESERVED: [&str; 4] = ["con", "prn", "aux", "nul"];

/// Refuse a component that is invalid on any supported platform, naming the component and the platform.
///
/// # Errors
/// [`PathError::BadComponent`] for reserved device names, `<>:"|?*`, control characters, `\`,
/// and a trailing dot or space.
pub fn validate_component(c: &str) -> Result<(), PathError> {
    let bad = |platform, reason| {
        tracing::debug!(component = c, platform, reason, "refused path component");
        Err(PathError::BadComponent {
            component: c.to_owned(),
            platform,
            reason,
        })
    };
    if c.contains('\0') {
        return bad("unix", "NUL byte");
    }
    if c.chars().any(|ch| {
        matches!(ch, '<' | '>' | ':' | '"' | '|' | '?' | '*' | '\\') || (ch as u32) < 0x20
    }) {
        return bad("windows", "reserved character");
    }
    if c.ends_with('.') || c.ends_with(' ') {
        return bad("windows", "trailing dot or space");
    }
    let stem = c.split('.').next().unwrap_or(c).trim_end().to_lowercase();
    let numbered = |p: &str| {
        stem.strip_prefix(p)
            .is_some_and(|n| matches!(n.as_bytes(), [b'1'..=b'9']))
    };
    if RESERVED.contains(&stem.as_str()) || numbered("com") || numbered("lpt") {
        return bad("windows", "reserved device name");
    }
    Ok(())
}
