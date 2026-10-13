//! Effect classes and exact grants (security.md 2.6, I6, I8, I10).
//!
//! Effects fall into four classes: ordinary, secret-shaped, control plane and
//! privilege. A [`Grant`] names one effect and one scope; a secret-shaped
//! path is only ever satisfied by the separate `fs.read.secret-shaped`
//! effect, never by a glob such as `**`, and control-plane writes are never
//! satisfied by a plain `fs.write` glob. `.git/**`, the trust store and
//! caches are refused at parse time.

mod glob;

use thiserror::Error;

/// The four effect classes of security.md 2.6.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EffectClass {
    /// Declared exactly and trusted per 2.3.
    Ordinary,
    /// Separate named effect, never implied by a glob.
    SecretShaped,
    /// Control-plane writes, never satisfied by a glob or CI trust.
    ControlPlane,
    /// `replaces`, `fix.machine`, `subprocess`.
    Privilege,
}

/// Why a grant could not be parsed.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum EffectError {
    /// The effect name is not one this crate knows.
    #[error("unknown effect `{0}`")]
    UnknownEffect(String),
    /// The scope falls in a region no grant may cover.
    #[error("scope `{0}` is not grantable")]
    NotGrantable(String),
}

/// Classify an effect name (`fs.read`, `fs.write.control`, ...).
#[must_use]
pub fn classify(effect: &str) -> Option<EffectClass> {
    match effect {
        "fs.read" | "fs.write" | "env" | "net" => Some(EffectClass::Ordinary),
        "fs.read.secret-shaped" | "env.secret" => Some(EffectClass::SecretShaped),
        "fs.write.control" => Some(EffectClass::ControlPlane),
        "replaces" | "fix.machine" | "subprocess" => Some(EffectClass::Privilege),
        _ => None,
    }
}

/// Case-insensitive extension test.
fn has_ext(name: &str, ext: &str) -> bool {
    std::path::Path::new(name)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case(ext))
}

/// True when the path (slash-separated, repo-relative) is secret-shaped.
#[must_use]
pub fn is_secret_path(path: &str) -> bool {
    let name = path.rsplit('/').next().unwrap_or(path);
    name == ".env"
        || name.starts_with(".env.")
        || has_ext(name, "pem")
        || has_ext(name, "key")
        || name.starts_with("id_")
        || matches!(name, ".npmrc" | ".pypirc" | ".netrc")
}

/// True when the environment variable name is secret-shaped.
#[must_use]
pub fn is_secret_env(name: &str) -> bool {
    const CONTAINS: [&str; 4] = ["TOKEN", "SECRET", "KEY", "PASSWORD"];
    const PREFIX: [&str; 5] = ["ACTIONS_", "AWS_", "AZURE_", "GOOGLE_", "NPM_"];
    CONTAINS.iter().any(|c| name.contains(c))
        || PREFIX.iter().any(|p| name.starts_with(p))
        || name.starts_with("CARGO_REGISTRY_")
        || name == "SSH_AUTH_SOCK"
}

/// True when the path is control plane (writes need `fs.write.control`).
#[must_use]
pub fn is_control_path(path: &str) -> bool {
    let name = path.rsplit('/').next().unwrap_or(path);
    path == ".git"
        || path.starts_with(".git/")
        || path.starts_with("packs/")
        || path.starts_with(".github/workflows/")
        || path.starts_with(".gob/")
        || matches!(name, "grimble.toml" | "frob.toml" | "CODEOWNERS")
        || has_ext(name, "lock")
}

/// True when no grant may ever cover this scope (.git, trust store, caches).
fn is_ungrantable(scope: &str) -> bool {
    let s = scope.trim_start_matches("./");
    s == ".git"
        || s.starts_with(".git/")
        || s.starts_with(".gob/trust")
        || s.starts_with(".gob/cache")
        || s.starts_with(".frob/cache")
        || s.starts_with(".grimble/cache")
}

/// One exact, least-privilege, expiring grant.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Grant {
    effect: String,
    scope: String,
    expires: Option<u64>,
}

impl Grant {
    /// Parse a grant, refusing unknown effects and ungrantable scopes.
    ///
    /// # Errors
    /// [`EffectError::UnknownEffect`] or [`EffectError::NotGrantable`].
    pub fn parse(effect: &str, scope: &str, expires: Option<u64>) -> Result<Self, EffectError> {
        let class = classify(effect).ok_or_else(|| {
            tracing::warn!(effect, "refusing grant: unknown effect");
            EffectError::UnknownEffect(effect.to_owned())
        })?;
        if class == EffectClass::ControlPlane && is_ungrantable(scope) {
            tracing::warn!(effect, scope, "refusing grant: scope is not grantable");
            return Err(EffectError::NotGrantable(scope.to_owned()));
        }
        tracing::debug!(effect, scope, ?expires, "grant parsed");
        Ok(Self {
            effect: effect.to_owned(),
            scope: scope.to_owned(),
            expires,
        })
    }

    /// The effect name this grant covers.
    #[must_use]
    pub fn effect(&self) -> &str {
        &self.effect
    }

    /// Whether the grant has expired at unix time `now`.
    #[must_use]
    pub fn expired(&self, now: u64) -> bool {
        self.expires.is_some_and(|e| now >= e)
    }

    /// Whether this grant permits `effect` on `path` at unix time `now`.
    ///
    /// The effect is matched exactly; the required effect is promoted to
    /// the secret-shaped or control-plane variant when the path demands it,
    /// so a broad `fs.read` of `**` never covers `.env`.
    #[must_use]
    pub fn permits(&self, effect: &str, path: &str, now: u64) -> bool {
        if self.expired(now) {
            return false;
        }
        let needed = match effect {
            "fs.read" if is_secret_path(path) => "fs.read.secret-shaped",
            "fs.write" if is_control_path(path) => "fs.write.control",
            other => other,
        };
        let ok = self.effect == needed && glob::matches(&self.scope, path);
        tracing::debug!(needed, path, ok, "grant evaluated");
        ok
    }
}

/// Whether any grant in `grants` permits `effect` on `path` at `now`.
#[must_use]
pub fn permitted(grants: &[Grant], effect: &str, path: &str, now: u64) -> bool {
    grants.iter().any(|g| g.permits(effect, path, now))
}
