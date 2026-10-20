//! Pin classification for external references (actions, reusable workflows, images).
//!
//! A reference is Must when it names immutable content (a commit SHA or an image
//! digest), May when it names a mutable tag or branch, and Unknown when it names
//! nothing (no tag, or `latest`).

// frob:ticket 01M3Z71542Y6NZG3G8A83EFRF2

use gob_ir::Status;

/// True when `s` is a full git object name (40 or 64 hex digits).
fn is_full_sha(s: &str) -> bool {
    matches!(s.len(), 40 | 64) && s.bytes().all(|b| b.is_ascii_hexdigit())
}

/// The pin status of `reference` (`owner/repo@ref`, `image:tag`, `image@sha256:..`).
#[must_use]
pub(crate) fn pin_status(reference: &str) -> Status {
    if let Some((_, rev)) = reference.rsplit_once('@') {
        return if is_full_sha(rev) || rev.contains(':') {
            Status::Must
        } else if rev.is_empty() || rev == "latest" {
            Status::Unknown
        } else {
            Status::May
        };
    }
    let last = reference.rsplit('/').next().unwrap_or(reference);
    match last.rsplit_once(':') {
        Some((_, tag)) if !tag.is_empty() && tag != "latest" => Status::May,
        _ => Status::Unknown,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests pin_status
    #[test]
    fn classifies_pins() {
        let sha = "a".repeat(40);
        assert_eq!(pin_status(&format!("actions/checkout@{sha}")), Status::Must);
        assert_eq!(pin_status("actions/checkout@v4"), Status::May);
        assert_eq!(pin_status("actions/checkout"), Status::Unknown);
        assert_eq!(pin_status("rust@sha256:abcd"), Status::Must);
        assert_eq!(pin_status("rust:1.80"), Status::May);
        assert_eq!(pin_status("rust:latest"), Status::Unknown);
        assert_eq!(pin_status("rust"), Status::Unknown);
        assert_eq!(pin_status("host:5000/rust"), Status::Unknown);
    }
}
