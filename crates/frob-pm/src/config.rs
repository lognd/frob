//! The `[pm]`, `[pm.wip]` and `[pm.classes]` config tables: the scrumban policies of `releases.md` section 2 as knobs.
//!
//! Every knob is materialized by `frob init` (architecture.md section 6), so a
//! repository sees its own process policy and nothing is silently inherited.
//! This module only declares and loads the knobs; the tickets that enforce them
//! (repository WIP limit, PM033 replenish, cycles) read [`PmConfig`].
// frob:ticket 01M4069R19D2KZENDGEH83JZSW

use std::fmt;
use std::path::Path;
use std::str::FromStr;

use gob_config::{ConfigError, ConfigTable};
use schemars::JsonSchema;
use serde::{Deserialize, Deserializer, Serialize};

/// The product whose `frob.toml` carries the tables.
const PRODUCT: &str = "frob";

/// Declare a closed set of knob names: serialization, schema, `FromStr` and a deserializer whose refusal names the nearest valid name.
macro_rules! knob_names {
    ($(#[$meta:meta])* $name:ident, $what:literal, { $($(#[$vmeta:meta])* $variant:ident => $text:literal),+ $(,)? }) => {
        $(#[$meta])*
        #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, JsonSchema)]
        pub enum $name {
            $($(#[$vmeta])* #[serde(rename = $text)] $variant),+
        }

        impl $name {
            /// Every known name, in declaration order.
            pub const ALL: &'static [Self] = &[$(Self::$variant),+];

            /// The name as written in `frob.toml`.
            pub const fn as_str(self) -> &'static str {
                match self { $(Self::$variant => $text),+ }
            }
        }

        impl fmt::Display for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(self.as_str())
            }
        }

        impl FromStr for $name {
            type Err = String;

            fn from_str(s: &str) -> Result<Self, String> {
                if let Some(v) = Self::ALL.iter().find(|v| v.as_str() == s) {
                    return Ok(*v);
                }
                tracing::warn!(kind = $what, name = s, "unknown pm config name");
                let known = Self::ALL.iter().map(|v| v.as_str()).collect::<Vec<_>>();
                let hint = nearest(s, &known)
                    .map_or_else(String::new, |n| format!("; did you mean `{n}`?"));
                Err(format!("unknown {} `{s}`{hint} (known: {})", $what, known.join(", ")))
            }
        }

        impl<'de> Deserialize<'de> for $name {
            fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
                let s = String::deserialize(d)?;
                s.parse().map_err(serde::de::Error::custom)
            }
        }
    };
}

/// The candidate within a sane edit distance of `name`, if any.
fn nearest(name: &str, candidates: &[&str]) -> Option<String> {
    let limit = (name.len() / 2).max(2);
    candidates
        .iter()
        .map(|c| (strsim::levenshtein(name, c), *c))
        .filter(|(d, _)| *d <= limit)
        .min_by_key(|(d, _)| *d)
        .map(|(_, c)| c.to_owned())
}

knob_names! {
    /// How work is assigned: only `rank` exists (pull from `doable`, highest rank first).
    Pull, "pull policy", {
        /// Take the highest-ranked doable ticket; nobody is assigned work they did not pull.
        Rank => "rank",
    }
}

knob_names! {
    /// A predicate of the definition of ready (checked on the move to `ready` and by `doable`).
    ReadyRequirement, "ready requirement", {
        /// The story carries a value statement, or the objective is qualified.
        StoryOrObjectiveQualified => "story_or_objective_qualified",
        /// At least one acceptance criterion exists.
        Criteria => "criteria",
        /// The ticket is sized.
        Points => "points",
        /// The ticket declares a scope.
        Scope => "scope",
        /// The ticket has a parent.
        Parent => "parent",
    }
}

knob_names! {
    /// A predicate of the definition of done (checked on close and land).
    DoneRequirement, "done requirement", {
        /// Every acceptance criterion is bound to passing evidence.
        CriteriaEvidenced => "criteria_evidenced",
        /// An objective ticket's measured target is met.
        ObjectiveTargetMet => "objective_target_met",
        /// Docs were touched, or the exception is recorded.
        DocsTouchedOrExcepted => "docs_touched_or_excepted",
        /// No child ticket is still open.
        NoOpenChildren => "no_open_children",
        /// A changelog fragment exists (REL003).
        ChangelogFragment => "changelog_fragment",
    }
}

impl DoneRequirement {
    /// The requirements enabled by default: the ones the close guard can evaluate today.
    pub const DEFAULT: &'static [Self] = &[
        Self::CriteriaEvidenced,
        Self::NoOpenChildren,
        Self::ChangelogFragment,
    ];
}

/// Scrumban policies: pull order, definitions of ready and done, cadence and capacity statistics.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "pm", materialize)]
pub struct PmTable {
    /// Strict process policy: PM rules that are warnings by default (PM001, PM002, PM013, PM034, PM036) become errors, so a repository can make its process gate-enforced; off by default so a fresh repository is only advised.
    #[config(default = false, enforcement)]
    pub strict: bool,
    /// Pull policy; `rank` takes the highest-ranked doable ticket, the only policy so far and the scrumban default.
    #[config(default = Pull::Rank, enforcement)]
    pub pull: Pull,
    /// Replenishment order point: PM033 advises planning when ready tickets fall below this (default twice the repository WIP limit, so the queue never starves a full WIP).
    #[config(default = 4, enforcement)]
    pub ready_min: u32,
    /// Definition of ready: predicates a ticket must satisfy to enter `ready`; the default is the full list of pm-enforcement.md section 3 so no ill-formed goal is pulled.
    #[config(default = ReadyRequirement::ALL.to_vec(), enforcement)]
    pub ready_requires: Vec<ReadyRequirement>,
    /// Definition of done: predicates checked on close and land; the default lists the three evaluable ones (`criteria_evidenced`, `no_open_children`, `changelog_fragment`); `docs_touched_or_excepted` and `objective_target_met` exist but refuse as Unresolved until they can be evaluated, so listing them is an explicit choice.
    #[config(default = DoneRequirement::DEFAULT.to_vec(), enforcement)]
    pub done_requires: Vec<DoneRequirement>,
    /// Days per cycle when a cycle is created without an explicit end; one week is the usual scrumban review cadence.
    #[config(default = 7, enforcement)]
    pub cycle_days: u32,
    /// Completed cycles needed before capacity and forecasts are enforced; below it they report Unresolved, so a fresh repository never needs an over-commit.
    #[config(default = 3, enforcement)]
    pub min_history: u32,
    /// Safety factor k in `capacity = rolling_mean - k * stddev` for cycle commitment; 0.5 trades a little throughput for commitments that are usually met.
    #[config(default = 0.5, enforcement)]
    pub capacity_k: f64,
    /// Sprint gate: while a cycle is active, `work` and `start` refuse a ticket that is not a member of it (`E-PM-NOT-IN-CYCLE`) unless it is expedite or started with `--unplanned --reason`, which assigns it to the cycle as a recorded over-commit; with no active cycle the gate is silent, so it defaults on.
    #[config(default = true, enforcement)]
    pub sprint_gate: bool,
}

/// Work-in-progress limits (`[pm.wip]`); 0 turns a limit off.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "pm.wip", materialize)]
pub struct PmWipTable {
    /// Most tickets one holder (actor plus worktree path) may have in progress; 1 makes an agent finish before starting another, 0 is off.
    #[config(default = 1, enforcement)]
    pub in_progress_per_identity: u32,
    /// Most tickets in progress in the repository at once, sized to what the machine can build; the default 2 matches the two-builder rule, and 0 is off.
    #[config(default = 2, enforcement)]
    pub in_progress: u32,
}

/// Classes of service (`[pm.classes]`).
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "pm.classes", materialize)]
pub struct PmClassesTable {
    /// Expedite tickets that may exceed the repository WIP limit at once; 1 lets one critical fix through without opening the floodgates.
    #[config(default = 1, enforcement)]
    pub expedite_max: u32,
    /// Largest share (0.0 to 1.0) of a cycle's points that intangible work (chores, debt) may take, checked by PM035; 0.2 keeps upkeep from crowding out features.
    #[config(default = 0.2, enforcement)]
    pub intangible_share: f64,
}

/// Every pm table, loaded and validated from one `frob.toml`; the value later tickets consume.
#[derive(Debug, Clone, Default)]
pub struct PmConfig {
    /// `[pm]`.
    pub pm: PmTable,
    /// `[pm.wip]`.
    pub wip: PmWipTable,
    /// `[pm.classes]`.
    pub classes: PmClassesTable,
}

impl PmConfig {
    /// Load `[pm]`, `[pm.wip]` and `[pm.classes]` from `<root>/frob.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, an unknown key or requirement name (with a did-you-mean) or a mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        let cfg = Self {
            pm: gob_config::load::<PmTable>(root, PRODUCT)?.value,
            wip: gob_config::load::<PmWipTable>(root, PRODUCT)?.value,
            classes: gob_config::load::<PmClassesTable>(root, PRODUCT)?.value,
        };
        tracing::debug!(root = %root.display(), "pm config loaded");
        Ok(cfg)
    }

    /// Like [`PmConfig::load`], but the repository-wide tables (`[pm]`, `[pm.wip]`, `[pm.classes]`) come from `<rev>:frob.toml` when that blob exists, so a branch cut before a limit changed enforces the current value; a missing blob or unreadable `rev` keeps the file in `root`.
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable or invalid file in `root` or an invalid blob at `rev`.
    // frob:ticket 01M4GWKEMB266C6GTFEP4R3G7W
    pub fn load_repo_wide(root: &Path, rev: &str) -> Result<Self, ConfigError> {
        let local = Self::load(root)?;
        let Some(text) = blob_at(root, rev) else {
            return Ok(local);
        };
        let label = Path::new(rev);
        let cfg = Self {
            pm: gob_config::load_str::<PmTable>(&text, label)?.value,
            wip: gob_config::load_str::<PmWipTable>(&text, label)?.value,
            classes: gob_config::load_str::<PmClassesTable>(&text, label)?.value,
        };
        tracing::debug!(rev, "pm config read from the base ref");
        Ok(cfg)
    }
}

/// The text of `frob.toml` at `rev` in the repository containing `root`, or `None` (logged) when the ref or blob is unavailable.
// frob:ticket 01M4GWKEMB266C6GTFEP4R3G7W
fn blob_at(root: &Path, rev: &str) -> Option<String> {
    let repo = gob_git::Repo::discover(root).ok()?;
    match repo.read_blob_at(rev, "frob.toml") {
        Ok(Some(bytes)) => String::from_utf8(bytes).ok(),
        Ok(None) => None,
        Err(e) => {
            tracing::debug!(rev, error = %e, "base-ref frob.toml unavailable; using the worktree copy");
            None
        }
    }
}
