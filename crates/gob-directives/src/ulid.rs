//! Ticket id shape checks (D24: only full 26-char ULIDs persist).

/// True for characters in Crockford base32 (digits and letters minus I, L, O, U), any case.
fn is_crockford(c: char) -> bool {
    c.is_ascii_alphanumeric() && !matches!(c.to_ascii_uppercase(), 'I' | 'L' | 'O' | 'U')
}

/// True when `s` is a canonical full ULID: 26 uppercase Crockford base32 chars, first at most `7`.
///
/// ```
/// assert!(gob_directives::is_full_ulid("01J9QKX3M8Z4T7N2V5B6C0D1E2"));
/// assert!(!gob_directives::is_full_ulid("T-0042"));
/// assert!(!gob_directives::is_full_ulid("~3M8Z4T7"));
/// ```
pub fn is_full_ulid(s: &str) -> bool {
    s.len() == 26
        && s.chars()
            .all(|c| is_crockford(c) && !c.is_ascii_lowercase())
        && s.starts_with(|c: char| ('0'..='7').contains(&c))
}

/// True when `s` is a v1 ticket alias (`T-` then digits), resolved through the ledger's aliases.
pub fn is_v1_alias(s: &str) -> bool {
    s.strip_prefix("T-")
        .is_some_and(|d| !d.is_empty() && d.chars().all(|c| c.is_ascii_digit()))
}

/// True when `s` is not a full ULID but reads like a ticket reference.
///
/// Covers v1 `T-0042` forms, `~handle` forms, and bare Crockford strings of
/// 7 to 26 characters (handles, truncated or lowercase ULIDs).
pub fn looks_like_ticket_ref(s: &str) -> bool {
    if is_full_ulid(s) {
        return false;
    }
    let v1 = s
        .strip_prefix(['T', 't'])
        .and_then(|r| r.strip_prefix('-'))
        .is_some_and(|d| !d.is_empty() && d.chars().all(|c| c.is_ascii_digit()));
    let handle = s
        .strip_prefix('~')
        .is_some_and(|h| !h.is_empty() && h.chars().all(is_crockford));
    let bare = (7..=26).contains(&s.len()) && s.chars().all(is_crockford);
    v1 || handle || bare
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-directives/src/ulid.rs::is_v1_alias
    #[test]
    fn v1_aliases_are_recognised() {
        assert!(is_v1_alias("T-0042"));
        assert!(!is_v1_alias("t-0042"));
        assert!(!is_v1_alias("T-"));
        assert!(!is_v1_alias("T-4x"));
    }

    #[test]
    fn full_ulid_accepted() {
        assert!(is_full_ulid("01J9QKX3M8Z4T7N2V5B6C0D1E2"));
    }

    #[test]
    fn near_misses_rejected() {
        assert!(!is_full_ulid("01J9QKX3M8Z4T7N2V5B6C0D1E")); // 25
        assert!(!is_full_ulid("01j9qkx3m8z4t7n2v5b6c0d1e2")); // lowercase
        assert!(!is_full_ulid("81J9QKX3M8Z4T7N2V5B6C0D1E2")); // overflow
        assert!(!is_full_ulid("01J9QKX3M8Z4T7N2V5B6C0D1EU")); // U excluded
    }

    #[test]
    fn ref_shapes() {
        assert!(looks_like_ticket_ref("T-0042"));
        assert!(looks_like_ticket_ref("~3M8Z4T7"));
        assert!(looks_like_ticket_ref("3M8Z4T7"));
        assert!(looks_like_ticket_ref("01j9qkx3m8z4t7n2v5b6c0d1e2"));
        assert!(!looks_like_ticket_ref("01J9QKX3M8Z4T7N2V5B6C0D1E2"));
        assert!(!looks_like_ticket_ref("banana"));
        assert!(!looks_like_ticket_ref("hello world"));
    }
}
