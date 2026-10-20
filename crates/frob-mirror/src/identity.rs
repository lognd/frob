//! Mirror identities (mirror.md 2.1 people, 3.3 bot ids, 3.5 identities by user id).
//!
//! Frob identities map to tracker users by tracker user id, never by login: logins can be
//! released and claimed by someone else, ids cannot. An identity with no mapping leaves the
//! issue unassigned and the published note says so. The tracker key (`PROJ-123`) becomes an
//! alias of the ticket so a lookup by that key resolves.

// frob:ticket 01M3ZX855DB35XQZQPFKYWR6WX

use std::collections::{BTreeMap, BTreeSet};

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::{debug, info, warn};

use crate::projection::{Identity, People};

/// Why identity configuration failed to load.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum IdentityError {
    /// The text is not a valid `[mirror.identities]` / `bot_ids` document.
    #[error("identities are malformed: {0}")]
    Malformed(String),
    /// Two frob identities map to one tracker user id.
    #[error("tracker user id {0} is mapped by more than one identity")]
    DuplicateUser(u64),
    /// A tracker key is empty or contains whitespace.
    #[error("tracker key `{0}` is not a valid alias")]
    BadKey(String),
}

/// The `[mirror]` identity configuration: the user-id map and the App identities.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct IdentityConfig {
    /// Frob identity (owner or assignee string) to tracker user id.
    #[serde(default)]
    pub identities: BTreeMap<String, u64>,
    /// The mirror's own App identities, by tracker user id.
    #[serde(default)]
    pub bot_ids: Vec<u64>,
}

impl IdentityConfig {
    /// Parse a JSON identity document and reject two identities sharing a user id.
    ///
    /// # Errors
    /// [`IdentityError::Malformed`] on bad shape (a login string where an id belongs is bad
    /// shape), [`IdentityError::DuplicateUser`] when an id is mapped twice.
    pub fn parse(text: &str) -> Result<Self, IdentityError> {
        let cfg: Self =
            serde_json::from_str(text).map_err(|e| IdentityError::Malformed(e.to_string()))?;
        let mut seen = BTreeSet::new();
        for id in cfg.identities.values() {
            if !seen.insert(*id) {
                warn!(user_id = id, "identity map rejected: duplicate user id");
                return Err(IdentityError::DuplicateUser(*id));
            }
        }
        debug!(
            identities = cfg.identities.len(),
            bots = cfg.bot_ids.len(),
            "identity config parsed"
        );
        Ok(cfg)
    }

    /// Whether `user_id` is one of the mirror's own App identities.
    #[must_use]
    pub fn is_bot(&self, user_id: u64) -> bool {
        self.bot_ids.contains(&user_id)
    }

    /// The frob identity mapped to a tracker user id, if any (reverse lookup for edits).
    #[must_use]
    pub fn frob_identity(&self, user_id: u64) -> Option<&str> {
        self.identities
            .iter()
            .find(|(_, id)| **id == user_id)
            .map(|(name, _)| name.as_str())
    }
}

/// Owner and assignee resolved to tracker user ids, with the notes for unmapped identities.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ResolvedPeople {
    /// Tracker user id to assign; `None` leaves the issue unassigned.
    pub assignee: Option<u64>,
    /// Tracker user id of the owner, when mapped.
    pub owner: Option<u64>,
    /// Lines for the published note, one per identity that could not be mapped.
    pub notes: Vec<String>,
}

/// Resolve a projection's people through the identity map; unmapped ones become notes.
#[must_use]
pub fn resolve_people(people: &People, cfg: &IdentityConfig) -> ResolvedPeople {
    let mut out = ResolvedPeople::default();
    let mut one = |role: &str, who: Option<&String>| -> Option<u64> {
        let name = who?;
        if let Some(id) = cfg.identities.get(name) {
            debug!(role, user_id = id, "identity resolved");
            Some(*id)
        } else {
            info!(role, "identity has no tracker mapping; left unassigned");
            out.notes.push(format!(
                "{role} `{name}` has no tracker user mapping; the issue is unassigned for them"
            ));
            None
        }
    };
    let assignee = one("assignee", people.assignee.as_ref());
    let owner = one("owner", people.owner.as_ref());
    out.assignee = assignee;
    out.owner = owner;
    out
}

/// Add a tracker key (such as `PROJ-123`) to a ticket identity's aliases, once.
///
/// # Errors
/// [`IdentityError::BadKey`] when the key is empty or has whitespace.
pub fn add_tracker_alias(identity: &mut Identity, key: &str) -> Result<bool, IdentityError> {
    if key.is_empty() || key.chars().any(char::is_whitespace) {
        return Err(IdentityError::BadKey(key.to_owned()));
    }
    if identity.aliases.iter().any(|a| a == key) {
        debug!(key, "tracker alias already present");
        return Ok(false);
    }
    identity.aliases.push(key.to_owned());
    info!(ulid = %identity.ulid, key, "tracker key added as ticket alias");
    Ok(true)
}

/// Find the ticket ULID answering to `reference` (ULID, handle or alias such as a tracker key).
#[must_use]
pub fn resolve_reference<'a>(tickets: &'a [Identity], reference: &str) -> Option<&'a str> {
    tickets
        .iter()
        .find(|t| {
            t.ulid == reference || t.handle == reference || t.aliases.iter().any(|a| a == reference)
        })
        .map(|t| t.ulid.as_str())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg() -> IdentityConfig {
        IdentityConfig::parse(r#"{"identities":{"alice":1001,"bob":1002},"bot_ids":[77]}"#)
            .expect("valid")
    }

    fn ident() -> Identity {
        Identity {
            ulid: "01ABC".into(),
            handle: "~ABC".into(),
            aliases: vec![],
            repository: "r".into(),
            ledger_path: "p".into(),
        }
    }

    // frob:tests resolve_people
    #[test]
    fn unmapped_owner_is_unassigned_and_noted() {
        let people = People {
            owner: Some("carol".into()),
            assignee: Some("carol".into()),
        };
        let r = resolve_people(&people, &cfg());
        assert_eq!(r.assignee, None);
        assert_eq!(r.owner, None);
        assert_eq!(r.notes.len(), 2);
        assert!(r.notes[0].contains("no tracker user mapping"));
    }

    // frob:tests resolve_people
    #[test]
    fn mapped_identity_resolves_to_user_id() {
        let people = People {
            owner: Some("alice".into()),
            assignee: Some("bob".into()),
        };
        let r = resolve_people(&people, &cfg());
        assert_eq!((r.owner, r.assignee), (Some(1001), Some(1002)));
        assert!(r.notes.is_empty());
    }

    // frob:tests parse
    #[test]
    fn logins_are_rejected_as_ids_and_duplicates_refused() {
        assert!(matches!(
            IdentityConfig::parse(r#"{"bot_ids":["octocat"]}"#),
            Err(IdentityError::Malformed(_))
        ));
        assert_eq!(
            IdentityConfig::parse(r#"{"identities":{"a":5,"b":5}}"#),
            Err(IdentityError::DuplicateUser(5))
        );
    }

    // frob:tests is_bot
    #[test]
    fn bot_ids_are_user_ids() {
        let c = cfg();
        assert!(c.is_bot(77));
        assert!(!c.is_bot(1001));
        assert_eq!(c.frob_identity(1002), Some("bob"));
    }

    // frob:tests add_tracker_alias
    // frob:tests resolve_reference
    #[test]
    fn tracker_key_alias_resolves_the_ticket() {
        let mut t = ident();
        assert_eq!(add_tracker_alias(&mut t, "PROJ-123"), Ok(true));
        assert_eq!(add_tracker_alias(&mut t, "PROJ-123"), Ok(false));
        assert!(add_tracker_alias(&mut t, "bad key").is_err());
        let all = vec![t];
        assert_eq!(resolve_reference(&all, "PROJ-123"), Some("01ABC"));
        assert_eq!(resolve_reference(&all, "PROJ-999"), None);
    }
}
