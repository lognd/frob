//! `[[check.tool]]` stages: external commands run after the built-in rules.

use std::time::{Duration, Instant};

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use gob_rules::{Finding, Rule, RuleId, Severity};

use crate::config::ToolStage;
use crate::report::Timing;
use crate::rules::Tool001;

/// Trailing characters of a tool's output quoted in the finding.
const TAIL: usize = 400;

fn tail(text: &str) -> String {
    let t = text.trim();
    let skip = t.chars().count().saturating_sub(TAIL);
    t.chars().skip(skip).collect()
}

/// Run `stages` in order; each is timed outside the budget and yields at most one `TOOL001`.
pub(crate) fn run_tools(
    root: &std::path::Path,
    stages: &[ToolStage],
    timing: &mut Timing,
) -> Vec<Finding> {
    if stages.is_empty() {
        return Vec::new();
    }
    let id: RuleId = Tool001
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"));
    let runner =
        Runner::new(Limits::default()).allow_tools(stages.iter().map(|s| s.command.clone()));
    let mut out = Vec::new();
    for stage in stages {
        let started = Instant::now();
        let spec = Spec {
            program: Program::Tool {
                name: stage.command.clone(),
            },
            args: stage.args.clone(),
            cwd: Some(root.to_path_buf()),
            env: Vec::new(),
            timeout: Duration::from_secs(stage.timeout_secs),
            capture: true,
        };
        let problem = match runner.run(&spec) {
            Ok(o) => match o.status {
                Outcome::Exited(0) => None,
                Outcome::Exited(code) => Some(format!(
                    "exited {code}: {}",
                    tail(&format!("{}\n{}", o.stdout, o.stderr))
                )),
                Outcome::Signaled => Some("was terminated by a signal".to_owned()),
                Outcome::TimedOut => Some(format!("timed out after {}s", stage.timeout_secs)),
            },
            Err(err) => Some(format!("could not run: {err}")),
        };
        timing.push(format!("tool:{}", stage.name), started.elapsed(), false);
        match problem {
            Some(p) if stage.fail_on_nonzero => {
                tracing::warn!(stage = %stage.name, problem = %p, "tool stage failed");
                out.push(Finding::new(
                    id.clone(),
                    Severity::Error,
                    None,
                    format!("tool stage `{}` ({}) {p}", stage.name, stage.command),
                    &stage.name,
                ));
            }
            Some(p) => {
                tracing::info!(stage = %stage.name, problem = %p, "tool stage failed (not gating)");
            }
            None => tracing::info!(stage = %stage.name, "tool stage passed"),
        }
    }
    out
}
