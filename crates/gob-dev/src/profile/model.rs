//! The `report.json` schema of `cargo dev profile` and the budget verdicts over it.

use serde::{Deserialize, Serialize};

/// Version of the `report.json` layout; bump when a field changes meaning.
pub const SCHEMA_VERSION: u32 = 1;

/// One profile run: where it ran, how it was configured and one [`Entry`] per leaf command.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Report {
    /// Layout version ([`SCHEMA_VERSION`]).
    pub schema_version: u32,
    /// Operating system the run measured (`linux`).
    pub os: String,
    /// CPU architecture the run measured (`aarch64`).
    pub arch: String,
    /// Cargo profile the binaries were built with.
    pub cargo_profile: String,
    /// Commit the throwaway clone was taken at, when known.
    pub commit: Option<String>,
    /// Warm runs timed per command.
    pub runs: u32,
    /// Multiplier applied to every budget in this run (slow runners use more than 1).
    pub budget_factor: f64,
    /// One entry per leaf command, sorted by command.
    pub entries: Vec<Entry>,
}

/// The measurement (or the skip) of one leaf command.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Entry {
    /// Leaf command, product first (`frob ticket show`).
    pub command: String,
    /// Arguments the scenario passed (empty for a skipped leaf).
    pub args: Vec<String>,
    /// Fixture the scenario ran in (`repo` or `tmp`), absent for a skipped leaf.
    pub fixture: Option<String>,
    /// Why the leaf was not measured, when it was not.
    pub skipped: Option<String>,
    /// Exit code of the last warm run.
    pub exit: Option<i32>,
    /// Whether every run exited with a code the scenario allows.
    pub exit_ok: bool,
    /// Median warm wall time in milliseconds.
    pub warm_ms: Option<f64>,
    /// Every warm sample in milliseconds, in run order.
    pub samples_ms: Vec<f64>,
    /// Wall time of the first run after deleting `.frob/`, when the scenario sets `cold`.
    pub cold_ms: Option<f64>,
    /// Peak resident set of one run in KiB (Linux only).
    pub max_rss_kib: Option<u64>,
    /// Absolute warm budget in milliseconds, before the budget factor.
    pub budget_ms: Option<u64>,
    /// Absolute cold budget in milliseconds, before the budget factor.
    pub cold_budget_ms: Option<u64>,
    /// The `--timing` stage tree the verb printed, when the scenario asks for it.
    pub timing: Option<serde_json::Value>,
}

impl Entry {
    /// A skipped leaf: named in the report so the table is complete, never measured.
    pub fn skipped(command: &str, reason: &str) -> Self {
        Self {
            command: command.to_owned(),
            args: Vec::new(),
            fixture: None,
            skipped: Some(reason.to_owned()),
            exit: None,
            exit_ok: true,
            warm_ms: None,
            samples_ms: Vec::new(),
            cold_ms: None,
            max_rss_kib: None,
            budget_ms: None,
            cold_budget_ms: None,
            timing: None,
        }
    }
}

/// Every way `report` breaks its scenarios, one human line each naming the command, the measured
/// value and the budget (already multiplied by the report's factor).
pub fn violations(report: &Report) -> Vec<String> {
    let mut out = Vec::new();
    for e in &report.entries {
        if e.skipped.is_some() {
            continue;
        }
        if !e.exit_ok {
            out.push(format!(
                "{}: exited {} which the scenario does not allow",
                e.command,
                e.exit
                    .map_or_else(|| "by signal".to_owned(), |c| c.to_string())
            ));
        }
        let over = |what: &str, measured: Option<f64>, budget: Option<u64>| {
            let (m, b) = (measured?, budget?);
            #[allow(
                clippy::cast_precision_loss,
                reason = "budgets are small millisecond counts, far below 2^52"
            )]
            let limit = b as f64 * report.budget_factor;
            (m > limit).then(|| {
                format!(
                    "{}: {what} {m:.0} ms exceeds the budget {limit:.0} ms ({b} ms x {})",
                    e.command, report.budget_factor
                )
            })
        };
        out.extend(over("warm median", e.warm_ms, e.budget_ms));
        out.extend(over("cold run", e.cold_ms, e.cold_budget_ms));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn entry(warm: f64, budget: u64) -> Entry {
        Entry {
            command: "frob check".to_owned(),
            warm_ms: Some(warm),
            budget_ms: Some(budget),
            exit: Some(0),
            ..Entry::skipped("frob check", "")
        }
        .measured()
    }

    impl Entry {
        fn measured(mut self) -> Self {
            self.skipped = None;
            self
        }
    }

    fn report(entries: Vec<Entry>, factor: f64) -> Report {
        Report {
            schema_version: SCHEMA_VERSION,
            os: "linux".to_owned(),
            arch: "aarch64".to_owned(),
            cargo_profile: "profiling".to_owned(),
            commit: None,
            runs: 5,
            budget_factor: factor,
            entries,
        }
    }

    // frob:tests crates/gob-dev/src/profile/model.rs::violations
    #[test]
    fn over_budget_names_command_measured_and_budget() {
        let v = violations(&report(vec![entry(1500.0, 1000)], 1.0));
        assert_eq!(v.len(), 1, "{v:?}");
        assert!(v[0].contains("frob check"), "{}", v[0]);
        assert!(v[0].contains("1500 ms"), "{}", v[0]);
        assert!(v[0].contains("1000 ms"), "{}", v[0]);
    }

    // frob:tests crates/gob-dev/src/profile/model.rs::violations
    #[test]
    fn budget_factor_scales_the_limit() {
        assert!(violations(&report(vec![entry(1500.0, 1000)], 2.0)).is_empty());
        assert_eq!(violations(&report(vec![entry(2500.0, 1000)], 2.0)).len(), 1);
    }

    // frob:tests crates/gob-dev/src/profile/model.rs::violations
    #[test]
    fn unexpected_exit_and_skips() {
        let mut bad = entry(1.0, 1000);
        bad.exit = Some(4);
        bad.exit_ok = false;
        let v = violations(&report(
            vec![bad, Entry::skipped("frob land", "needs a remote")],
            1.0,
        ));
        assert_eq!(v.len(), 1, "{v:?}");
        assert!(v[0].contains("exited 4"), "{}", v[0]);
    }
}
