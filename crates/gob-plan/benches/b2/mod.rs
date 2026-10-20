//! Shared parts of benchmark B2 (plugins.md section 6.6): a rule compiled in against the same
//! rule as a disk-loaded plan served from a warm plan cache.
//!
//! The compiled-in form is what `gob_plan::codegen` emits: embedded canonical plan bytes read by
//! `Plan::load_embedded`. The disk form is `gob_packs::PlanCache::load_or_compile` hitting a
//! verified entry. Each run obtains the plan, then executes it over every fixture file; the gate
//! holds the disk time to [`LIMIT`] times the compiled-in time. Findings must be identical first,
//! compared as JSON.

// frob:ticket 01M3ZX7JHQQ3BVZWFMPAW40T13

#[path = "../b1/mod.rs"]
#[allow(dead_code, reason = "B2 reuses only part of the B1 harness")]
pub mod b1;

use std::time::{Duration, Instant};

use b1::{Case, Prepared, run_plan};
use gob_packs::{PlanCache, Source};
use gob_plan::plan::Plan;
use gob_trust::MachineKey;

pub use b1::{BenchError, LIMIT, cases, fixture, gate, median, prepare};

/// A warm cache holding one rule, plus the compiled-in bytes of the same rule.
pub struct Pair {
    /// Rule id.
    pub id: &'static str,
    /// The canonical plan bytes, standing in for the generated module's static.
    pub embedded: &'static [u8],
    /// The cache the disk form loads from.
    pub cache: PlanCache,
    digest: [u8; 32],
    /// Keeps the cache directory alive.
    _dir: tempfile::TempDir,
}

const ENGINE: &str = "b2-engine";

/// Builds the warm cache and the embedded bytes for `case` (outside any timed region).
pub fn pair(case: &Case) -> Result<Pair, BenchError> {
    let fail = |e: String| BenchError::Rule(case.id, e);
    let dir = tempfile::tempdir().map_err(|e| fail(e.to_string()))?;
    let cache = PlanCache::open_at(
        dir.path().join("grimble").join("state"),
        MachineKey::from_bytes([2; 32]),
        None,
    )
    .map_err(|e| fail(e.to_string()))?;
    let digest = [7u8; 32];
    let warm = cache
        .load_or_compile(&digest, ENGINE, || {
            Ok::<_, std::convert::Infallible>(vec![case.plan.clone()])
        })
        .map_err(|e| fail(e.to_string()))?;
    debug_assert!(matches!(warm.source, Source::Compiled));
    let embedded: &'static [u8] = Box::leak(case.plan.to_bytes().into_boxed_slice());
    Ok(Pair {
        id: case.id,
        embedded,
        cache,
        digest,
        _dir: dir,
    })
}

/// The compiled-in plan: what the generated module's `plan()` returns.
pub fn compiled_plan(p: &Pair) -> Result<Plan, BenchError> {
    Plan::load_embedded(p.embedded).map_err(|e| BenchError::Rule(p.id, e.to_string()))
}

/// The disk plan: a verified, decoded cache hit (never a recompile).
pub fn disk_plan(p: &Pair) -> Result<Plan, BenchError> {
    let loaded = p
        .cache
        .load_or_compile(&p.digest, ENGINE, || {
            Err::<Vec<Plan>, _>("cache entry went missing".to_string())
        })
        .map_err(|e| BenchError::Rule(p.id, e))?;
    debug_assert!(matches!(loaded.source, Source::Cache));
    loaded
        .plans
        .into_iter()
        .next()
        .ok_or_else(|| BenchError::Rule(p.id, "cache entry holds no plan".to_string()))
}

/// Runs `plan` over `files` as `case` and returns the findings as one JSON value.
pub fn findings_json(
    case: &Case,
    plan: &Plan,
    files: &[Prepared],
) -> Result<serde_json::Value, BenchError> {
    let run_case = Case {
        id: case.id,
        plan: plan.clone(),
        edges: case.edges,
        hand: case.hand,
    };
    let mut out = Vec::new();
    for f in files {
        let found: Vec<_> = run_plan(&run_case, f)?
            .into_iter()
            .map(|(unresolved, n)| serde_json::json!({"unresolved": unresolved, "node": format!("{n:?}")}))
            .collect();
        out.push(serde_json::json!({"path": f.path, "findings": found}));
    }
    Ok(serde_json::json!({"rule": case.id, "files": out}))
}

/// One timed session: obtain a plan with `load`, then execute it over every file.
pub fn session(
    case: &Case,
    files: &[Prepared],
    load: impl Fn() -> Result<Plan, BenchError>,
) -> Result<usize, BenchError> {
    let run_case = Case {
        id: case.id,
        plan: load()?,
        edges: case.edges,
        hand: case.hand,
    };
    files
        .iter()
        .map(|f| run_plan(&run_case, f).map(|v| v.len()))
        .sum()
}

/// Median-of-`reps` wall time of `f`, after one warm-up.
pub fn median_time<T>(reps: u32, mut f: impl FnMut() -> T) -> Duration {
    std::hint::black_box(f());
    let mut ts: Vec<f64> = (0..reps)
        .map(|_| {
            let start = Instant::now();
            std::hint::black_box(f());
            start.elapsed().as_secs_f64()
        })
        .collect();
    Duration::from_secs_f64(median(&std::mem::take(&mut ts)))
}

/// The disk-over-compiled time ratio of one rule over `files`.
pub fn ratio(case: &Case, p: &Pair, files: &[Prepared], reps: u32) -> f64 {
    let compiled = median_time(reps, || session(case, files, || compiled_plan(p)));
    let disk = median_time(reps, || session(case, files, || disk_plan(p)));
    disk.as_secs_f64() / compiled.as_secs_f64().max(f64::EPSILON)
}
