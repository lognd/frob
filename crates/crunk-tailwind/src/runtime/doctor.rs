//! The presence table behind `crunk doctor`: node, the project's tailwindcss, the helper.

// frob:ticket 01M43ARYX61ESX3S9XG1WS0DQ4

use serde::Serialize;

use super::model::UNRESOLVED_CODE;
use super::{Evaluation, Runtime, Sources, resolve};

/// One line of the table.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Row {
    /// What was checked (`node`, `tailwindcss`, `helper`).
    pub item: String,
    /// `ok`, `missing`, `failed` or `skipped`.
    pub state: String,
    /// The path, version or reason.
    pub detail: String,
}

/// What a doctor run found.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct DoctorReport {
    /// The table, in `node`, `tailwindcss`, `helper` order.
    pub rows: Vec<Row>,
    /// Anything that blocks node-verified Tailwind truth.
    pub issues: Vec<String>,
    /// Expected notices, chiefly the static fallback naming [`UNRESOLVED_CODE`].
    pub info: Vec<String>,
}

fn row(item: &str, state: &str, detail: impl Into<String>) -> Row {
    Row {
        item: item.to_owned(),
        state: state.to_owned(),
        detail: detail.into(),
    }
}

pub(super) fn report(rt: &Runtime, sources: &Sources) -> DoctorReport {
    let mut rows = Vec::new();
    let mut issues = Vec::new();
    let mut info = Vec::new();

    let node = rt.exec().resolve_node();
    if let Some(path) = &node {
        rows.push(row("node", "ok", path.display().to_string()));
    } else {
        let name = &rt.options.node_binary;
        rows.push(row("node", "missing", format!("no `{name}` on PATH")));
        issues.push(format!(
            "no `{name}` binary found on PATH; Tailwind truth falls back to {UNRESOLVED_CODE}"
        ));
    }

    let dir = resolve::find_tailwindcss_dir(&rt.project_root);
    let version = dir.as_deref().map(resolve::read_version);
    match (&dir, &version) {
        (None, _) => {
            rows.push(row("tailwindcss", "missing", "no node_modules/tailwindcss"));
            issues.push("no tailwindcss install found in this project's node_modules".to_owned());
        }
        (Some(_), Some(Ok(v))) => rows.push(row("tailwindcss", "ok", v.clone())),
        (Some(d), Some(Err(e))) => {
            rows.push(row("tailwindcss", "failed", e.clone()));
            issues.push(format!(
                "tailwindcss at {} has an unreadable version",
                d.display()
            ));
        }
        (Some(_), None) => {}
    }

    let probe = sources.config_path.is_some() || sources.css_entry.is_some();
    if rt.options.static_mode {
        rows.push(row("helper", "skipped", "static mode requested"));
        info.push(format!(
            "static mode requested: Tailwind truth is not verified; every candidate is {UNRESOLVED_CODE}"
        ));
    } else if node.is_none() || !matches!(version, Some(Ok(_))) {
        rows.push(row(
            "helper",
            "skipped",
            "needs node and a tailwindcss install",
        ));
        info.push(format!("static fallback: {UNRESOLVED_CODE}"));
    } else if !probe {
        rows.push(row(
            "helper",
            "skipped",
            "no config or CSS entry to probe with",
        ));
        info.push("helper probe skipped: no config or CSS entry given".to_owned());
    } else {
        match rt.evaluate_candidates(&["flex".to_owned()], sources) {
            Ok(Evaluation::Resolved(_)) => rows.push(row("helper", "ok", "compiled `flex`")),
            Ok(Evaluation::Unresolved(u)) => {
                rows.push(row("helper", "skipped", u.to_string()));
                info.push(u.to_string());
            }
            Err(e) => {
                rows.push(row("helper", "failed", e.to_string()));
                issues.push(format!("the tailwind helper failed to run: {e}"));
            }
        }
    }
    tracing::info!(issues = issues.len(), "tailwind doctor finished");
    DoctorReport { rows, issues, info }
}
