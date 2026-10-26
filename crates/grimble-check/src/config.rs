//! The `grimble.toml` tables owned by grimble: `[compute]`, `[packs]` and `[grimble]`.
//!
//! `[check]` and `[perf]` belong to `gob-check`. The pack tables are accepted and
//! validated here (packs.md 3.6); repository packs load atoms only (see `packs`), and a run that enables anything else says so.

// frob:ticket 01M41H9Y7TTWDN6DAQ5C06R6B7
// frob:ticket 01M4FGXVQTN5NJ0JBGWAMVHK82
// frob:ticket 01M4H4WTSTB7X4A6STFEF8K8S3
// frob:ticket 01M5HJ075VJZAP88EVTCX1MH8C
// frob:ticket 01M5FSSDC7EG5QA70CRABC8SMA
// frob:ticket 01M5HMKRFRZYFQC6HVNPHC3Z2P

use std::collections::BTreeMap;
use std::path::Path;

use gob_config::{ConfigError, ConfigTable};
use gob_rules::Severity;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Product name, the stem of `grimble.toml` and of the `.grimble/` state directory.
pub const PRODUCT: &str = "grimble";

pub use gob_config::{ComputeTable, blake3_tagged, compute_digest};

/// One `[[packs.external]]` entry (packs.md 3.4): a pack fetched once and vendored.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ExternalPack {
    /// Pack id, `ext/NAME`.
    pub id: String,
    /// `https` URL the pack is fetched from.
    pub url: String,
    /// The pack digest the author expects (`blake3:...`).
    pub digest: String,
}

/// Which data packs the repository enables (packs.md 3.6). Only `local/` packs (atoms) load; external packs and PACK rules do not yet.
#[derive(Debug, Clone, PartialEq, Eq, ConfigTable)]
#[config(table = "packs", materialize)]
pub struct PacksTable {
    /// Enabled pack ids in load order.
    #[config(default = Vec::new(), enforcement)]
    pub enabled: Vec<String>,
    /// Path of the pack lock, relative to the repository root.
    #[config(default = "grimble.packs.lock".to_owned(), enforcement)]
    pub lock: String,
    /// External packs (`[[packs.external]]`).
    #[config(default = Vec::new())]
    pub external: Vec<ExternalPack>,
    /// Repository severity overrides by atom then rule (`[packs.severity]`).
    #[config(default = std::collections::BTreeMap::new())]
    pub severity: std::collections::BTreeMap<String, std::collections::BTreeMap<String, String>>,
}

impl PacksTable {
    /// Load `[packs]` from `<root>/grimble.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, PRODUCT)?.value)
    }

    /// True when the repository asks for packs this build does not load: external packs and
    /// enabled ids outside the `local/` repository packs (a built-in is only partly compiled in).
    pub fn requests_packs(&self) -> bool {
        !self.external.is_empty() || self.enabled.iter().any(|id| !id.starts_with("local/"))
    }
}

/// The `[coh]` table: project overrides for COH002 ("decision with effects") and COH003 ("mixed abstraction levels").
///
/// The language adapter's effects capability decides by default (a call through `fs`, `os`,
/// `subprocess` is an effect, `console.log` is not). A configured list adds to it and matches on
/// the callee's last path segment in any language, so `a.b.send` is `send`: `effect_calls` marks
/// a name as an effect, `trivial` as never one, and a name in both is trivial. Both default to
/// empty. A call the capability cannot place leaves the verdict Unresolved until it is listed.
/// `max_level_spread` is the COH003 threshold: callees further apart than that many layers fire.
#[derive(Debug, Clone, PartialEq, Eq, ConfigTable)]
#[config(table = "coh")]
pub struct CohTable {
    /// Extra callee names that perform an effect (IO, messaging, persistence) when called inside a decision.
    #[config(default = crate::coh002::default_effect_calls())]
    pub effect_calls: Vec<String>,
    /// Extra callee names that are trivial (logging, metrics, asserts) and never count as an effect.
    #[config(default = crate::coh002::default_trivial())]
    pub trivial: Vec<String>,
    /// The largest layer distance between a unit's callees that COH003 still accepts as one level of abstraction.
    #[config(default = u64::from(crate::coh003::DEFAULT_MAX_LEVEL_SPREAD))]
    pub max_level_spread: u64,
}

impl CohTable {
    /// Load `[coh]` from `<root>/grimble.toml` (a missing file or table means no overrides).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, PRODUCT)?.value)
    }
}

/// The warning printed when packs are requested but not loaded.
pub const PACKS_NOT_LOADED: &str = "packs are enabled in grimble.toml but this build loads only local/ packs (atoms); external packs, the lock and PACK rules are not evaluated";

/// The conventional model root `grimble init` seeds and the `models` knob defaults to.
pub const DEFAULT_MODEL_ROOT: &str = "design/model.grmb";

/// The `[grimble]` table: model roots and binding policy (grmb-spec 3, binding.md 6).
#[derive(Debug, Clone, PartialEq, Eq, ConfigTable)]
#[config(table = "grimble", materialize)]
pub struct GrimbleTable {
    /// Root `.grmb` files, one independent model each; only files reachable from them through
    /// `include` are loaded (MDL019 names the rest, MDL021 fires when none is declared).
    #[config(default = vec![DEFAULT_MODEL_ROOT.to_owned()], enforcement)]
    pub models: Vec<String>,
    /// Selectors whose public units must have an owner (SYS005); empty turns the rule off.
    #[config(default = Vec::new())]
    pub modeled: Vec<String>,
    /// Warn rules SYS001 and SYS005 become Errors.
    #[config(default = false)]
    pub strict: bool,
    /// A Body with fewer tokens than this cannot be paired as a rename (binding.md 5.4 item 3).
    #[config(default = 12_u64)]
    pub rename_min_tokens: u64,
    /// A function, method or type longer than this many lines fires LARGE001; 0 turns the rule off.
    #[config(default = 400_u64)]
    pub large_lines: u64,
    /// Tokens a window needs to count as a DUP001 clone; 0 turns the rule off.
    #[config(default = grimble_arch::DUP_MIN_TOKENS)]
    pub dup_min_tokens: u64,
    /// Disjoint copies a block needs before DUP001 fires; below 2 turns the rule off.
    #[config(default = grimble_arch::DUP_MIN_OCCURRENCES)]
    pub dup_min_occurrences: u64,
}

impl GrimbleTable {
    /// Load `[grimble]` from `<root>/grimble.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, PRODUCT)?.value)
    }
}

/// The ledger directory of `frob.toml` (`[tickets] dir`), the one frob-owned path that is configurable.
///
/// Read straight from the shared file (grimble links no frob crate); a missing or unreadable
/// file, table or key, or a non-string value, gives [`grimble_bind::frob_owned::DEFAULT_LEDGER_DIR`].
pub fn ledger_dir(root: &Path) -> String {
    gob_config::ledger_dir(root)
}

/// The severity tokens `[rules.<id>] severity` accepts; `Unresolved` is a state, not a setting.
const SEVERITY_TOKENS: [(&str, Severity); 3] = [
    ("advisory", Severity::Advisory),
    ("warn", Severity::Warn),
    ("error", Severity::Error),
];

/// The `[rules.<id>]` severity overrides of `grimble.toml`, by rule id.
///
/// `[rules]` is shared with the other products reading the same file, so it is not a
/// `ConfigTable`: an id grimble does not register and a key other than `severity` are ignored
/// here (the first is logged), while a `severity` that is not `advisory`, `warn` or `error`
/// is a hard error. An override replaces the rule default and `[grimble] strict`, and never
/// turns an `Unresolved` finding into a decided one.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RuleOverrides {
    /// Severity by rule id.
    pub severity: BTreeMap<String, Severity>,
}

impl RuleOverrides {
    /// Read `[rules.<id>]` from the walked `grimble.toml` content `read` (a missing file means no overrides).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, a non-table `[rules]` entry or an
    /// invalid severity.
    pub fn load(root: &Path, read: std::io::Result<String>) -> Result<Self, ConfigError> {
        match read {
            Ok(text) => Self::parse(&text, &root.join(format!("{PRODUCT}.toml"))),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(Self::default()),
            Err(source) => Err(ConfigError::Io {
                path: root.join(format!("{PRODUCT}.toml")),
                source,
            }),
        }
    }

    /// Parse the `[rules]` table of TOML `text` labelled `label`.
    ///
    /// # Errors
    ///
    /// As [`RuleOverrides::load`], minus the file read.
    pub fn parse(text: &str, label: &Path) -> Result<Self, ConfigError> {
        let doc = text
            .parse::<toml::Table>()
            .map_err(|e| ConfigError::Parse {
                path: label.to_owned(),
                message: e.to_string(),
            })?;
        let mut out = Self::default();
        let Some(rules) = doc.get("rules") else {
            return Ok(out);
        };
        let invalid = |message: String| ConfigError::Invalid {
            table: "rules".to_owned(),
            message,
        };
        let toml::Value::Table(rules) = rules else {
            return Err(invalid("expected a table of `[rules.<id>]`".to_owned()));
        };
        for (id, entry) in rules {
            if id == "ramp" {
                // `[rules] ramp = bool` is the ramp-in switch (gob-rules), not a rule.
                continue;
            }
            let toml::Value::Table(entry) = entry else {
                return Err(invalid(format!("`{id}` must be a table `[rules.{id}]`")));
            };
            let Some(value) = entry.get("severity") else {
                continue;
            };
            let token = value
                .as_str()
                .ok_or_else(|| invalid(format!("`{id}.severity` must be a string")))?;
            let severity = SEVERITY_TOKENS
                .iter()
                .find(|(t, _)| *t == token)
                .map(|(_, s)| *s)
                .ok_or_else(|| {
                    invalid(format!(
                        "`{id}.severity` is `{token}`; expected `advisory`, `warn` or `error`"
                    ))
                })?;
            tracing::debug!(rule = %id, ?severity, "rule severity override read");
            out.severity.insert(id.clone(), severity);
        }
        Ok(out)
    }

    /// Rewrite the severity of every decided finding whose rule is overridden; returns how many changed.
    pub fn apply(&self, findings: &mut [gob_rules::Finding]) -> usize {
        if self.severity.is_empty() {
            return 0;
        }
        let mut changed = 0;
        for f in findings {
            if f.severity == Severity::Unresolved {
                continue;
            }
            if let Some(&to) = self.severity.get(f.rule.as_str())
                && f.severity != to
            {
                f.severity = to;
                changed += 1;
            }
        }
        tracing::info!(changed, "rule severity overrides applied");
        changed
    }

    /// Ids of overrides that name no rule in `known`, for a log line (the file is shared across products).
    pub fn unknown_ids(&self, known: impl Fn(&str) -> bool) -> Vec<&str> {
        self.severity
            .keys()
            .map(String::as_str)
            .filter(|id| !known(id))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse(text: &str) -> Result<RuleOverrides, ConfigError> {
        RuleOverrides::parse(text, Path::new("grimble.toml"))
    }

    // frob:tests RuleOverrides.parse
    #[test]
    fn parse_reads_each_severity_and_skips_entries_without_one() {
        let got = parse(
            "[rules.A001]\nseverity = \"error\"\n[rules.B001]\nseverity = \"warn\"\n[rules.C001]\nseverity = \"advisory\"\n[rules.D001]\ndisabled = true\n",
        )
        .unwrap();
        assert_eq!(got.severity.len(), 3);
        assert_eq!(got.severity["A001"], Severity::Error);
        assert_eq!(got.severity["C001"], Severity::Advisory);
    }

    // frob:tests RuleOverrides.parse
    #[test]
    fn parse_rejects_bad_tokens_and_shapes() {
        for bad in [
            "[rules.A001]\nseverity = \"unresolved\"\n",
            "[rules.A001]\nseverity = 3\n",
            "[rules]\nA001 = \"error\"\n",
            "rules = 1\n",
        ] {
            assert!(parse(bad).is_err(), "{bad}");
        }
        assert_eq!(parse("[check]\n").unwrap(), RuleOverrides::default());
    }

    // frob:tests RuleOverrides.unknown_ids
    #[test]
    fn unknown_ids_names_only_unregistered_overrides() {
        let o = parse("[rules.A001]\nseverity = \"error\"\n[rules.Z999]\nseverity = \"warn\"\n")
            .unwrap();
        assert_eq!(o.unknown_ids(|id| id == "A001"), ["Z999"]);
    }

    // frob:tests RuleOverrides.load
    #[test]
    fn load_treats_a_missing_file_as_no_overrides() {
        let missing = Err(std::io::ErrorKind::NotFound.into());
        let got = RuleOverrides::load(Path::new("."), missing).unwrap();
        assert_eq!(got, RuleOverrides::default());
        let denied = Err(std::io::ErrorKind::PermissionDenied.into());
        assert!(RuleOverrides::load(Path::new("."), denied).is_err());
    }
}
