//! `Repo::discover_shared` opens a path once while a `DiscoverScope` is live.

use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};

use gob_git::{DiscoverScope, Repo};

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

// frob:ticket 01M56M6YM7DZTNXT65BP75ES1Y
// frob:tests crates/gob-git/src/session.rs::DiscoverScope
#[test]
fn shared_discover_opens_a_path_once_only_inside_a_scope() {
    let dir = tempfile::tempdir().expect("tmp");
    Repo::init(dir.path()).expect("init");
    assert_scoped_sharing(dir.path(), &Opens::default());
}

/// Asserts `discover_shared` opens `path` once per call outside a scope and once inside one.
fn assert_scoped_sharing(path: &std::path::Path, opens: &Opens) {
    tracing::subscriber::with_default(opens.clone(), || count_opens(path, opens));
}

/// The open-count assertions behind [`assert_scoped_sharing`], run under the counting subscriber.
fn count_opens(path: &std::path::Path, opens: &Opens) {
    Repo::discover_shared(path).expect("open");
    Repo::discover_shared(path).expect("open");
    assert_eq!(opens.0.load(Ordering::SeqCst), 2, "no scope: no sharing");

    let scope = DiscoverScope::begin();
    Repo::discover_shared(path).expect("open");
    Repo::discover_shared(path).expect("open");
    Repo::discover_shared(path).expect("open");
    assert_eq!(opens.0.load(Ordering::SeqCst), 3, "one open inside a scope");
    drop(scope);

    Repo::discover_shared(path).expect("open");
    assert_eq!(
        opens.0.load(Ordering::SeqCst),
        4,
        "the scope forgot the handle"
    );
}
