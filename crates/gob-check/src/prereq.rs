//! Prerequisites of tool stages: commands that produce gitignored build output a stage reads.
//!
//! A stage declares `requires = ["wasm-pack build"]`, or the repository declares `[check] setup`
//! steps that precede every stage. Both run in the repository root of the checkout being checked,
//! so a land checkout or a fresh ticket worktree builds what it needs before the stage runs.
//! Each distinct command line runs once per check run however many stages need it; a command that
//! fails (or cannot be found) makes the stage Unresolved naming it, never a red or green verdict
//! about the stage's own tool.

use std::collections::HashMap;
use std::path::Path;
use std::sync::{Arc, Mutex, OnceLock};

use gob_exec::{ExecError, Outcome, Runner};

use crate::config::{ToolParser, ToolStage};
use crate::tools::{ToolTrust, escape, excerpt, launch, status_text, vet_message};

/// A prerequisite command line split into its program and arguments (no shell, no quoting).
///
/// # Errors
///
/// A message when the line is empty, or its program is a path or carries shell syntax or quotes.
pub(crate) fn split(line: &str) -> Result<(String, Vec<String>), String> {
    let mut words = line.split_whitespace();
    let Some(program) = words.next() else {
        return Err("it is empty".to_owned());
    };
    if line.chars().any(|c| "\"'`$|&;<>\\".contains(c)) {
        return Err(
            "it has quoting or shell syntax; a prerequisite is a program and plain arguments, so put anything more in a script".to_owned(),
        );
    }
    if program.contains('/') {
        return Err("its program must be a name on PATH, not a path".to_owned());
    }
    Ok((program.to_owned(), words.map(str::to_owned).collect()))
}

type Slot = Arc<OnceLock<Result<(), String>>>;

/// The prerequisites of one check run: the repository `setup` steps and a once-only record of what ran.
#[derive(Debug, Default)]
pub(crate) struct Prereqs {
    setup: Vec<String>,
    done: Mutex<HashMap<String, Slot>>,
}

impl Prereqs {
    /// Prerequisites that run `setup` before every stage.
    pub(crate) fn new(setup: &[String]) -> Self {
        Self {
            setup: setup.to_vec(),
            done: Mutex::default(),
        }
    }

    /// The program names every prerequisite of `stages` and the setup steps run, for the runner allowlist.
    pub(crate) fn programs(&self, stages: &[ToolStage]) -> Vec<String> {
        self.setup
            .iter()
            .chain(stages.iter().flat_map(|s| &s.requires))
            .filter_map(|line| split(line).ok().map(|(program, _)| program))
            .collect()
    }

    /// Run the setup steps then `stage`'s `requires`, each at most once per run.
    ///
    /// # Errors
    ///
    /// The Unresolved message naming the first prerequisite that failed, with the remedy.
    pub(crate) fn ensure(
        &self,
        runner: &Runner,
        root: &Path,
        stage: &ToolStage,
        trust: Option<&dyn ToolTrust>,
    ) -> Result<(), String> {
        for (kind, line) in self
            .setup
            .iter()
            .map(|l| ("setup step", l))
            .chain(stage.requires.iter().map(|l| ("prerequisite", l)))
        {
            let slot = {
                let mut done = self
                    .done
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner);
                Arc::clone(done.entry(line.clone()).or_default())
            };
            slot.get_or_init(|| run_one(runner, root, stage, trust, line))
                .clone()
                .map_err(|why| {
                    format!(
                        "tool stage `{}` was not run: {kind} `{}` {why}; run `{}` in the repository root and fix its failure, then re-run",
                        stage.name,
                        escape(line),
                        escape(line)
                    )
                })?;
        }
        Ok(())
    }
}

/// Run one prerequisite `line` under the stage's trust gate; `Err` says how it failed.
fn run_one(
    runner: &Runner,
    root: &Path,
    stage: &ToolStage,
    trust: Option<&dyn ToolTrust>,
    line: &str,
) -> Result<(), String> {
    let (program, args) = split(line).map_err(|why| format!("is malformed: {why}"))?;
    let step = ToolStage {
        name: format!("{}:requires", stage.name),
        def: None,
        command: program,
        args: args.clone(),
        parser: ToolParser::None,
        requires: Vec::new(),
        ..stage.clone()
    };
    let pack = vet_message(root, &step, trust).inspect_err(|_| {
        tracing::warn!(stage = %stage.name, line, "prerequisite could not be vetted");
    })?;
    tracing::info!(stage = %stage.name, line, "prerequisite running");
    match launch(runner, root, &step, pack.as_ref(), args) {
        Ok(o) if o.status == Outcome::Exited(0) => {
            tracing::info!(line, "prerequisite passed");
            Ok(())
        }
        Ok(o) => {
            tracing::warn!(line, status = %status_text(&o), "prerequisite failed");
            Err(format!(
                "failed ({}); stderr: {}",
                status_text(&o),
                excerpt(&o.stderr)
            ))
        }
        Err(err @ ExecError::NotFound { .. }) => {
            tracing::warn!(line, %err, "prerequisite command not found");
            Err(format!(
                "could not run ({err}); is it installed and on PATH?"
            ))
        }
        Err(err) => {
            tracing::error!(line, %err, "prerequisite could not run");
            Err(format!("could not run ({err})"))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::split;

    // frob:tests crates/gob-check/src/prereq.rs::split
    #[test]
    fn a_requirement_splits_into_program_and_plain_arguments() {
        assert_eq!(
            split("wasm-pack build --dev"),
            Ok(("wasm-pack".to_owned(), vec!["build".into(), "--dev".into()]))
        );
        assert!(split("  ").is_err());
        assert!(split("sh -c 'make'").is_err());
        assert!(split("./build.sh").is_err());
    }
}
