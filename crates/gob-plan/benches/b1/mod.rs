//! Shared parts of benchmark B1 (plugins.md section 6.6): the plan executor against handwritten
//! Rust on three std rules, over the 100k-line fixture.
//!
//! The gate: per rule, the median over files of `plan time / handwritten time` must stay at or
//! under [`LIMIT`]. Findings from both forms must be equal first, or the timing means nothing.

pub mod fixture;
pub mod hand;

use std::time::{Duration, Instant};

use gob_ir::Model;
use gob_plan::exec::outcome::{Kind, outcomes};
use gob_plan::exec::relations::Relations;
use gob_plan::exec::{ExecError, Input};
use gob_plan::grl::parse;
use gob_plan::lower::lower_rule;
use gob_plan::plan::{Plan, Provenance};
use gob_text::{FileInterner, SourceText};

/// The ratio above which the gate fails (plugins.md section 6.6).
pub const LIMIT: f64 = 1.3;

/// One finding as compared between forms: its kind and the node it is on.
pub type Found = (bool, gob_ir::NodeId);

/// Why a B1 step failed.
#[derive(Debug, thiserror::Error)]
pub enum BenchError {
    /// The rule source did not parse or lower.
    #[error("rule {0} did not compile: {1}")]
    Rule(&'static str, String),
    /// A fixture file did not build into a model.
    #[error("fixture {0} did not model: {1}")]
    Model(String, String),
    /// The executor refused a plan.
    #[error("executor failed: {0}")]
    Exec(#[from] ExecError),
    /// The plan and the handwritten form disagree on a file.
    #[error(
        "{rule} on {path}: plan and handwritten findings differ\n plan: {plan:?}\n hand: {hand:?}"
    )]
    Mismatch {
        /// Rule id.
        rule: &'static str,
        /// File path.
        path: String,
        /// Plan findings.
        plan: Vec<Found>,
        /// Handwritten findings.
        hand: Vec<Found>,
    },
    /// The median per-file ratio is over the limit.
    #[error("{rule}: median per-file ratio {ratio:.2}x exceeds {limit:.2}x")]
    OverBudget {
        /// Rule id.
        rule: &'static str,
        /// Measured ratio.
        ratio: f64,
        /// Limit it was held to.
        limit: f64,
    },
}

/// A fixture file built into a model once, outside any timed region.
pub struct Prepared {
    /// Repository path.
    pub path: String,
    /// Its model.
    pub model: Model,
    /// Its text.
    pub source: SourceText,
}

/// Builds the model and source text of `file` as language `lang`.
pub fn prepare(file: &fixture::SourceFile, lang: &str) -> Result<Prepared, BenchError> {
    let err = |e: String| BenchError::Model(file.path.clone(), e);
    let model = gob_symbols::model_of_source_at(&file.path, &file.text)
        .or_else(|_| gob_symbols::model_of_source(lang, &file.text))
        .map_err(|e| err(e.to_string()))?;
    let source = SourceText::new(file.text.clone()).map_err(|e| err(e.to_string()))?;
    Ok(Prepared {
        path: file.path.clone(),
        model,
        source,
    })
}

/// The three std rules, their language and their handwritten form.
pub struct Case {
    /// Rule id.
    pub id: &'static str,
    /// Lowered plan.
    pub plan: Plan,
    /// Whether the plan needs the `calls` and `tests` edges.
    pub edges: bool,
    /// The handwritten form.
    pub hand: fn(&Prepared) -> Vec<Found>,
}

fn compile(id: &'static str, src: &str) -> Result<Plan, BenchError> {
    let parsed = parse(FileInterner::new().intern(id), src);
    let (true, Some(rule)) = (parsed.is_ok(), parsed.file.rules.first()) else {
        return Err(BenchError::Rule(id, format!("{:?}", parsed.errors)));
    };
    lower_rule(rule, Provenance::Std).map_err(|e| BenchError::Rule(id, e.to_string()))
}

/// Compiles TODO001, COV001 (Rust) and DOC002 (Markdown) into cases, once.
pub fn cases() -> Result<[Case; 3], BenchError> {
    Ok([
        Case {
            id: "TODO001",
            plan: compile(
                "TODO001",
                include_str!("../../tests/ten_rules/cases/TODO001.grl"),
            )?,
            edges: false,
            hand: hand::todo001,
        },
        Case {
            id: "COV001",
            plan: compile(
                "COV001",
                include_str!("../../tests/ten_rules/cases/COV001.grl"),
            )?,
            edges: true,
            hand: hand::cov001,
        },
        Case {
            id: "DOC002",
            plan: compile(
                "DOC002",
                include_str!("../../tests/ten_rules/cases/DOC002.grl"),
            )?,
            edges: false,
            hand: hand::doc002,
        },
    ])
}

/// Runs the plan of `case` over `p` and returns its sorted findings.
pub fn run_plan(case: &Case, p: &Prepared) -> Result<Vec<Found>, BenchError> {
    let mut rels = Relations::new();
    if case.edges {
        rels = rels
            .with_edges("calls", gob_ir::eval::Ctx::new(&p.model).rel_calls())
            .with_edges("tests", gob_ir::eval::Relation::new());
    }
    let input = Input {
        model: &p.model,
        source: Some(&p.source),
    };
    let out = outcomes(&case.plan, &input, &rels)?;
    let mut found: Vec<Found> = out
        .findings
        .iter()
        .filter_map(|f| f.subject.map(|n| (f.kind == Kind::Unresolved, n)))
        .collect();
    found.sort();
    Ok(found)
}

/// Asserts the plan and handwritten findings of `case` agree on `p` (acceptance: equal).
pub fn check_equal(case: &Case, p: &Prepared) -> Result<usize, BenchError> {
    let plan = run_plan(case, p)?;
    let hand = (case.hand)(p);
    if plan == hand {
        Ok(plan.len())
    } else {
        Err(BenchError::Mismatch {
            rule: case.id,
            path: p.path.clone(),
            plan,
            hand,
        })
    }
}

/// The fastest of `reps` runs of `f`, after one warm-up.
pub fn best_of<T>(reps: u32, mut f: impl FnMut() -> T) -> Duration {
    std::hint::black_box(f());
    (0..reps)
        .map(|_| {
            let start = Instant::now();
            std::hint::black_box(f());
            start.elapsed()
        })
        .min()
        .unwrap_or_default()
}

/// Per-file ratios of one rule: plan time over handwritten time.
pub fn ratios(case: &Case, files: &[Prepared], reps: u32) -> Result<Vec<f64>, BenchError> {
    files
        .iter()
        .map(|p| {
            let hand = best_of(reps, || (case.hand)(p));
            let plan = best_of(reps, || run_plan(case, p));
            Ok(plan.as_secs_f64() / hand.as_secs_f64().max(f64::EPSILON))
        })
        .collect()
}

/// The median of `xs` (0.0 when empty).
pub fn median(xs: &[f64]) -> f64 {
    let mut v = xs.to_vec();
    v.sort_by(f64::total_cmp);
    match v.len() {
        0 => 0.0,
        n if n % 2 == 1 => v[n / 2],
        n => f64::midpoint(v[n / 2 - 1], v[n / 2]),
    }
}

/// The gate: passes when `ratio` is at or under `limit`.
pub fn gate(rule: &'static str, ratio: f64, limit: f64) -> Result<(), BenchError> {
    if ratio <= limit {
        Ok(())
    } else {
        Err(BenchError::OverBudget { rule, ratio, limit })
    }
}
