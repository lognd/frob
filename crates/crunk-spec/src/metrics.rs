//! Post-launch artifacts: `design/metrics/*.toml` (one HEART metric per file) and
//! `design/experiments/*.toml` (one experiment per file). Parsing is pure; [`load_metrics`] reads
//! a project and reports each bad file as a located problem and refuses a repeated id.

// frob:ticket 01M5XCZ1C4P58PFPRCH880G1HE

use std::collections::BTreeSet;
use std::path::Path;

use serde::Deserialize;

use crate::research::{Date, ResearchError, ResearchProblem, parse_toml};

/// Directory holding metric files, relative to the project root.
pub const METRICS_DIR: &str = "design/metrics";
/// Directory holding experiment files, relative to the project root.
pub const EXPERIMENTS_DIR: &str = "design/experiments";

/// One of the five HEART categories.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Heart {
    /// Satisfaction, as measured by surveys.
    Happiness,
    /// How much users interact.
    Engagement,
    /// New users of a feature.
    Adoption,
    /// Users who come back.
    Retention,
    /// Efficiency, effectiveness and error rate.
    TaskSuccess,
}

/// One HEART metric (`design/metrics/<id>.toml`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Metric {
    /// The metric's unique id.
    pub id: String,
    /// The HEART category.
    pub heart: Heart,
    /// The goal this metric tracks, when it tracks one.
    #[serde(default)]
    pub goal: Option<String>,
    /// The flow step this metric instruments, when it instruments one.
    #[serde(default)]
    pub step: Option<String>,
    /// The analytics event the metric reads.
    #[serde(default)]
    pub event: Option<String>,
}

/// The on-disk shape of an experiment, before its date is parsed.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RawExperiment {
    id: String,
    component: String,
    #[serde(default)]
    variants: Vec<String>,
    started: String,
    max_age_days: i64,
    #[serde(default)]
    guardrail: Option<String>,
}

/// One experiment (`design/experiments/<id>.toml`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Experiment {
    /// The experiment's unique id.
    pub id: String,
    /// The component whose variants are compared.
    pub component: String,
    /// The variants under test.
    pub variants: Vec<String>,
    /// The day the experiment started.
    pub started: Date,
    /// How many days it may run before it is stale.
    pub max_age_days: i64,
    /// The guardrail metric id, when one is named.
    pub guardrail: Option<String>,
}

/// Parse one metric file.
///
/// # Errors
/// [`ResearchError`] for invalid TOML, an unknown HEART category or the wrong schema.
pub fn parse_metric(text: &str) -> Result<Metric, ResearchError> {
    parse_toml(text)
}

/// Parse one experiment file; `started` must be `YYYY-MM-DD`.
///
/// # Errors
/// [`ResearchError`] for invalid TOML, the wrong schema or a malformed date.
pub fn parse_experiment(text: &str) -> Result<Experiment, ResearchError> {
    let raw: RawExperiment = parse_toml(text)?;
    let started = Date::parse(&raw.started).ok_or_else(|| ResearchError {
        line: None,
        message: format!("`started` must be YYYY-MM-DD, got `{}`", raw.started),
    })?;
    Ok(Experiment {
        id: raw.id,
        component: raw.component,
        variants: raw.variants,
        started,
        max_age_days: raw.max_age_days,
        guardrail: raw.guardrail,
    })
}

/// Everything loaded from a project's metrics and experiments; each list is sorted by path.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct MetricSet {
    /// Metrics with their paths.
    pub metrics: Vec<(String, Metric)>,
    /// Experiments with their paths.
    pub experiments: Vec<(String, Experiment)>,
    /// Files that were unreadable, invalid or repeated an id.
    pub problems: Vec<ResearchProblem>,
}

impl MetricSet {
    /// True when no metric or experiment file exists (problems aside).
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.metrics.is_empty() && self.experiments.is_empty()
    }
}

/// Load every `.toml` in `<root>/<dir>`, keeping valid files and refusing a repeated id.
fn load_kind<T>(
    root: &Path,
    dir: &str,
    parse: fn(&str) -> Result<T, ResearchError>,
    id_of: fn(&T) -> &str,
    problems: &mut Vec<ResearchProblem>,
) -> Vec<(String, T)> {
    let Ok(entries) = std::fs::read_dir(root.join(dir)) else {
        tracing::debug!(dir, "no metrics directory");
        return Vec::new();
    };
    let mut names: Vec<String> = entries
        .filter_map(Result::ok)
        .filter_map(|e| e.file_name().into_string().ok())
        .filter(|n| Path::new(n).extension().is_some_and(|x| x == "toml"))
        .collect();
    names.sort();
    let mut seen = BTreeSet::new();
    let mut out = Vec::new();
    for name in names {
        let path = format!("{dir}/{name}");
        let mut refuse = |message: String, line| {
            tracing::warn!(%path, %message, "metrics file rejected");
            problems.push(ResearchProblem {
                path: path.clone(),
                line,
                message,
            });
        };
        let text = match std::fs::read_to_string(root.join(&path)) {
            Ok(t) => t,
            Err(err) => {
                refuse(format!("unreadable: {err}"), None);
                continue;
            }
        };
        match parse(&text) {
            Ok(item) if seen.insert(id_of(&item).to_owned()) => out.push((path.clone(), item)),
            Ok(item) => refuse(format!("duplicate id `{}`", id_of(&item)), None),
            Err(e) => refuse(e.message, e.line),
        }
    }
    out
}

/// Read every metric and experiment under `root`. A missing directory contributes nothing; a bad
/// file becomes a [`ResearchProblem`] and a repeated id within a kind is refused.
#[must_use]
pub fn load_metrics(root: &Path) -> MetricSet {
    let mut problems = Vec::new();
    let metrics = load_kind(root, METRICS_DIR, parse_metric, |m| &m.id, &mut problems);
    let experiments = load_kind(
        root,
        EXPERIMENTS_DIR,
        parse_experiment,
        |x| &x.id,
        &mut problems,
    );
    tracing::debug!(
        metrics = metrics.len(),
        experiments = experiments.len(),
        problems = problems.len(),
        "loaded metrics"
    );
    MetricSet {
        metrics,
        experiments,
        problems,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/crunk-spec/src/metrics.rs::parse_metric
    #[test]
    fn metric_parses() {
        let m = parse_metric("id = \"m\"\nheart = \"task-success\"\nevent = \"e\"\n").expect("ok");
        assert_eq!(m.heart, Heart::TaskSuccess);
    }

    // frob:tests crates/crunk-spec/src/metrics.rs::parse_metric
    #[test]
    fn unknown_heart_category_is_rejected() {
        assert!(parse_metric("id = \"m\"\nheart = \"joy\"\n").is_err());
    }

    // frob:tests crates/crunk-spec/src/metrics.rs::parse_experiment
    #[test]
    fn experiment_parses() {
        let text = "id = \"x\"\ncomponent = \"button\"\nvariants = [\"a\"]\nstarted = \"2026-01-02\"\nmax_age_days = 30\n";
        assert_eq!(parse_experiment(text).expect("ok").max_age_days, 30);
    }

    // frob:tests crates/crunk-spec/src/metrics.rs::parse_experiment
    #[test]
    fn bad_start_date_is_rejected() {
        let text = "id = \"x\"\ncomponent = \"b\"\nstarted = \"soon\"\nmax_age_days = 1\n";
        assert!(parse_experiment(text).is_err());
    }

    // frob:tests crates/crunk-spec/src/metrics.rs::load_metrics
    #[test]
    fn load_tolerates_empty_and_refuses_duplicate_ids() {
        let dir = tempfile::tempdir().expect("tmp");
        assert!(load_metrics(dir.path()).is_empty());
        let p = dir.path().join(METRICS_DIR);
        std::fs::create_dir_all(&p).expect("mk");
        std::fs::write(p.join("a.toml"), "id = \"x\"\nheart = \"retention\"\n").expect("w");
        std::fs::write(p.join("b.toml"), "id = \"x\"\nheart = \"adoption\"\n").expect("w");
        let set = load_metrics(dir.path());
        assert_eq!(set.metrics.len(), 1);
        assert_eq!(set.problems.len(), 1);
    }
}
