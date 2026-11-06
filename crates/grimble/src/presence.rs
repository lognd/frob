//! Who may acknowledge a capability grant: a person at a terminal who is a listed attester.
//!
//! Presence and the attester match are shared with `frob` through `gob_cli`; this module only
//! turns them into the grant-approval refusals (`E-ATTEST-NOT-HUMAN`, `E-ATTEST-NOT-ATTESTER`).

// frob:ticket 01M4GYBNW01DT1MJ6NJN2GX6NN

use gob_cli::{CliError, Presence, Refusal, RefusalClass, is_listed_attester};

/// The identity allowed to approve grants, or the refusal that says why nobody here may.
///
/// `identity` is the git `user.email`; `attesters` is frob.toml `[evidence] attesters`.
///
/// # Errors
///
/// `E-ATTEST-NOT-HUMAN` when no person is at a terminal, `E-ATTEST-NOT-ATTESTER` when the
/// identity is missing or not listed.
pub fn authorize(
    presence: &Presence,
    identity: Option<&str>,
    attesters: &[String],
) -> Result<String, CliError> {
    let reasons = presence.reasons();
    if !reasons.is_empty() {
        tracing::warn!(?reasons, "grant approval refused: no person present");
        return Err(Refusal::new(
            "E-ATTEST-NOT-HUMAN",
            RefusalClass::GuardNeedsAction,
            format!(
                "E-ATTEST-NOT-HUMAN: an attestation is a person's statement; refused because {}",
                reasons.join("; ")
            ),
        )
        .with_remedy(
            "stop and tell the user which grants need approval; only a person at an interactive terminal can run `grimble ack --grants`, and an agent never does",
        )
        .requiring_human()
        .into());
    }
    match identity {
        Some(id) if is_listed_attester(id, attesters) => Ok(id.to_owned()),
        _ => {
            let who = identity.map_or_else(
                || "no git user.email is set".to_owned(),
                |i| format!("`{i}` is not an attester"),
            );
            let list = if attesters.is_empty() {
                "[evidence] attesters is empty, so nobody may approve grants".to_owned()
            } else {
                format!("[evidence] attesters lists {}", attesters.join(", "))
            };
            tracing::warn!(%who, "grant approval refused: not an attester");
            Err(Refusal::new(
                "E-ATTEST-NOT-ATTESTER",
                RefusalClass::GuardNeedsAction,
                format!("E-ATTEST-NOT-ATTESTER: {who}; {list}"),
            )
            .with_remedy(
                "the repository owner must list the approving identity under [evidence] attesters in frob.toml; an agent must not edit that list",
            )
            .requiring_human()
            .into())
        }
    }
}
