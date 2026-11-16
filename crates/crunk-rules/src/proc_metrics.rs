//! The post-launch checks (live phase only): every flow step needs an analytics event, every
//! experiment variant must be a declared component variant, every experiment needs a guardrail
//! metric and must not outlive its max age, and a metric must reference a known goal. A load
//! problem is a located schema finding; below the live phase, or with no artifacts, it is silent.

// frob:ticket 01M5XCZ1C4P58PFPRCH880G1HE

use std::collections::BTreeSet;

use crunk_spec::metrics::MetricSet;
use crunk_spec::phase::Phase;
use crunk_spec::research::Date;

/// What a post-launch finding is about.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum MetricIssue {
    /// A metric or experiment file is malformed or repeats an id.
    Schema,
    /// A flow step has no analytics event.
    StepNoEvent,
    /// An experiment variant is not a declared component variant.
    UnknownVariant,
    /// An experiment names no guardrail metric.
    NoGuardrail,
    /// An experiment has run past its max age.
    Stale,
    /// A metric or guardrail references something that does not exist.
    Dangling,
}

/// One post-launch finding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MetricFinding {
    /// What kind of finding.
    pub issue: MetricIssue,
    /// The file (or flow step id) it is about.
    pub path: String,
    /// The 1-based line, when known.
    pub line: Option<usize>,
    /// The human message.
    pub message: String,
}

/// The project facts the checks compare the artifacts against.
#[derive(Debug, Clone)]
pub struct MetricContext {
    /// The project phase; only live is checked.
    pub phase: Phase,
    /// Today, supplied by the caller so the age check never reads the clock.
    pub today: Date,
    /// Every flow step id.
    pub flow_steps: BTreeSet<String>,
    /// Every declared `(component, variant)` pair.
    pub variants: BTreeSet<(String, String)>,
    /// Every declared goal id.
    pub goals: BTreeSet<String>,
}

/// A finding without a line.
fn finding(issue: MetricIssue, path: &str, message: String) -> MetricFinding {
    MetricFinding {
        issue,
        path: path.to_owned(),
        line: None,
        message,
    }
}

/// Run every post-launch check. Findings come in load problems, steps, metrics, experiments order.
#[must_use]
pub fn check_metric_rules(set: &MetricSet, ctx: &MetricContext) -> Vec<MetricFinding> {
    if ctx.phase < Phase::Live {
        tracing::debug!(phase = %ctx.phase, "below live; metric checks skipped");
        return Vec::new();
    }
    let mut out: Vec<MetricFinding> = set
        .problems
        .iter()
        .map(|p| MetricFinding {
            issue: MetricIssue::Schema,
            path: p.path.clone(),
            line: p.line,
            message: p.message.clone(),
        })
        .collect();
    if set.is_empty() {
        tracing::debug!(problems = out.len(), "no metric artifacts; checks silent");
        return out;
    }
    for step in &ctx.flow_steps {
        let has_event = set
            .metrics
            .iter()
            .any(|(_, m)| m.step.as_deref() == Some(step) && m.event.is_some());
        if !has_event {
            out.push(finding(
                MetricIssue::StepNoEvent,
                step,
                format!("flow step `{step}` has no analytics event"),
            ));
        }
    }
    for (path, m) in &set.metrics {
        if let Some(goal) = m.goal.as_ref().filter(|g| !ctx.goals.contains(*g)) {
            out.push(finding(
                MetricIssue::Dangling,
                path,
                format!("metric `{}` references unknown goal `{goal}`", m.id),
            ));
        }
    }
    for (path, x) in &set.experiments {
        for v in &x.variants {
            if !ctx.variants.contains(&(x.component.clone(), v.clone())) {
                out.push(finding(
                    MetricIssue::UnknownVariant,
                    path,
                    format!(
                        "variant `{v}` is not a declared variant of `{}`",
                        x.component
                    ),
                ));
            }
        }
        match &x.guardrail {
            None => out.push(finding(
                MetricIssue::NoGuardrail,
                path,
                format!("experiment `{}` has no guardrail metric", x.id),
            )),
            Some(g) if !set.metrics.iter().any(|(_, m)| m.id == *g) => out.push(finding(
                MetricIssue::Dangling,
                path,
                format!("experiment `{}` guardrail `{g}` is not a metric", x.id),
            )),
            Some(_) => {}
        }
        let age = ctx.today.days() - x.started.days();
        if age > x.max_age_days {
            out.push(finding(
                MetricIssue::Stale,
                path,
                format!(
                    "experiment `{}` is {age} days old, over its {} day limit",
                    x.id, x.max_age_days
                ),
            ));
        }
    }
    tracing::debug!(findings = out.len(), "metric checks done");
    out
}
