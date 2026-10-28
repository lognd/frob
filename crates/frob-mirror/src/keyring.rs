//! Marker keyring (mirror.md 3.3): one signing key, older keys that verify only
//! until a stated time, and a budgeted re-marking plan for rotation.
//!
//! Keys come from the credentials environment, never from repository files.

// frob:ticket 01M4052RG3QVXW6CHTG8BNS7CD

use gob_trust::{
    Canonical, CanonicalWriter, MachineKey, Tag, TrustError, mac_record, verify_record,
};

/// MAC domain for markers.
const MARKER_CONTEXT: &str = "frob-mirror-marker/v1";

/// Why a keyring operation failed.
#[derive(Debug, thiserror::Error)]
pub enum KeyringError {
    /// The kid is not in the keyring, or its verify-only period has ended (MIR001 marker-key-unknown).
    #[error(
        "marker key {kid:?} is unknown or past its verify-only period (MIR001 marker-key-unknown)"
    )]
    UnknownKid {
        /// The kid named by the marker.
        kid: String,
    },
    /// The MAC does not match: a copied or forged marker.
    #[error("marker MAC does not verify under key {kid:?}")]
    BadMac {
        /// The kid named by the marker.
        kid: String,
    },
    /// A key could not be read from the environment.
    #[error("cannot load key {kid:?}: {source}")]
    Load {
        /// The kid being loaded.
        kid: String,
        /// The underlying failure.
        source: TrustError,
    },
    /// Two keys share a kid.
    #[error("duplicate key id {kid:?} in keyring")]
    DuplicateKid {
        /// The repeated kid.
        kid: String,
    },
    /// A rotation budget of zero can never finish.
    #[error("re-marking budget must be at least 1 operation per run")]
    ZeroBudget,
}

/// The authenticated fields of a marker: what the MAC covers.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MarkerFields {
    /// Repository node id the marker is bound to.
    pub repo_node_id: String,
    /// The ticket ULID.
    pub ulid: String,
    /// The create nonce.
    pub nonce: String,
}

impl Canonical for MarkerFields {
    fn write_canonical(&self, w: &mut CanonicalWriter) {
        w.str(&self.repo_node_id).str(&self.ulid).str(&self.nonce);
    }
}

/// A signed marker: `frob:v1 kid=<id> ulid=<ULID> nonce=<n> mac=<...>` in structured form.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SignedMarker {
    /// The key that signed it.
    pub kid: String,
    /// The authenticated fields.
    pub fields: MarkerFields,
    /// The MAC tag.
    pub tag: Tag,
}

/// An older key: verifies markers until `verify_until` (unix seconds, exclusive), never signs.
struct VerifyOnly {
    kid: String,
    key: MachineKey,
    verify_until: i64,
}

/// Configuration of one older key: where its secret lives and until when it verifies.
#[derive(Debug, Clone)]
pub struct OlderKeySpec {
    /// Key id.
    pub kid: String,
    /// Environment variable holding the 64-hex key.
    pub var: String,
    /// Unix seconds at which the key stops verifying.
    pub verify_until: i64,
}

/// One signing key plus verify-only older keys.
pub struct Keyring {
    current_kid: String,
    current: MachineKey,
    older: Vec<VerifyOnly>,
}

impl std::fmt::Debug for Keyring {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Keyring")
            .field("current_kid", &self.current_kid)
            .field(
                "older",
                &self.older.iter().map(|o| &o.kid).collect::<Vec<_>>(),
            )
            .finish_non_exhaustive()
    }
}

impl Keyring {
    /// Build a keyring from in-memory keys (tests and callers that already hold the secrets).
    ///
    /// # Errors
    /// [`KeyringError::DuplicateKid`] when a kid repeats.
    pub fn new(
        current_kid: &str,
        current: MachineKey,
        older: Vec<(String, MachineKey, i64)>,
    ) -> Result<Self, KeyringError> {
        let mut seen = vec![current_kid.to_owned()];
        for (kid, _, _) in &older {
            if seen.contains(kid) {
                return Err(KeyringError::DuplicateKid { kid: kid.clone() });
            }
            seen.push(kid.clone());
        }
        tracing::debug!(current_kid, older = older.len(), "keyring built");
        Ok(Self {
            current_kid: current_kid.to_owned(),
            current,
            older: older
                .into_iter()
                .map(|(kid, key, verify_until)| VerifyOnly {
                    kid,
                    key,
                    verify_until,
                })
                .collect(),
        })
    }

    /// Load the keyring from environment variables (credentials environment only).
    ///
    /// # Errors
    /// [`KeyringError::Load`] for an unset or malformed variable, or [`KeyringError::DuplicateKid`].
    pub fn from_env(
        current_kid: &str,
        current_var: &str,
        older: &[OlderKeySpec],
    ) -> Result<Self, KeyringError> {
        let load = |kid: &str, var: &str| {
            MachineKey::from_env_var(var).map_err(|source| KeyringError::Load {
                kid: kid.to_owned(),
                source,
            })
        };
        let current = load(current_kid, current_var)?;
        let mut keys = Vec::with_capacity(older.len());
        for spec in older {
            keys.push((
                spec.kid.clone(),
                load(&spec.kid, &spec.var)?,
                spec.verify_until,
            ));
        }
        Self::new(current_kid, current, keys)
    }

    /// The kid new markers are signed under.
    pub fn current_kid(&self) -> &str {
        &self.current_kid
    }

    /// Sign `fields` with the current key only.
    pub fn sign(&self, fields: MarkerFields) -> SignedMarker {
        let tag = mac_record(&self.current, MARKER_CONTEXT, &fields);
        tracing::debug!(kid = %self.current_kid, ulid = %fields.ulid, "marker signed");
        SignedMarker {
            kid: self.current_kid.clone(),
            fields,
            tag,
        }
    }

    /// Verify a marker at time `now` (unix seconds): current key always, older keys until their end.
    ///
    /// # Errors
    /// [`KeyringError::UnknownKid`] for an absent or expired kid; [`KeyringError::BadMac`] otherwise.
    pub fn verify(&self, marker: &SignedMarker, now: i64) -> Result<(), KeyringError> {
        let key = if marker.kid == self.current_kid {
            &self.current
        } else {
            match self.older.iter().find(|o| o.kid == marker.kid) {
                Some(o) if now < o.verify_until => &o.key,
                found => {
                    tracing::warn!(kid = %marker.kid, expired = found.is_some(), "marker kid not usable");
                    return Err(KeyringError::UnknownKid {
                        kid: marker.kid.clone(),
                    });
                }
            }
        };
        verify_record(key, MARKER_CONTEXT, &marker.fields, &marker.tag).map_err(|_| {
            KeyringError::BadMac {
                kid: marker.kid.clone(),
            }
        })
    }
}

/// One re-marking operation: re-sign the marker of `issue` (currently under `from_kid`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Remark {
    /// Issue identifier (number or node id) as the caller tracks it.
    pub issue: String,
    /// The kid the issue's marker is under now.
    pub from_kid: String,
}

/// Re-marking spread over runs: `runs[i]` is the work of run `i`, each within the budget.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct RotationPlan {
    /// Per-run operation lists.
    pub runs: Vec<Vec<Remark>>,
}

/// Plan rotation: every `(issue, kid)` not under the current kid becomes one [`Remark`],
/// chunked into runs of at most `budget_per_run` operations, in input order.
///
/// # Errors
/// [`KeyringError::ZeroBudget`] when `budget_per_run` is 0.
pub fn plan_rotation(
    ring: &Keyring,
    markers: &[(String, String)],
    budget_per_run: usize,
) -> Result<RotationPlan, KeyringError> {
    if budget_per_run == 0 {
        return Err(KeyringError::ZeroBudget);
    }
    let ops: Vec<Remark> = markers
        .iter()
        .filter(|(_, kid)| kid != ring.current_kid())
        .map(|(issue, kid)| Remark {
            issue: issue.clone(),
            from_kid: kid.clone(),
        })
        .collect();
    let runs: Vec<Vec<Remark>> = ops.chunks(budget_per_run).map(<[Remark]>::to_vec).collect();
    tracing::info!(
        ops = ops.len(),
        runs = runs.len(),
        budget_per_run,
        "rotation planned"
    );
    Ok(RotationPlan { runs })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(b: u8) -> MachineKey {
        MachineKey::from_bytes([b; 32])
    }

    fn fields() -> MarkerFields {
        MarkerFields {
            repo_node_id: "R_1".into(),
            ulid: "01ABC".into(),
            nonce: "n1".into(),
        }
    }

    fn ring() -> Keyring {
        Keyring::new("k2", key(2), vec![("k1".into(), key(1), 1000)]).unwrap()
    }

    #[test]
    fn verify_only_key_verifies_and_new_markers_use_current() {
        let old = Keyring::new("k1", key(1), vec![]).unwrap().sign(fields());
        let r = ring();
        assert!(r.verify(&old, 999).is_ok());
        assert_eq!(r.sign(fields()).kid, "k2");
    }

    // frob:tests crates/frob-mirror/src/keyring.rs::Keyring.from_env
    #[test]
    fn from_env_with_an_unset_variable_is_a_load_error_naming_the_kid() {
        let r = Keyring::from_env("k9", "FROB_MIRROR_TEST_KEY_THAT_IS_NEVER_SET", &[]);
        assert!(matches!(r, Err(KeyringError::Load { ref kid, .. }) if kid == "k9"));
    }

    #[test]
    fn key_past_verify_period_is_unknown_kid() {
        let old = Keyring::new("k1", key(1), vec![]).unwrap().sign(fields());
        assert!(matches!(
            ring().verify(&old, 1000),
            Err(KeyringError::UnknownKid { .. })
        ));
    }

    #[test]
    fn tampered_fields_fail_mac() {
        let r = ring();
        let mut m = r.sign(fields());
        m.fields.ulid = "01XYZ".into();
        assert!(matches!(r.verify(&m, 0), Err(KeyringError::BadMac { .. })));
    }

    #[test]
    fn rotation_is_budgeted_across_runs() {
        let r = ring();
        let markers: Vec<(String, String)> = (0..5)
            .map(|i| (format!("#{i}"), if i == 4 { "k2" } else { "k1" }.to_owned()))
            .collect();
        let plan = plan_rotation(&r, &markers, 3).unwrap();
        assert_eq!(plan.runs.len(), 2);
        assert_eq!(plan.runs[0].len(), 3);
        assert_eq!(plan.runs[1].len(), 1);
        assert!(matches!(
            plan_rotation(&r, &markers, 0),
            Err(KeyringError::ZeroBudget)
        ));
    }
}
