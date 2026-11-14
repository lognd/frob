//! Runner behaviour: timeout, concurrency bound, allowlist, spawn counts.

use std::time::Duration;

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

/// Spin (yielding, no wall clock) until `cond` holds or the attempt budget runs out; the last verdict.
fn settle(mut cond: impl FnMut() -> bool) -> bool {
    for _ in 0..20_000_000u32 {
        if cond() {
            return true;
        }
        std::thread::yield_now();
    }
    cond()
}

#[cfg(unix)]
#[test]
fn timeout_kills_group() {
    if !gob_exec::require_sh("timeout_kills_group") {
        return;
    }
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
    let out = runner.run(&spec).unwrap();
    assert_eq!(out.status, Outcome::TimedOut);
}

#[cfg(unix)]
#[test]
fn timeout_kills_direct_child() {
    let runner = Runner::new(Limits { jobs: 2 });
    let direct = runner
        .run(&sleep_spec("5", Duration::from_millis(100)))
        .unwrap();
    assert_eq!(direct.status, Outcome::TimedOut);
    eprintln!("direct kill took {:?}", direct.duration);
}

#[cfg(unix)]
#[test]
fn timeout_leaves_no_grandchild() {
    if !gob_exec::require_sh("timeout_leaves_no_grandchild") {
        return;
    }
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
    // Wait for the kernel to reap, then the pid must not be live.
    if pid_dead(pid).is_some() {
        assert!(
            settle(|| pid_dead(pid) == Some(true)),
            "grandchild {pid} alive"
        );
    }
}

/// Run four 0.2 s sleeps at once on `runner` and collect the outputs.
fn run_four_sleeps(runner: &Runner) -> Vec<gob_exec::Output> {
    std::thread::scope(|s| {
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
    })
}

#[test]
fn concurrency_is_bounded_by_jobs() {
    let runner = Runner::new(Limits { jobs: 2 });
    let outs = run_four_sleeps(&runner);
    assert!(outs.iter().all(|o| o.status == Outcome::Exited(0)));
    let max = max_concurrency(&outs);
    assert!(max <= 2, "observed concurrency {max}");
    assert_eq!(runner.spawn_count(), SpawnCount(4));
}

/// Peak number of overlapping runs among `outs`.
fn max_concurrency(outs: &[gob_exec::Output]) -> i32 {
    let base = outs.iter().map(|o| o.started).min().unwrap();
    let mut events: Vec<(Duration, i32)> = Vec::new();
    for o in outs {
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
    max
}

#[test]
fn unlisted_program_is_not_allowed() {
    let runner = Runner::new(Limits { jobs: 1 }).allow_tools(["git-lfs".to_owned()]);
    let err = runner
        .run(&sleep_spec("0", Duration::from_secs(1)))
        .unwrap_err();
    assert!(matches!(err, ExecError::NotAllowed { .. }), "{err:?}");
}

#[test]
fn path_like_program_is_not_allowed() {
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
    if !gob_exec::require_sh("captured_output_is_redacted_and_env_added") {
        return;
    }
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
    if !gob_exec::require_sh("a_flooding_child_is_killed_at_the_output_cap_with_a_typed_error") {
        return;
    }
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec!["-c".into(), "yes aaaaaaaaaaaaaaaa".into()],
        cwd: None,
        env: vec![],
        timeout: Duration::from_secs(30),
        capture: true,
    };
    let err = Runner::new(Limits { jobs: 1 })
        .output_cap(1024 * 1024)
        .run(&spec)
        .unwrap_err();
    assert!(
        matches!(err, ExecError::OutputCap { limit } if limit == 1024 * 1024),
        "{err:?}"
    );
}

// frob:tests crates/gob-exec/src/runner.rs::Runner.output_cap
#[test]
fn output_under_the_cap_is_returned_whole() {
    if !gob_exec::require_sh("output_under_the_cap_is_returned_whole") {
        return;
    }
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
    if !gob_exec::require_sh("timeout_kills_setsid_grandchild_and_returns_promptly") {
        return;
    }
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
    let out = runner.run(&spec).unwrap();
    assert_eq!(out.status, Outcome::TimedOut);
    let pid = out.stdout.trim();
    assert!(!pid.is_empty(), "grandchild pid should have been captured");
    if pid_dead(pid).is_some() {
        assert!(
            settle(|| pid_dead(pid) == Some(true)),
            "setsid grandchild {pid} survived the timeout"
        );
    }
}

// frob:ticket 01M4CTDYG696JWM20AZPYFAH0T
#[cfg(unix)]
#[test]
fn normal_exit_does_not_block_on_pipe_held_by_background_child() {
    if !gob_exec::require_sh("normal_exit_does_not_block_on_pipe_held_by_background_child") {
        return;
    }
    let runner = Runner::new(Limits { jobs: 1 });
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec!["-c".into(), "setsid sleep 30 & echo $!; echo out".into()],
        cwd: None,
        env: vec![],
        timeout: Duration::from_secs(10),
        capture: true,
    };
    let out = runner.run(&spec).unwrap();
    assert_eq!(out.status, Outcome::Exited(0));
    assert!(
        out.stdout.contains("out"),
        "partial output kept: {:?}",
        out.stdout
    );
    out.stdout.lines().next().into_iter().for_each(|pid| {
        std::process::Command::new("kill").arg(pid).status().ok();
    });
}

// frob:ticket 01M4DYPFE1Z7MXVNG8MJ7N30N5
// frob:tests crates/gob-exec/src/runner.rs::Runner.run_with_env
#[test]
fn a_secret_looking_stdout_payload_is_intact_while_the_transcript_stdout_and_stderr_are_redacted() {
    if !gob_exec::require_sh(
        "a_secret_looking_stdout_payload_is_intact_while_the_transcript_stdout_and_stderr_are_redacted",
    ) {
        return;
    }
    let runner = Runner::new(Limits { jobs: 1 });
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec![
            "-c".into(),
            "echo 'a { --secret=hunter2abc; }'; echo 'password=hunter2abc' >&2".into(),
        ],
        cwd: None,
        env: vec![],
        timeout: Duration::from_secs(5),
        capture: true,
    };
    let out = runner.run(&spec).unwrap();
    assert_eq!(out.stdout_raw.trim(), "a { --secret=hunter2abc; }");
    assert!(!out.stdout.contains("hunter2abc"), "{}", out.stdout);
    assert!(!out.stderr.contains("hunter2abc"), "{}", out.stderr);
}

// frob:ticket 01M5D5PZP5BZFRWT9W86STF8MV
// frob:tests crates/gob-exec/src/runner.rs::Runner.spawn_detached
#[cfg(unix)]
#[test]
fn spawn_detached_returns_at_once_and_the_child_finishes_on_its_own() {
    if !gob_exec::require_sh("spawn_detached_returns_at_once_and_the_child_finishes_on_its_own") {
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    // A fifo: the child blocks opening it until this test reads, so a spawn that waited for the
    // child would hang, and no clock is needed to know the child finished.
    let marker = dir.path().join("marker");
    let made = std::process::Command::new("mkfifo").arg(&marker).status();
    if !made.is_ok_and(|s| s.success()) {
        return;
    }
    let runner = Runner::new(Limits { jobs: 1 });
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec!["-c".into(), "echo \"$KICK\" > marker".into()],
        cwd: Some(dir.path().to_path_buf()),
        env: vec![("KICK".into(), "1".into())],
        timeout: Duration::from_secs(5),
        capture: false,
    };
    let pid = runner
        .spawn_detached(&spec, &gob_exec::EnvPolicy::Inherit)
        .unwrap();
    assert!(pid > 0);
    assert_eq!(runner.spawn_count(), SpawnCount(1));
    assert_eq!(std::fs::read_to_string(&marker).unwrap().trim(), "1");
}

// frob:ticket 01M5D5PZP5BZFRWT9W86STF8MV
// frob:tests crates/gob-exec/src/runner.rs::Runner.spawn_detached
#[test]
fn spawn_detached_refuses_a_tool_off_the_allowlist_and_a_missing_hook() {
    let runner = Runner::new(Limits { jobs: 1 }).allow_tools(["git".to_owned()]);
    let mut spec = sleep_spec("1", Duration::from_secs(1));
    let denied = runner.spawn_detached(&spec, &gob_exec::EnvPolicy::Inherit);
    assert!(matches!(denied, Err(ExecError::NotAllowed { .. })));
    spec.program = Program::Hook {
        path: "/nonexistent/frob-hook".into(),
    };
    let missing = runner.spawn_detached(&spec, &gob_exec::EnvPolicy::Inherit);
    assert!(matches!(missing, Err(ExecError::NotFound { .. })));
    assert_eq!(runner.spawn_count(), SpawnCount(0));
}

/// True when `tasklist` still lists `pid` (Windows only).
#[cfg(windows)]
fn windows_pid_alive(pid: &str) -> bool {
    let out = std::process::Command::new("tasklist")
        .args(["/FI", &format!("PID eq {pid}"), "/NH"])
        .output()
        .expect("tasklist runs");
    String::from_utf8_lossy(&out.stdout)
        .split_whitespace()
        .any(|w| w == pid)
}

// frob:ticket 01M4K8HPCVY5Q40KWRW70G51Q4
#[cfg(windows)]
#[test]
fn windows_timeout_kills_descendants() {
    // The pid goes through a file in the run's cwd: a killed PowerShell may never flush its
    // stdout pipe, and no path is turned into text.
    let dir = tempfile::tempdir().expect("tempdir");
    let runner = Runner::new(Limits { jobs: 1 });
    let script = "$p = Start-Process ping -ArgumentList '-n','30','127.0.0.1' -PassThru \
         -WindowStyle Hidden; Set-Content -Path pid.txt -Value $p.Id -Encoding ascii; \
         Start-Sleep 30";
    let spec = Spec {
        program: Program::Tool {
            name: "powershell".into(),
        },
        args: vec!["-NoProfile".into(), "-Command".into(), script.into()],
        cwd: Some(dir.path().to_path_buf()),
        env: vec![],
        timeout: Duration::from_secs(20),
        capture: true,
    };
    let out = runner.run(&spec).unwrap();
    assert_eq!(out.status, Outcome::TimedOut);
    let text = std::fs::read_to_string(dir.path().join("pid.txt")).unwrap_or_default();
    let pid = text.trim();
    assert!(!pid.is_empty(), "grandchild pid should have been captured");
    assert!(
        settle(|| !windows_pid_alive(pid)),
        "descendant {pid} survived the timeout"
    );
}

// frob:tests crates/gob-exec/src/runner.rs::set_ambient_env
#[cfg(unix)]
#[test]
fn ambient_env_reaches_children_and_spec_env_wins() {
    if !gob_exec::require_sh("ambient_env_reaches_children_and_spec_env_wins") {
        return;
    }
    gob_exec::set_ambient_env("GOB_EXEC_AMBIENT_PROBE", "ambient");
    gob_exec::set_ambient_env("GOB_EXEC_AMBIENT_BOTH", "ambient");
    let runner = Runner::new(Limits { jobs: 1 });
    let spec = Spec {
        program: Program::Tool { name: "sh".into() },
        args: vec![
            "-c".into(),
            "echo $GOB_EXEC_AMBIENT_PROBE $GOB_EXEC_AMBIENT_BOTH".into(),
        ],
        cwd: None,
        env: vec![("GOB_EXEC_AMBIENT_BOTH".into(), "spec".into())],
        timeout: Duration::from_secs(10),
        capture: true,
    };
    let out = runner.run(&spec).unwrap();
    assert_eq!(out.stdout.trim(), "ambient spec");
}
