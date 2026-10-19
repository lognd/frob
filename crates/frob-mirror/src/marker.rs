//! Marker v1 (mirror.md 3.3, security.md 2.11): format, parse and trust decision.
//!
//! A marker is `frob:v1 kid=<id> ulid=<ULID> nonce=<n> mac=<hex>`. It counts only in the
//! bot-authored creation revision of an issue body; anything else carrying one is MIR003.

// frob:ticket 01M3ZX851JW2KYRMCCK5RQKG5W

use gob_trust::Tag;

use crate::github::read::{CreationRevision, Fidelity};
use crate::keyring::{Keyring, KeyringError, MarkerFields, SignedMarker};

/// Marker prefix and version tag.
const PREFIX: &str = "frob:v1";

/// Why a bot-authored marker was not adopted.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Rejection {
    /// The kid is unknown or expired (MIR001 marker-key-unknown); never a recreate.
    KeyUnknown {
        /// The kid named by the marker.
        kid: String,
    },
    /// The MAC does not verify (wrong key, other repository, edited fields).
    BadMac {
        /// The kid named by the marker.
        kid: String,
    },
    /// The marker text is malformed.
    Malformed,
}

/// What the mirror concludes about one issue's marker.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MarkerVerdict {
    /// No marker in the creation revision.
    None,
    /// A valid bot-authored marker: the issue is adopted for this ULID.
    Adopted(SignedMarker),
    /// A marker on an issue not created by a mirror bot: ignored, reported as MIR003 (Advisory).
    Spoofed,
    /// A bot-authored marker that does not verify: not adopted.
    Rejected(Rejection),
    /// The creation revision is unavailable (history gap): nothing is trusted.
    Unreadable,
}

/// Render a signed marker as its one-line text.
pub fn format_marker(m: &SignedMarker) -> String {
    format!(
        "{PREFIX} kid={} ulid={} nonce={} mac={}",
        m.kid,
        m.fields.ulid,
        m.fields.nonce,
        m.tag.to_hex()
    )
}

/// Parse the first marker in `body` bound to `repo_node_id`; `None` when no marker text is
/// present, `Some(Err(()))` when marker text is present but malformed.
pub fn parse_marker(body: &str, repo_node_id: &str) -> Option<Result<SignedMarker, ()>> {
    let start = body.find(PREFIX)?;
    let line = body[start..].lines().next().unwrap_or_default();
    let line = line.split("-->").next().unwrap_or_default().trim();
    Some(parse_line(line, repo_node_id).ok_or(()))
}

/// Parse one marker line; `None` unless all four fields are present exactly once.
fn parse_line(line: &str, repo_node_id: &str) -> Option<SignedMarker> {
    let mut parts = line.split_whitespace();
    if parts.next()? != PREFIX {
        return None;
    }
    let (mut kid, mut ulid, mut nonce, mut mac) = (None, None, None, None);
    for part in parts {
        let (k, v) = part.split_once('=')?;
        let slot = match k {
            "kid" => &mut kid,
            "ulid" => &mut ulid,
            "nonce" => &mut nonce,
            "mac" => &mut mac,
            _ => return None,
        };
        if slot.replace(v.to_owned()).is_some() {
            return None;
        }
    }
    Some(SignedMarker {
        kid: kid?,
        fields: MarkerFields {
            repo_node_id: repo_node_id.to_owned(),
            ulid: ulid?,
            nonce: nonce?,
        },
        tag: Tag::from_hex(&mac?)?,
    })
}

/// Decide what the creation revision's marker means: trusted only when authored by one of
/// `bot_ids` (user ids) and the MAC verifies under the keyring at `now` (unix seconds).
pub fn evaluate(
    creation: &CreationRevision,
    bot_ids: &[u64],
    ring: &Keyring,
    repo_node_id: &str,
    now: i64,
) -> MarkerVerdict {
    if creation.fidelity == Fidelity::Gap && creation.body.is_none() {
        tracing::warn!("marker: creation revision unavailable");
        return MarkerVerdict::Unreadable;
    }
    let Some(body) = creation.body.as_deref() else {
        return MarkerVerdict::Unreadable;
    };
    let Some(parsed) = parse_marker(body, repo_node_id) else {
        return MarkerVerdict::None;
    };
    if !bot_ids.contains(&creation.author_id) {
        tracing::warn!(
            author = creation.author_id,
            "MIR003 spoofed-marker: ignored"
        );
        return MarkerVerdict::Spoofed;
    }
    let Ok(marker) = parsed else {
        tracing::warn!("marker: malformed on bot issue");
        return MarkerVerdict::Rejected(Rejection::Malformed);
    };
    match ring.verify(&marker, now) {
        Ok(()) => {
            tracing::debug!(kid = %marker.kid, ulid = %marker.fields.ulid, "marker adopted");
            MarkerVerdict::Adopted(marker)
        }
        Err(KeyringError::UnknownKid { kid }) => {
            tracing::warn!(%kid, "MIR001 marker-key-unknown");
            MarkerVerdict::Rejected(Rejection::KeyUnknown { kid })
        }
        Err(_) => {
            tracing::warn!(kid = %marker.kid, "marker MAC mismatch: not adopted");
            MarkerVerdict::Rejected(Rejection::BadMac { kid: marker.kid })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_trust::MachineKey;

    const BOT: u64 = 7;

    fn ring(seed: u8) -> Keyring {
        Keyring::new("k1", MachineKey::from_bytes([seed; 32]), vec![]).unwrap()
    }

    fn signed(r: &Keyring) -> SignedMarker {
        r.sign(MarkerFields {
            repo_node_id: "R_1".into(),
            ulid: "01ABC".into(),
            nonce: "n1".into(),
        })
    }

    fn creation(author: u64, body: String) -> CreationRevision {
        CreationRevision {
            author_id: author,
            body: Some(body),
            fidelity: Fidelity::Full,
        }
    }

    fn body_of(m: &SignedMarker) -> String {
        format!("text\n<!-- {} -->", format_marker(m))
    }

    // frob:tests evaluate
    #[test]
    fn other_user_with_valid_looking_marker_is_spoofed() {
        let r = ring(1);
        let c = creation(99, body_of(&signed(&r)));
        assert_eq!(evaluate(&c, &[BOT], &r, "R_1", 0), MarkerVerdict::Spoofed);
    }

    // frob:tests evaluate
    #[test]
    fn bot_issue_with_wrong_mac_is_not_adopted() {
        let signer = ring(2);
        let c = creation(BOT, body_of(&signed(&signer)));
        let v = evaluate(&c, &[BOT], &ring(1), "R_1", 0);
        assert_eq!(
            v,
            MarkerVerdict::Rejected(Rejection::BadMac { kid: "k1".into() })
        );
    }

    // frob:tests evaluate
    #[test]
    fn bot_issue_with_valid_marker_is_adopted() {
        let r = ring(1);
        let m = signed(&r);
        let c = creation(BOT, body_of(&m));
        assert_eq!(
            evaluate(&c, &[BOT], &r, "R_1", 0),
            MarkerVerdict::Adopted(m)
        );
    }

    // frob:tests evaluate
    #[test]
    fn marker_is_bound_to_repository() {
        let r = ring(1);
        let c = creation(BOT, body_of(&signed(&r)));
        assert!(matches!(
            evaluate(&c, &[BOT], &r, "R_other", 0),
            MarkerVerdict::Rejected(Rejection::BadMac { .. })
        ));
    }

    // frob:tests evaluate
    #[test]
    fn unknown_kid_is_mir001_not_recreate() {
        let r = ring(1);
        let mut m = signed(&r);
        m.kid = "gone".into();
        let c = creation(BOT, body_of(&m));
        assert_eq!(
            evaluate(&c, &[BOT], &r, "R_1", 0),
            MarkerVerdict::Rejected(Rejection::KeyUnknown { kid: "gone".into() })
        );
    }

    // frob:tests evaluate
    #[test]
    fn no_marker_and_gap_cases() {
        let r = ring(1);
        assert_eq!(
            evaluate(&creation(BOT, "plain".into()), &[BOT], &r, "R_1", 0),
            MarkerVerdict::None
        );
        let gap = CreationRevision {
            author_id: BOT,
            body: None,
            fidelity: Fidelity::Gap,
        };
        assert_eq!(
            evaluate(&gap, &[BOT], &r, "R_1", 0),
            MarkerVerdict::Unreadable
        );
    }

    // frob:tests parse_marker
    #[test]
    fn format_parse_round_trip_and_malformed() {
        let m = signed(&ring(1));
        assert_eq!(parse_marker(&format_marker(&m), "R_1"), Some(Ok(m)));
        assert_eq!(parse_marker("frob:v1 kid=a", "R_1"), Some(Err(())));
        assert_eq!(parse_marker("nothing", "R_1"), None);
    }
}
