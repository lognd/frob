//! `rule check`: compile a rule file and print each rule's cost class and prefilter.

use super::{Diag, diagnostics, parse_clean};
use crate::lower::lower_rule;
use crate::plan::{CostClass, Provenance};

/// What compiling one rule produced.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct RuleCost {
    /// The rule id.
    pub rule: String,
    /// `per-file`, `per-repo` or `closure(N)`.
    pub cost: String,
    /// The node kinds the executor visits; empty means every node.
    pub prefilter: Vec<String>,
}

impl RuleCost {
    /// The line the text view prints.
    pub fn text(&self) -> String {
        let pre = if self.prefilter.is_empty() {
            "any".to_owned()
        } else {
            self.prefilter.join(", ")
        };
        format!("{}  {:<8} prefilter: {pre}", self.rule, self.cost)
    }
}

/// The compile result of one file.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, schemars::JsonSchema)]
pub struct FileCheck {
    /// The file path as given.
    pub path: String,
    /// Compile diagnostics with codes.
    pub diagnostics: Vec<Diag>,
    /// One entry per rule that lowered to a plan.
    pub rules: Vec<RuleCost>,
}

impl FileCheck {
    /// Whether the file compiled without errors.
    pub fn ok(&self) -> bool {
        !self.diagnostics.iter().any(|d| d.severity == "error")
    }
}

fn cost_word(c: CostClass) -> String {
    match c {
        CostClass::PerFile => "per-file".to_owned(),
        CostClass::PerRepo => "per-repo".to_owned(),
        CostClass::Closure(n) => format!("closure({n})"),
    }
}

/// Compile one rule file.
pub fn check_source(path: &str, source: &str) -> FileCheck {
    let (mut diags, has_error) = diagnostics(path, source);
    let mut rules = Vec::new();
    if !has_error && let Some(file) = parse_clean(path, source) {
        for rule in &file.rules {
            match lower_rule(rule, Provenance::Std) {
                Ok(plan) => {
                    let mut prefilter: Vec<String> =
                        plan.prefilter_kinds().map(str::to_owned).collect();
                    prefilter.sort();
                    rules.push(RuleCost {
                        rule: rule.id.text.clone(),
                        cost: cost_word(plan.cost()),
                        prefilter,
                    });
                }
                Err(e) => diags.push(Diag {
                    code: String::new(),
                    severity: "error".to_owned(),
                    line: 0,
                    col: 0,
                    message: format!("{}: {e}", rule.id.text),
                }),
            }
        }
    }
    FileCheck {
        path: path.to_owned(),
        diagnostics: diags,
        rules,
    }
}
