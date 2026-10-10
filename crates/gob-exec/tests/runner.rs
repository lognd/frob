//! Runner behaviour: timeout, concurrency bound, allowlist, spawn counts.

use std::time::{Duration, Instant};

use gob_exec::{ExecError, Limits, Outcome, Program, Runner, SpawnCount, Spec, assert_spawns};

fn sleep_spec(secs: &str, timeout: Duration) -> Spec {
    Spec {
        program: Program::Tool {
            name: "sleep".into(),
        },
        args: vec![secs.into()],
        cwd: None,
        env: vec![],
        timeout,
        capture: true,
    }
}

#[cfg(unix)]
#[test]
fn timeout_kills_group() {
    let runner = Runner::new(Limits { jobs: 2 });
    // sh forks a grandchild sleep; the group kill must take it down too.
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec!["-c".into(), "sleep 5 & echo $! ; wait".into()],
        cwd: None,
        env: vec![],
        timeout: Duration::from_millis(100),
        capture: false,
    };
    let t = Instant::now();
    let out = runner.run(&spec).unwrap();
    assert_eq!(out.status, Outcome::TimedOut);
    eprintln!("group kill took {:?}", t.elapsed());

    let direct = runner
        .run(&sleep_spec("5", Duration::from_millis(100)))
        .unwrap();
    assert_eq!(direct.status, Outcome::TimedOut);
    eprintln!("direct kill took {:?}", direct.duration);
}

#[cfg(unix)]
#[test]
fn timeout_leaves_no_grandchild() {
    let runner = Runner::new(Limits { jobs: 1 });
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec!["-c".into(), "sleep 5 & echo $!; wait".into()],
        cwd: None,
        env: vec![],
        timeout: Duration::from_millis(300),
        capture: true,
    };
    let out = runner.run(&spec).unwrap();
    assert_eq!(out.status, Outcome::TimedOut);
    let pid = out.stdout.trim();
    assert!(!pid.is_empty(), "grandchild pid should have been captured");
    // Give the kernel a moment to reap, then the pid must not be live.
    std::thread::sleep(Duration::from_millis(100));
    let alive = std::path::Path::new("/proc").join(pid).join("stat");
    if std::path::Path::new("/proc/self").exists() {
        let stat = std::fs::read_to_string(alive).unwrap_or_default();
        assert!(
            stat.is_empty() || stat.contains(") Z "),
            "grandchild alive: {stat}"
        );
    }
}

#[test]
fn concurrency_is_bounded_by_jobs() {
    let runner = Runner::new(Limits { jobs: 2 });
    let outs: Vec<_> = std::thread::scope(|s| {
        let hs: Vec<_> = (0..4)
            .map(|_| {
                s.spawn(|| {
                    runner
                        .run(&sleep_spec("0.2", Duration::from_secs(5)))
                        .unwrap()
                })
            })
            .collect();
        hs.into_iter().map(|h| h.join().unwrap()).collect()
    });
    let base = outs.iter().map(|o| o.started).min().unwrap();
    let mut events: Vec<(Duration, i32)> = Vec::new();
    for o in &outs {
        assert_eq!(o.status, Outcome::Exited(0));
        let s = o.started - base;
        events.push((s, 1));
        events.push((s + o.duration, -1));
    }
    // Ends sort before starts at equal instants.
    events.sort_by_key(|&(t, d)| (t, d));
    let (mut cur, mut max) = (0, 0);
    for (_, d) in events {
        cur += d;
        max = max.max(cur);
    }
    assert!(max <= 2, "observed concurrency {max}");
    assert_eq!(runner.spawn_count(), SpawnCount(4));
}

#[test]
fn unlisted_program_is_not_allowed() {
    let runner = Runner::new(Limits { jobs: 1 }).allow_tools(["git-lfs".to_owned()]);
    let err = runner
        .run(&sleep_spec("0", Duration::from_secs(1)))
        .unwrap_err();
    assert!(matches!(err, ExecError::NotAllowed { .. }), "{err:?}");

    let path_like = Spec {
        program: Program::Tool {
            name: "/bin/sleep".into(),
        },
        ..sleep_spec("0", Duration::from_secs(1))
    };
    let err = Runner::new(Limits { jobs: 1 }).run(&path_like).unwrap_err();
    assert!(matches!(err, ExecError::NotAllowed { .. }), "{err:?}");
}

#[test]
fn missing_tool_is_not_found() {
    let spec = Spec {
        program: Program::Tool {
            name: "definitely-not-a-real-tool-xyz".into(),
        },
        ..sleep_spec("0", Duration::from_secs(1))
    };
    let err = Runner::new(Limits { jobs: 1 }).run(&spec).unwrap_err();
    assert!(matches!(err, ExecError::NotFound { .. }), "{err:?}");
}

#[test]
fn spawn_counter_counts_only_real_spawns() {
    let runner = Runner::new(Limits { jobs: 1 });
    let g0 = SpawnCount::global();
    assert_spawns(2, || {
        runner
            .run(&sleep_spec("0", Duration::from_secs(5)))
            .unwrap();
        runner
            .run(&sleep_spec("0", Duration::from_secs(5)))
            .unwrap();
    });
    assert_spawns(0, || {
        let bad = Spec {
            program: Program::Tool {
                name: "nope-xyz".into(),
            },
            ..sleep_spec("0", Duration::from_secs(1))
        };
        assert!(runner.run(&bad).is_err());
    });
    assert_eq!(runner.spawn_count(), SpawnCount(2));
    assert!(SpawnCount::global().since(g0) >= 2);
}

#[test]
fn captured_output_is_redacted_and_env_added() {
    let runner = Runner::new(Limits { jobs: 1 });
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec![
            "-c".into(),
            "echo hello $FROB_T9; echo oops >&2; exit 3".into(),
        ],
        cwd: None,
        env: vec![("FROB_T9".into(), "world".into())],
        timeout: Duration::from_secs(5),
        capture: true,
    };
    let out = runner.run(&spec).unwrap();
    assert_eq!(out.status, Outcome::Exited(3));
    assert_eq!(out.stdout.trim(), "hello world");
    assert_eq!(out.stderr.trim(), "oops");
}

// frob:tests crates/gob-exec/src/runner.rs::Runner.output_cap
#[test]
fn a_flooding_child_is_killed_at_the_output_cap_with_a_typed_error() {
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec!["-c".into(), "yes aaaaaaaaaaaaaaaa".into()],
        cwd: None,
        env: vec![],
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let started = Instant::now();
    let err = Runner::new(Limits { jobs: 1 })
        .output_cap(1024 * 1024)
        .run(&spec)
        .unwrap_err();
    assert!(
        matches!(err, ExecError::OutputCap { limit } if limit == 1024 * 1024),
        "{err:?}"
    );
    assert!(
        started.elapsed() < Duration::from_secs(10),
        "killed promptly"
    );
}

// frob:tests crates/gob-exec/src/runner.rs::Runner.output_cap
#[test]
fn output_under_the_cap_is_returned_whole() {
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec!["-c".into(), "echo small".into()],
        cwd: None,
        env: vec![],
        timeout: Duration::from_secs(5),
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .output_cap(16)
        .run(&spec)
        .unwrap();
    assert_eq!(out.stdout.trim(), "small");
}

// frob:ticket 01M4CTDYG696JWM20AZPYFAH0T
/// True when `pid` is gone or a zombie (Linux `/proc`); `None` where `/proc` is absent.
#[cfg(unix)]
fn pid_dead(pid: &str) -> Option<bool> {
    if !std::path::Path::new("/proc/self").exists() {
        return None;
    }
    let stat = std::fs::read_to_string(std::path::Path::new("/proc").join(pid).join("stat"))
        .unwrap_or_default();
    Some(stat.is_empty() || stat.contains(") Z "))
}

// frob:ticket 01M4CTDYG696JWM20AZPYFAH0T
#[cfg(unix)]
#[test]
fn timeout_kills_setsid_grandchild_and_returns_promptly() {
    let runner = Runner::new(Limits { jobs: 1 });
    // The grandchild leaves the process group and keeps the capture pipes open for 30 s.
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec!["-c".into(), "setsid sleep 30 & echo $!; wait".into()],
        cwd: None,
        env: vec![],
        timeout: Duration::from_millis(300),
        capture: true,
    };
    let t = Instant::now();
    let out = runner.run(&spec).unwrap();
    let took = t.elapsed();
    assert_eq!(out.status, Outcome::TimedOut);
    assert!(
        took < Duration::from_millis(300) + Duration::from_secs(2),
        "run took {took:?}"
    );
    let pid = out.stdout.trim();
    assert!(!pid.is_empty(), "grandchild pid should have been captured");
    std::thread::sleep(Duration::from_millis(100));
    if let Some(dead) = pid_dead(pid) {
        assert!(dead, "setsid grandchild {pid} survived the timeout");
    }
}

// frob:ticket 01M4CTDYG696JWM20AZPYFAH0T
#[cfg(unix)]
#[test]
fn normal_exit_does_not_block_on_pipe_held_by_background_child() {
    let runner = Runner::new(Limits { jobs: 1 });
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec!["-c".into(), "setsid sleep 30 & echo $!; echo out".into()],
        cwd: None,
        env: vec![],
        timeout: Duration::from_secs(10),
        capture: true,
    };
    let t = Instant::now();
    let out = runner.run(&spec).unwrap();
    assert_eq!(out.status, Outcome::Exited(0));
    assert!(t.elapsed() < Duration::from_secs(5), "join was not bounded");
    assert!(
        out.stdout.contains("out"),
        "partial output kept: {:?}",
        out.stdout
    );
    if let Some(pid) = out.stdout.lines().next() {
        let _ = std::process::Command::new("kill").arg(pid).status();
    }
}
