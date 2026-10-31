//! Timing one scenario: cold run, warm-up, N warm runs, one peak-memory run, one `--timing` run.

use std::path::Path;
use std::time::Duration;

use gob_exec::{Outcome, Program, Runner, Spec};

use super::ProfileError;
use super::model::Entry;
use super::scenarios::Scenario;

/// Median of `samples` (mean of the middle pair for an even count), `None` when empty.
pub fn median(samples: &[f64]) -> Option<f64> {
    if samples.is_empty() {
        return None;
    }
    let mut s = samples.to_vec();
    s.sort_by(f64::total_cmp);
    let mid = s.len() / 2;
    Some(if s.len() % 2 == 1 {
        s[mid]
    } else {
        f64::midpoint(s[mid - 1], s[mid])
    })
}

/// Replace `{ticket}` in `args` with `ticket`.
pub fn expand(args: &[String], ticket: &str) -> Vec<String> {
    args.iter().map(|a| a.replace("{ticket}", ticket)).collect()
}

fn millis(d: Duration) -> f64 {
    d.as_secs_f64() * 1000.0
}

struct Run {
    timed_out: bool,
    exit: Option<i32>,
    wall_ms: f64,
    stdout: String,
}

fn run_once(
    runner: &Runner,
    program: Program,
    args: Vec<String>,
    cwd: &Path,
    timeout: Duration,
) -> Result<Run, ProfileError> {
    let label = program.label();
    let out = runner
        .run(&Spec {
            program,
            args,
            cwd: Some(cwd.to_path_buf()),
            env: vec![("NO_COLOR".to_owned(), "1".to_owned())],
            timeout,
            capture: true,
        })
        .map_err(|e| ProfileError::Spawn(format!("{label}: {e}")))?;
    Ok(Run {
        timed_out: out.status == Outcome::TimedOut,
        exit: match out.status {
            Outcome::Exited(c) => Some(c),
            Outcome::Signaled | Outcome::TimedOut => None,
        },
        wall_ms: millis(out.duration),
        stdout: out.stdout,
    })
}

/// Peak resident set in KiB of one run of `exe args`, through GNU `time -f %M` (Linux only).
fn peak_rss_kib(
    runner: &Runner,
    exe: &Path,
    args: &[String],
    cwd: &Path,
    timeout: Duration,
) -> Option<u64> {
    if !cfg!(target_os = "linux") {
        return None;
    }
    let holder = tempfile::NamedTempFile::new().ok()?;
    let out_file = holder.path().to_path_buf();
    let mut full = vec![
        "-f".to_owned(),
        "%M".to_owned(),
        "-o".to_owned(),
        gob_path::Shown::with_home(&out_file, None).to_string(),
        gob_path::Shown::with_home(exe, None).to_string(),
    ];
    full.extend(args.iter().cloned());
    let ran = run_once(
        runner,
        Program::Tool {
            name: "time".to_owned(),
        },
        full,
        cwd,
        timeout,
    );
    let text = std::fs::read_to_string(&out_file).ok();
    if let Err(e) = ran {
        tracing::warn!(error = %e, "peak memory run failed");
        return None;
    }
    // GNU time writes the requested line last, after any "Command exited with" note.
    text?.lines().last()?.trim().parse().ok()
}

/// Run `scenario` for `command` with `exe` in `cwd` and fill an [`Entry`].
///
/// # Errors
/// [`ProfileError::Spawn`] when the binary cannot be started.
pub fn measure(
    runner: &Runner,
    command: &str,
    exe: &Path,
    scenario: &Scenario,
    args: Vec<String>,
    cwd: &Path,
    runs: u32,
) -> Result<Entry, ProfileError> {
    let program = || Program::Hook {
        path: exe.to_path_buf(),
    };
    let timeout = scenario.timeout();
    let mut exits_ok = true;
    let mut last_exit = None;
    let timed_out = std::cell::Cell::new(false);
    let mut note = |run: &Run| {
        exits_ok &= run.exit.is_some_and(|c| scenario.exit.contains(&c));
        last_exit = run.exit;
        timed_out.set(timed_out.get() || run.timed_out);
    };
    let mut cold_ms = None;
    if scenario.cold {
        let cache = cwd.join(".frob");
        if cache.exists() {
            std::fs::remove_dir_all(&cache).map_err(|e| {
                ProfileError::Io(format!("{}: {e}", gob_path::Shown::with_home(&cache, None)))
            })?;
        }
        let run = run_once(runner, program(), args.clone(), cwd, timeout)?;
        note(&run);
        cold_ms = Some(run.wall_ms);
    }
    let runs = scenario.runs.map_or(runs, |cap| cap.min(runs));
    let mut samples = Vec::new();
    let aborted = || timed_out.get();
    // frob:ticket 01M69P2ZY0CQ2Q00FQFC7E9GDH
    // A timed-out run is not repeated: the rest would only time out again and burn the job.
    if !aborted() {
        let warmup = run_once(runner, program(), args.clone(), cwd, timeout)?;
        note(&warmup);
    }
    for _ in 0..runs {
        if aborted() {
            break;
        }
        let run = run_once(runner, program(), args.clone(), cwd, timeout)?;
        note(&run);
        samples.push(run.wall_ms);
    }
    if aborted() {
        tracing::warn!(
            command,
            timeout_s = timeout.as_secs(),
            "run timed out; scenario aborted"
        );
    }
    let max_rss_kib = if aborted() {
        None
    } else {
        peak_rss_kib(runner, exe, &args, cwd, timeout)
    };
    let timing = if scenario.timing && !aborted() {
        let mut with = args.clone();
        with.push("--timing".to_owned());
        with.push("--json".to_owned());
        let run = run_once(runner, program(), with, cwd, timeout)?;
        serde_json::from_str::<serde_json::Value>(&run.stdout)
            .ok()
            .and_then(|v| v.pointer("/data/timing").cloned())
    } else {
        None
    };
    tracing::info!(command, ?last_exit, warm = ?median(&samples), ?cold_ms, ?max_rss_kib, "measured");
    Ok(Entry {
        command: command.to_owned(),
        args,
        fixture: Some(scenario.fixture.name().to_owned()),
        skipped: None,
        exit: last_exit,
        exit_ok: exits_ok,
        warm_ms: median(&samples),
        samples_ms: samples,
        cold_ms,
        max_rss_kib,
        budget_ms: scenario.budget_ms,
        cold_budget_ms: scenario.cold_budget_ms,
        timing,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-dev/src/profile/measure.rs::median
    #[test]
    fn median_of_odd_even_and_empty() {
        assert_eq!(median(&[]), None);
        assert_eq!(median(&[3.0, 1.0, 2.0]), Some(2.0));
        assert_eq!(median(&[4.0, 1.0, 2.0, 3.0]), Some(2.5));
    }

    // frob:tests crates/gob-dev/src/profile/measure.rs::expand
    #[test]
    fn ticket_placeholder_expands() {
        let args = vec![
            "ticket".to_owned(),
            "show".to_owned(),
            "{ticket}".to_owned(),
        ];
        assert_eq!(expand(&args, "~ABC"), ["ticket", "show", "~ABC"]);
    }

    #[cfg(unix)]
    fn shell_scenario(exit: &[i32], cold: bool) -> Scenario {
        Scenario {
            args: Vec::new(),
            fixture: crate::profile::scenarios::FixtureKind::Tmp,
            readonly: true,
            cold,
            timing: false,
            runs: None,
            timeout_s: None,
            exit: exit.to_vec(),
            budget_ms: Some(500),
            cold_budget_ms: Some(500),
            skip: None,
        }
    }

    // frob:tests crates/gob-dev/src/profile/measure.rs::measure
    #[cfg(unix)]
    #[test]
    fn measure_times_runs_checks_exit_codes_and_clears_the_cold_cache() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::create_dir(tmp.path().join(".frob")).unwrap();
        let runner = Runner::new(gob_exec::Limits { jobs: 1 });
        let args = vec!["-c".to_owned(), "exit 3".to_owned()];
        let sh = Path::new("/bin/sh");
        let ok = measure(
            &runner,
            "x y",
            sh,
            &shell_scenario(&[3], true),
            args.clone(),
            tmp.path(),
            4,
        )
        .unwrap();
        assert!(ok.exit_ok && ok.exit == Some(3));
        assert_eq!(ok.samples_ms.len(), 4);
        assert!(ok.cold_ms.is_some() && ok.warm_ms.is_some());
        assert!(
            !tmp.path().join(".frob").exists(),
            "cold run must delete .frob"
        );
        let bad = measure(
            &runner,
            "x y",
            sh,
            &shell_scenario(&[0], false),
            args,
            tmp.path(),
            1,
        )
        .unwrap();
        assert!(!bad.exit_ok && bad.cold_ms.is_none());
    }

    // frob:tests crates/gob-dev/src/profile/measure.rs::measure
    // frob:ticket 01M69P2ZY0CQ2Q00FQFC7E9GDH
    #[cfg(unix)]
    #[test]
    fn a_timed_out_run_aborts_the_scenario_after_one_run() {
        let tmp = tempfile::tempdir().unwrap();
        let runner = Runner::new(gob_exec::Limits { jobs: 1 });
        let args = vec!["-c".to_owned(), "echo x >> n; sleep 30".to_owned()];
        let mut scenario = shell_scenario(&[0], false);
        scenario.timeout_s = Some(1);
        let entry = measure(
            &runner,
            "x y",
            Path::new("/bin/sh"),
            &scenario,
            args,
            tmp.path(),
            3,
        )
        .unwrap();
        assert!(!entry.exit_ok && entry.exit.is_none());
        assert!(entry.samples_ms.is_empty());
        let runs = std::fs::read_to_string(tmp.path().join("n")).unwrap();
        assert_eq!(runs.lines().count(), 1, "only the first run may start");
    }
}
