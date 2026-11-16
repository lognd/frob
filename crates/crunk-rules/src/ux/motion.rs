//! The prototyping checks over authored flows: every edge targets a declared node, every motion is
//! a duration token within the configured bound, and every motion has a reduced-motion twin.
//! Without duration tokens the motion checks are `Unresolved` rather than silently clean.

// frob:ticket 01M5XCZ1K91B012K3QDSH0JBCS

use crunk_tokens::{TokenKind, TokenSet, TokenValue};

use crate::flow_files::FlowFacts;

/// The token mode (or `-reduced` sibling token suffix) that carries a motion's reduced-motion twin.
pub const REDUCED: &str = "reduced";

/// What a prototyping finding is about.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum MotionIssue {
    /// An edge starts or ends at a node the flow does not declare.
    MissingTarget,
    /// A motion is a duration literal such as `200ms`, not a token name.
    LiteralDuration,
    /// A motion names a token that is missing or not a duration.
    UnknownToken,
    /// A motion's duration token is above the bound.
    OverBound,
    /// A motion has no reduced-motion twin.
    NoReducedTwin,
    /// A reduced-motion twin is itself animated beyond the bound.
    TwinOverBound,
    /// No duration tokens are declared, so the motion checks could not run.
    Unresolved,
}

/// One prototyping finding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MotionFinding {
    /// What kind of finding.
    pub issue: MotionIssue,
    /// The flow file it is about, relative to the project root.
    pub path: String,
    /// The human message.
    pub message: String,
}

/// True when `motion` is a duration literal (`200ms`, `0.2s`, `0`) rather than a token name.
fn is_literal(motion: &str) -> bool {
    let m = motion.trim();
    m.starts_with(|c: char| c.is_ascii_digit() || c == '.')
}

/// The token name a flow's motion reference means: `motion.slide` and `--motion-slide` are one.
fn token_name(motion: &str) -> String {
    if motion.starts_with("--") {
        motion.to_owned()
    } else {
        crunk_tokens::dialect::name_of_path(motion)
    }
}

/// A duration in milliseconds, or `None` when `value` is not a duration.
fn millis(value: Option<&TokenValue>) -> Option<f64> {
    match value {
        Some(TokenValue::Duration(ms)) => Some(*ms),
        _ => None,
    }
}

/// The reduced-motion twin of token `name`: its `reduced` mode value, else the `<name>-reduced`
/// sibling token; `None` when neither exists.
fn twin(set: &TokenSet, name: &str) -> Option<f64> {
    let mode = set
        .get(name)
        .and_then(|t| t.modes.get(REDUCED))
        .and_then(|v| millis(Some(v)));
    mode.or_else(|| millis(set.resolve(&format!("{name}-{REDUCED}"), None)))
}

/// Edges whose endpoints are not declared nodes of their flow.
fn check_targets(facts: &FlowFacts) -> Vec<MotionFinding> {
    let mut out = Vec::new();
    for (path, flow) in &facts.files {
        for edge in &flow.edges {
            for node in [&edge.from, &edge.to] {
                if !flow.nodes.contains(node) {
                    tracing::debug!(%path, %node, "flow edge targets a missing node");
                    out.push(MotionFinding {
                        issue: MotionIssue::MissingTarget,
                        path: path.clone(),
                        message: format!(
                            "trigger `{}` from `{}` to `{}` targets missing node `{node}`",
                            edge.trigger, edge.from, edge.to
                        ),
                    });
                }
            }
        }
    }
    out
}

/// One motion reference read against the tokens and the bound.
fn check_motion(
    path: &str,
    motion: &str,
    set: &TokenSet,
    max_ms: Option<f64>,
) -> Vec<MotionFinding> {
    let finding = |issue, message: String| MotionFinding {
        issue,
        path: path.to_owned(),
        message,
    };
    if is_literal(motion) {
        return vec![finding(
            MotionIssue::LiteralDuration,
            format!("motion `{motion}` is a literal; reference a duration token"),
        )];
    }
    let Some(ms) = millis(set.resolve(&token_name(motion), None)) else {
        return vec![finding(
            MotionIssue::UnknownToken,
            format!("motion `{motion}` is not a declared duration token"),
        )];
    };
    let mut out = Vec::new();
    if max_ms.is_some_and(|max| ms > max) {
        out.push(finding(
            MotionIssue::OverBound,
            format!("motion `{motion}` lasts {ms}ms, above the bound"),
        ));
    }
    match twin(set, &token_name(motion)) {
        None => out.push(finding(
            MotionIssue::NoReducedTwin,
            format!("motion `{motion}` has no reduced-motion twin"),
        )),
        Some(t) if max_ms.is_some_and(|max| t > max) => out.push(finding(
            MotionIssue::TwinOverBound,
            format!("the reduced-motion twin of `{motion}` lasts {t}ms, above the bound"),
        )),
        Some(_) => {}
    }
    out
}

/// Run every prototyping check. `tokens` is `None` when the host cannot supply them; with no
/// duration tokens declared and motion in use the result is a single `Unresolved` finding. Zero
/// duration is valid, and `max_ms` of `None` disables the bound checks only.
#[must_use]
pub fn check_motion_rules(
    facts: &FlowFacts,
    tokens: Option<&TokenSet>,
    max_ms: Option<f64>,
) -> Vec<MotionFinding> {
    let mut out = check_targets(facts);
    let used: Vec<(&str, &str)> = facts
        .files
        .iter()
        .flat_map(|(path, flow)| {
            flow.edges
                .iter()
                .filter_map(move |e| e.motion.as_deref().map(|m| (path.as_str(), m)))
        })
        .collect();
    if used.is_empty() {
        return out;
    }
    let Some(set) = tokens.filter(|s| has_duration(s)) else {
        tracing::debug!("no duration tokens; motion checks unresolved");
        out.push(MotionFinding {
            issue: MotionIssue::Unresolved,
            path: used[0].0.to_owned(),
            message: "no motion tokens are declared; the motion checks are unresolved".to_owned(),
        });
        return out;
    };
    for (path, motion) in used {
        out.extend(check_motion(path, motion, set, max_ms));
    }
    tracing::debug!(findings = out.len(), "motion checks done");
    out
}

/// True when any token is a duration (a `[scales]` step or an authored token holding one).
fn has_duration(set: &TokenSet) -> bool {
    set.of_kind(TokenKind::Duration).next().is_some()
        || set
            .iter()
            .any(|t| matches!(t.value, TokenValue::Duration(_)))
}
