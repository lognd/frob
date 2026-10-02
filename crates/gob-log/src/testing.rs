//! Test-only helper that records tracing events for assertions.

use std::fmt::Write as _;
use std::sync::{Arc, Mutex};

use tracing::field::{Field, Visit};
use tracing::{Event, Level, Subscriber};
use tracing_subscriber::layer::{Context, SubscriberExt};
use tracing_subscriber::{EnvFilter, Layer};

/// One recorded event.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CapturedEvent {
    /// Event level.
    pub level: Level,
    /// Event target (module path by default).
    pub target: String,
    /// The `message` field, empty if absent.
    pub message: String,
    /// Other fields as `name=value` strings in emission order.
    pub fields: Vec<(String, String)>,
}

#[derive(Default)]
struct FieldVisitor {
    message: String,
    fields: Vec<(String, String)>,
}

impl Visit for FieldVisitor {
    fn record_debug(&mut self, field: &Field, value: &dyn std::fmt::Debug) {
        if field.name() == "message" {
            let _ = write!(self.message, "{value:?}");
        } else {
            self.fields
                .push((field.name().to_owned(), format!("{value:?}")));
        }
    }
}

struct Recorder(Arc<Mutex<Vec<CapturedEvent>>>);

impl<S: Subscriber> Layer<S> for Recorder {
    fn on_event(&self, event: &Event<'_>, _ctx: Context<'_, S>) {
        let mut v = FieldVisitor::default();
        event.record(&mut v);
        let meta = event.metadata();
        self.0
            .lock()
            .expect("capture buffer lock is never poisoned")
            .push(CapturedEvent {
                level: *meta.level(),
                target: meta.target().to_owned(),
                message: v.message,
                fields: v.fields,
            });
    }
}

/// Runs `f` under a thread-local subscriber filtered by `filter`
/// (`FROB_LOG` syntax) and returns the events it emitted.
///
/// # Panics
///
/// Panics if `filter` does not parse; that is a bug in the calling test.
pub fn capture<F: FnOnce()>(filter: &str, f: F) -> Vec<CapturedEvent> {
    let buf = Arc::new(Mutex::new(Vec::new()));
    let subscriber = tracing_subscriber::registry().with(
        Recorder(Arc::clone(&buf))
            .with_filter(EnvFilter::try_new(filter).expect("test filter must parse")),
    );
    tracing::subscriber::with_default(subscriber, f);
    let out = buf.lock().expect("capture buffer lock is never poisoned");
    out.clone()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn filter_limits_events_to_matching_target_and_level() {
        let events = capture("gob_git=debug", || {
            tracing::debug!(target: "gob_git", n = 1, "wanted");
            tracing::trace!(target: "gob_git", "too verbose");
            tracing::debug!(target: "gob_exec", "other target");
            tracing::error!(target: "gob_exec", "also other target");
        });
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].message, "wanted");
        assert_eq!(events[0].target, "gob_git");
        assert_eq!(events[0].fields, vec![("n".to_owned(), "1".to_owned())]);
    }

    #[test]
    fn plain_level_filter_admits_everything_at_or_above() {
        let events = capture("warn", || {
            tracing::info!("no");
            tracing::warn!("yes");
        });
        assert_eq!(events.len(), 1);
    }
}
