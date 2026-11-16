//! The post-launch checks: the acceptance cases and edge cases.

// frob:ticket 01M5XCZ1C4P58PFPRCH880G1HE

use std::collections::BTreeSet;

use crunk_rules::proc_metrics::{MetricContext, MetricFinding, MetricIssue, check_metric_rules};
use crunk_spec::metrics::{Experiment, Heart, Metric, MetricSet};
use crunk_spec::phase::Phase;
use crunk_spec::research::{Date, ResearchProblem};

fn date(text: &str) -> Date {
    Date::parse(text).expect("date")
}

fn ctx(phase: Phase) -> MetricContext {
    MetricContext {
        phase,
        today: date("2026-06-01"),
        flow_steps: BTreeSet::new(),
        variants: BTreeSet::from([("button".to_owned(), "big".to_owned())]),
        goals: BTreeSet::from(["buy".to_owned()]),
    }
}

fn metric(id: &str, goal: Option<&str>, step: Option<&str>, event: Option<&str>) -> Metric {
    Metric {
        id: id.to_owned(),
        heart: Heart::Engagement,
        goal: goal.map(str::to_owned),
        step: step.map(str::to_owned),
        event: event.map(str::to_owned),
    }
}

fn experiment(variant: &str, guardrail: Option<&str>, started: &str) -> Experiment {
    Experiment {
        id: "x".to_owned(),
        component: "button".to_owned(),
        variants: vec![variant.to_owned()],
        started: date(started),
        max_age_days: 30,
        guardrail: guardrail.map(str::to_owned),
    }
}

fn with_metric(m: Metric) -> MetricSet {
    MetricSet {
        metrics: vec![("design/metrics/m.toml".to_owned(), m)],
        ..MetricSet::default()
    }
}

fn with_experiment(x: Experiment) -> MetricSet {
    let mut set = with_metric(metric("guard", None, None, None));
    set.experiments = vec![("design/experiments/x.toml".to_owned(), x)];
    set
}

fn issues(found: Vec<MetricFinding>) -> Vec<MetricIssue> {
    found.into_iter().map(|f| f.issue).collect()
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn flow_step_without_event_fires() {
    let mut c = ctx(Phase::Live);
    c.flow_steps.insert("cart".to_owned());
    let found = check_metric_rules(&with_metric(metric("m", None, Some("cart"), None)), &c);
    assert_eq!(issues(found), [MetricIssue::StepNoEvent]);
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn flow_step_with_event_is_clean() {
    let mut c = ctx(Phase::Live);
    c.flow_steps.insert("cart".to_owned());
    let set = with_metric(metric("m", None, Some("cart"), Some("cart_viewed")));
    assert!(check_metric_rules(&set, &c).is_empty());
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn undeclared_variant_fires() {
    let set = with_experiment(experiment("huge", Some("guard"), "2026-05-20"));
    let found = check_metric_rules(&set, &ctx(Phase::Live));
    assert_eq!(issues(found), [MetricIssue::UnknownVariant]);
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn experiment_without_guardrail_fires() {
    let set = with_experiment(experiment("big", None, "2026-05-20"));
    let found = check_metric_rules(&set, &ctx(Phase::Live));
    assert_eq!(issues(found), [MetricIssue::NoGuardrail]);
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn guardrail_naming_no_metric_is_dangling() {
    let set = with_experiment(experiment("big", Some("ghost"), "2026-05-20"));
    let found = check_metric_rules(&set, &ctx(Phase::Live));
    assert_eq!(issues(found), [MetricIssue::Dangling]);
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn old_experiment_is_stale() {
    let set = with_experiment(experiment("big", Some("guard"), "2026-01-01"));
    let found = check_metric_rules(&set, &ctx(Phase::Live));
    assert_eq!(issues(found), [MetricIssue::Stale]);
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn recent_experiment_is_clean() {
    let set = with_experiment(experiment("big", Some("guard"), "2026-05-20"));
    assert!(check_metric_rules(&set, &ctx(Phase::Live)).is_empty());
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn metric_with_unknown_goal_is_dangling() {
    let found = check_metric_rules(
        &with_metric(metric("m", Some("nope"), None, None)),
        &ctx(Phase::Live),
    );
    assert_eq!(issues(found), [MetricIssue::Dangling]);
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn phase_below_live_is_skipped() {
    let mut c = ctx(Phase::Beta);
    c.flow_steps.insert("cart".to_owned());
    assert!(check_metric_rules(&with_metric(metric("m", Some("nope"), None, None)), &c).is_empty());
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn empty_set_is_silent() {
    assert!(check_metric_rules(&MetricSet::default(), &ctx(Phase::Live)).is_empty());
}

// frob:tests crates/crunk-rules/src/proc_metrics.rs::check_metric_rules
#[test]
fn load_problems_are_located_schema_findings() {
    let bad = MetricSet {
        problems: vec![ResearchProblem {
            path: "design/metrics/a.toml".to_owned(),
            line: Some(2),
            message: "duplicate id".to_owned(),
        }],
        ..MetricSet::default()
    };
    let found = check_metric_rules(&bad, &ctx(Phase::Live));
    assert_eq!(found[0].issue, MetricIssue::Schema);
    assert_eq!(found[0].line, Some(2));
}
