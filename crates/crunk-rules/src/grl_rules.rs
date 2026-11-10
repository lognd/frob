//! Runs the GRL-generated crunk rules (`packs/crunk-core/generated`) over a [`CrunkHost`]: the host's
//! stamped files (and each sheet's source) become one workspace model, the `[layers]` and `[org]`
//! tables of the spec become the `config.layers` and `config.org` side tables, and each generated
//! finding is mapped back to a file path and a file-local line.

// frob:ticket 01M71T80ZZPW5Z00CKF3ANQ2X3

use std::collections::HashMap;

use gob_plan::catalog::{Column, FieldType};
use gob_plan::exec::message::render_message;
use gob_plan::exec::outcome::{Kind, Outcomes};
use gob_plan::exec::relations::{Relations, SideData, SideTable};
use gob_plan::exec::{Input, Scalar};
use gob_plan::plan::Plan;
use gob_plan::workspace::{self, WorkspaceFile};

use crate::file_attrs::host_stamped_files;
use crate::host::{CrunkHost, missing_inputs};
use crate::org::case_name;
use crate::sheets::site_path;

#[path = "../../../packs/crunk-core/generated/layer001.rs"]
#[allow(dead_code, clippy::pedantic, clippy::restriction, missing_docs)]
mod layer001;
#[path = "../../../packs/crunk-core/generated/org002.rs"]
#[allow(dead_code, clippy::pedantic, clippy::restriction, missing_docs)]
mod org002;

/// One finding of a GRL-run rule, located in a project file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GrlFinding {
    /// The rule id (`LAYER001`, `ORG002`).
    pub rule: &'static str,
    /// The project-relative path of the file.
    pub path: String,
    /// The 1-based line in that file.
    pub line: u32,
    /// The rendered report message.
    pub message: String,
}

/// What running a GRL rule on a host produced.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GrlOutcome {
    /// The rule ran; these are its findings (possibly none).
    Findings(Vec<GrlFinding>),
    /// The rule has nothing to judge here, and why.
    Inapplicable(String),
}

/// Why a GRL rule could not run.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum GrlRunError {
    /// The workspace model or a side table could not be built.
    #[error("workspace: {0}")]
    Workspace(String),
    /// The generated plan was malformed or the executor refused it.
    #[error("execution: {0}")]
    Exec(String),
}

/// A generated rule: its id, plan loader and runner.
struct Generated {
    id: &'static str,
    plan: fn() -> Result<Plan, gob_plan::plan::PlanError>,
}

fn col(name: &str, ty: FieldType) -> Column {
    Column {
        name: name.to_owned(),
        ty,
    }
}

/// The workspace files of `host`: each stamped file with its sheet's source (empty when it has none).
fn files_of<H: CrunkHost + ?Sized>(host: &H) -> Vec<WorkspaceFile> {
    let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
        return Vec::new();
    };
    let sources: HashMap<_, _> = styles
        .sheets
        .iter()
        .map(|s| (s.path.clone(), s.source.as_str()))
        .collect();
    host_stamped_files(host)
        .into_iter()
        .map(|f| {
            let text = sources.get(&f.path).copied().unwrap_or_default();
            let mut file = WorkspaceFile::new(site_path(spec, &f.path), text);
            file.attrs = f
                .attrs
                .into_iter()
                .map(|(k, v)| (k.to_owned(), v))
                .collect();
            file
        })
        .collect()
}

/// Builds the workspace, runs `run`, and maps each finding back to a file and line.
fn execute<H: CrunkHost + ?Sized>(
    host: &H,
    rule: &Generated,
    side: SideData,
    run: impl FnOnce(&Input<'_>, &Relations) -> Result<Outcomes, String>,
) -> Result<Vec<GrlFinding>, GrlRunError> {
    let files = files_of(host);
    let ws = workspace::build(&files, gob_symbols::model_of_source_at)
        .map_err(|e| GrlRunError::Workspace(e.to_string()))?;
    let source = gob_text::SourceText::new(ws.text.clone())
        .map_err(|_| GrlRunError::Workspace("project text too large".to_owned()))?;
    let input = Input {
        model: &ws.model,
        source: Some(&source),
    };
    let plan = (rule.plan)().map_err(|e| GrlRunError::Exec(format!("{e:?}")))?;
    let out = run(&input, &Relations::new().with_side(side)).map_err(GrlRunError::Exec)?;
    let mut found = Vec::new();
    for f in out.findings.iter().filter(|f| f.kind == Kind::Fire) {
        let Some(span) = f
            .subject
            .and_then(|n| ws.model.term().node(n).location().span())
        else {
            continue;
        };
        let Some(lc) = source.line_col(span.range.start()) else {
            continue;
        };
        let (file, line) = ws.locate(lc.line);
        let message = render_message(&plan, &input, f);
        tracing::debug!(rule = rule.id, path = %files[file].path, line, "GRL rule fired");
        found.push(GrlFinding {
            rule: rule.id,
            path: files[file].path.clone(),
            line,
            message,
        });
    }
    tracing::info!(rule = rule.id, findings = found.len(), "GRL rule ran");
    Ok(found)
}

/// Runs the GRL LAYER001: integer `z-index` values not among `[layers]`.
///
/// # Errors
/// [`GrlRunError`] when the workspace or the generated plan cannot run.
pub fn run_layer001<H: CrunkHost + ?Sized>(host: &H) -> Result<GrlOutcome, GrlRunError> {
    if let Some(why) = missing_inputs(host) {
        return Ok(GrlOutcome::Inapplicable(why));
    }
    let Some(spec) = host.spec() else {
        return Ok(GrlOutcome::Inapplicable("no valid crunk.toml".to_owned()));
    };
    if spec.layers.is_empty() {
        tracing::debug!("LAYER001: no [layers] declared");
        return Ok(GrlOutcome::Inapplicable(
            "no [layers] are declared".to_owned(),
        ));
    }
    let rows = spec
        .layers
        .iter()
        .map(|(name, value)| vec![Scalar::Str(name.clone()), Scalar::Int(*value)])
        .collect();
    let table = SideTable::new(
        vec![col("name", FieldType::Str), col("value", FieldType::Int)],
        rows,
    );
    let side = side_with("config.layers", table)?;
    let rule = Generated {
        id: "LAYER001",
        plan: layer001::plan,
    };
    execute(host, &rule, side, |i, r| {
        layer001::run(i, r).map_err(|e| format!("{e:?}"))
    })
    .map(GrlOutcome::Findings)
}

/// Runs the GRL ORG002: class selectors not written in `[org] class_case`.
///
/// # Errors
/// [`GrlRunError`] when the workspace or the generated plan cannot run.
pub fn run_org002<H: CrunkHost + ?Sized>(host: &H) -> Result<GrlOutcome, GrlRunError> {
    if let Some(why) = missing_inputs(host) {
        return Ok(GrlOutcome::Inapplicable(why));
    }
    let Some(spec) = host.spec() else {
        return Ok(GrlOutcome::Inapplicable("no valid crunk.toml".to_owned()));
    };
    let row = vec![Scalar::Str(case_name(spec.org.class_case).to_owned())];
    let table = SideTable::new(vec![col("class_case", FieldType::Str)], vec![row]);
    let side = side_with("config.org", table)?;
    let rule = Generated {
        id: "ORG002",
        plan: org002::plan,
    };
    execute(host, &rule, side, |i, r| {
        org002::run(i, r).map_err(|e| format!("{e:?}"))
    })
    .map(GrlOutcome::Findings)
}

/// Side data holding the one table `name`.
fn side_with(name: &str, table: SideTable) -> Result<SideData, GrlRunError> {
    let mut side = SideData::new();
    side.insert(name, table)
        .map_err(|e| GrlRunError::Workspace(e.to_string()))?;
    Ok(side)
}
