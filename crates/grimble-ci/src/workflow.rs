//! A parsed GitHub Actions workflow: the keys the CI rules read, plus line lookups for findings.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use std::collections::BTreeSet;

use serde_yaml_ng::Value;

/// A workflow file: its path, text and parsed YAML root.
pub(crate) struct Workflow<'a> {
    /// Repo-relative path of the file.
    pub path: &'a str,
    /// The file text (findings point into it).
    pub text: &'a str,
    root: Value,
}

/// One job of a workflow.
pub(crate) struct Job<'a> {
    /// The job id (`build`).
    pub id: &'a str,
    /// The job mapping.
    pub value: &'a Value,
}

/// A `key` of mapping `v`, `None` for a non-mapping or an absent key.
pub(crate) fn key<'a>(v: &'a Value, k: &str) -> Option<&'a Value> {
    v.get(k)
}

/// The text of a scalar (string, number or bool) value.
pub(crate) fn scalar(v: &Value) -> Option<String> {
    match v {
        Value::String(s) => Some(s.clone()),
        Value::Number(n) => Some(n.to_string()),
        Value::Bool(b) => Some(b.to_string()),
        _ => None,
    }
}

impl<'a> Workflow<'a> {
    /// Parse `text`; the error is the YAML parser's message.
    pub fn parse(path: &'a str, text: &'a str) -> Result<Self, String> {
        match serde_yaml_ng::from_str::<Value>(text) {
            Ok(root) if root.is_mapping() => Ok(Self { path, text, root }),
            Ok(_) => Err("the workflow root is not a mapping".to_owned()),
            Err(err) => Err(err.to_string()),
        }
    }

    /// The `on:` value (YAML 1.1 readers may have turned the key into a boolean `true`).
    fn on(&self) -> Option<&Value> {
        key(&self.root, "on").or_else(|| self.root.as_mapping()?.get(Value::Bool(true)))
    }

    /// The event names that trigger the workflow.
    pub fn triggers(&self) -> BTreeSet<String> {
        match self.on() {
            Some(Value::String(s)) => BTreeSet::from([s.clone()]),
            Some(Value::Sequence(seq)) => seq.iter().filter_map(scalar).collect(),
            Some(Value::Mapping(map)) => map.keys().filter_map(scalar).collect(),
            _ => BTreeSet::new(),
        }
    }

    /// The configuration mapping of trigger `event` (`push: {tags: ..}`), if any.
    pub fn trigger_config(&self, event: &str) -> Option<&Value> {
        key(self.on()?, event)
    }

    /// The top-level `permissions` value.
    pub fn permissions(&self) -> Option<&Value> {
        key(&self.root, "permissions")
    }

    /// True when the workflow declares `concurrency` at the top level.
    pub fn has_concurrency(&self) -> bool {
        key(&self.root, "concurrency").is_some()
    }

    /// The jobs in file order.
    pub fn jobs(&self) -> Vec<Job<'_>> {
        let Some(map) = key(&self.root, "jobs").and_then(Value::as_mapping) else {
            return Vec::new();
        };
        map.iter()
            .filter_map(|(k, value)| {
                Some(Job {
                    id: k.as_str()?,
                    value,
                })
            })
            .collect()
    }

    /// The byte range of the first line whose trimmed text starts with `needle` at or after `from`.
    pub fn line_of(&self, needle: &str, from: usize) -> Option<(usize, usize)> {
        let mut offset = 0;
        for line in self.text.split_inclusive('\n') {
            let end = offset + line.trim_end_matches(['\n', '\r']).len();
            if offset >= from && line.trim_start().starts_with(needle) {
                return Some((offset, end));
            }
            offset += line.len();
        }
        None
    }

    /// The range of the top-level `key:` line, else the first line of the file.
    pub fn top_range(&self, k: &str) -> (usize, usize) {
        let needle = format!("{k}:");
        self.line_of(&needle, 0)
            .unwrap_or_else(|| self.first_line())
    }

    /// The range of the line that declares job `id`, else the `jobs:` line.
    pub fn job_range(&self, id: &str) -> (usize, usize) {
        let start = self.top_range("jobs").0;
        self.line_of(&format!("{id}:"), start + 1)
            .unwrap_or_else(|| self.top_range("jobs"))
    }

    /// The range of the first line at or after job `id` that contains `needle`, else the job line.
    pub fn within_job(&self, id: &str, needle: &str) -> (usize, usize) {
        let job = self.job_range(id);
        let mut offset = 0;
        for line in self.text.split_inclusive('\n') {
            let end = offset + line.trim_end_matches(['\n', '\r']).len();
            if offset > job.0 && line.contains(needle) {
                return (offset, end);
            }
            offset += line.len();
        }
        job
    }

    /// The range of the first line of the file.
    fn first_line(&self) -> (usize, usize) {
        (0, self.text.lines().next().map_or(0, str::len))
    }
}

impl Job<'_> {
    /// The job-level `permissions` value.
    pub fn permissions(&self) -> Option<&Value> {
        key(self.value, "permissions")
    }

    /// True for a reusable-workflow call (`uses:` at job level; it has no steps or timeout).
    pub fn is_call(&self) -> bool {
        key(self.value, "uses").is_some()
    }

    /// The steps in order.
    pub fn steps(&self) -> Vec<&Value> {
        key(self.value, "steps")
            .and_then(Value::as_sequence)
            .map(|s| s.iter().collect())
            .unwrap_or_default()
    }
}

/// The `run:` text of a step.
pub(crate) fn run_of(step: &Value) -> Option<&str> {
    key(step, "run").and_then(Value::as_str)
}

/// The `uses:` text of a step.
pub(crate) fn uses_of(step: &Value) -> Option<&str> {
    key(step, "uses").and_then(Value::as_str)
}

/// The scalar `with.<name>` input of a step.
pub(crate) fn with_of(step: &Value, name: &str) -> Option<String> {
    scalar(key(key(step, "with")?, name)?)
}
