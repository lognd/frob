//! A `DiscoverScope` makes one check run open its work tree fewer times than without.

use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};

use frob_check::{CheckOptions, run};
use gob_git::DiscoverScope;

/// Counts `repository discovered` events on the thread that installs it.
#[derive(Clone, Default)]
struct Opens(Arc<AtomicUsize>);

impl tracing::Subscriber for Opens {
    fn enabled(&self, _: &tracing::Metadata<'_>) -> bool {
        true
    }
    fn new_span(&self, _: &tracing::span::Attributes<'_>) -> tracing::span::Id {
        tracing::span::Id::from_u64(1)
    }
    fn record(&self, _: &tracing::span::Id, _: &tracing::span::Record<'_>) {}
    fn record_follows_from(&self, _: &tracing::span::Id, _: &tracing::span::Id) {}
    fn enter(&self, _: &tracing::span::Id) {}
    fn exit(&self, _: &tracing::span::Id) {}
    fn event(&self, event: &tracing::Event<'_>) {
        struct V(bool);
        impl tracing::field::Visit for V {
            fn record_debug(&mut self, f: &tracing::field::Field, v: &dyn std::fmt::Debug) {
                if f.name() == "message" && format!("{v:?}") == "repository discovered" {
                    self.0 = true;
                }
            }
        }
        let mut v = V(false);
        event.record(&mut v);
        if v.0 {
            self.0.fetch_add(1, Ordering::SeqCst);
        }
    }
}

/// Run `git args` in `root` as a fixed identity, asserting success.
fn git_in(root: &std::path::Path, args: &[&str]) {
    let out = std::process::Command::new("git")
        .current_dir(root)
        .args(["-c", "user.name=T", "-c", "user.email=t@example.com"])
        .args(args)
        .output()
        .expect("git runs");
    assert!(out.status.success(), "git {args:?}: {out:?}");
}

/// A committed one-file repository.
fn fixture() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path();
    git_in(root, &["init", "-q"]);
    std::fs::write(root.join("frob.toml"), "").expect("write");
    std::fs::write(root.join("a.txt"), "a\n").expect("write");
    git_in(root, &["add", "-A"]);
    git_in(root, &["commit", "-q", "-m", "init"]);
    dir
}

/// Discoveries one check run of `root` logs on this thread.
fn opens_of(root: &std::path::Path) -> usize {
    let opens = Opens::default();
    let options = CheckOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    tracing::subscriber::with_default(opens.clone(), || {
        run(root, &options).expect("run");
    });
    opens.0.load(Ordering::SeqCst)
}

/// Discoveries one check run of `root` logs inside a `DiscoverScope`.
fn scoped_opens_of(root: &std::path::Path) -> usize {
    let _scope = DiscoverScope::begin();
    opens_of(root)
}

// frob:ticket 01M56M6YM7DZTNXT65BP75ES1Y
// frob:tests crates/frob-check/src/snapshot.rs::open_ledger
#[test]
fn a_check_run_opens_the_work_tree_fewer_times_inside_a_discover_scope() {
    let dir = fixture();
    let plain = opens_of(dir.path());
    let scoped = scoped_opens_of(dir.path());
    assert!(scoped < plain, "scoped {scoped} opens vs plain {plain}");
}
