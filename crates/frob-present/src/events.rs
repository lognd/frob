//! Stage events: the data form producers emit as `tracing` events (docs/design/output.md section 5).
//!
//! Producers never hold a [`crate::Presenter`]; they call these functions and a layer translates
//! the events. Fields: `stage`, `phase = start|progress|end`, `done`, `total`, `elapsed_ms`,
//! `outcome`, `ui = true`, all on target [`TARGET`].

use std::time::Duration;

use crate::stage::Outcome;

/// The `tracing` target of every stage event.
pub const TARGET: &str = "frob::stage";

/// Emit the start of stage `stage`; `total` is the known step count when there is one.
pub fn emit_start(stage: &str, total: Option<u64>) {
    tracing::info!(
        target: "frob::stage",
        ui = true,
        stage,
        phase = "start",
        total = total.unwrap_or(0),
        "stage start"
    );
}

/// Emit progress `done` inside stage `stage`.
pub fn emit_progress(stage: &str, done: u64) {
    tracing::info!(
        target: "frob::stage",
        ui = true,
        stage,
        phase = "progress",
        done,
        "stage progress"
    );
}

/// Emit the end of stage `stage` with its measured duration and outcome.
pub fn emit_end(stage: &str, elapsed: Duration, outcome: Outcome) {
    tracing::info!(
        target: "frob::stage",
        ui = true,
        stage,
        phase = "end",
        elapsed_ms = u64::try_from(elapsed.as_millis()).unwrap_or(u64::MAX),
        outcome = outcome.label(),
        "stage end"
    );
}

/// Run `f` as stage `stage`: emit start, run, emit end (ok) with the measured wall time.
pub fn timed<T>(stage: &str, f: impl FnOnce() -> T) -> (T, Duration) {
    emit_start(stage, None);
    let timer = std::time::Instant::now();
    let value = f();
    let took = timer.elapsed();
    emit_end(stage, took, Outcome::Ok);
    (value, took)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, Mutex};
    use tracing::field::{Field, Visit};
    use tracing_subscriber::Layer;
    use tracing_subscriber::layer::{Context, SubscriberExt};

    #[derive(Default)]
    struct Grab(Vec<(String, String)>);
    impl Visit for Grab {
        fn record_debug(&mut self, f: &Field, v: &dyn std::fmt::Debug) {
            self.0.push((f.name().to_owned(), format!("{v:?}")));
        }
    }

    type Seen = Vec<(String, Vec<(String, String)>)>;
    struct Sink(Arc<Mutex<Seen>>);
    impl<S: tracing::Subscriber> Layer<S> for Sink {
        fn on_event(&self, e: &tracing::Event<'_>, _: Context<'_, S>) {
            let mut g = Grab::default();
            e.record(&mut g);
            self.0
                .lock()
                .unwrap()
                .push((e.metadata().target().to_owned(), g.0));
        }
    }

    fn capture(f: impl FnOnce()) -> Seen {
        let seen = Arc::new(Mutex::new(Vec::new()));
        let sub = tracing_subscriber::registry().with(Sink(seen.clone()));
        tracing::subscriber::with_default(sub, f);
        std::mem::take(&mut *seen.lock().unwrap())
    }

    fn field<'a>(fields: &'a [(String, String)], name: &str) -> Option<&'a str> {
        fields
            .iter()
            .find(|(k, _)| k == name)
            .map(|(_, v)| v.as_str())
    }

    // frob:tests crates/frob-present/src/events.rs::timed
    #[test]
    fn stage_events_timed_emits_start_then_end_on_the_stage_target() {
        let events = capture(|| {
            let (v, _) = timed("land.merge", || 7);
            assert_eq!(v, 7);
        });
        assert_eq!(events.len(), 2);
        assert!(events.iter().all(|(t, _)| t == TARGET));
        assert_eq!(field(&events[0].1, "phase"), Some("\"start\""));
        assert_eq!(field(&events[0].1, "stage"), Some("\"land.merge\""));
        assert_eq!(field(&events[0].1, "ui"), Some("true"));
        assert_eq!(field(&events[1].1, "phase"), Some("\"end\""));
        assert_eq!(field(&events[1].1, "outcome"), Some("\"ok\""));
        assert!(field(&events[1].1, "elapsed_ms").is_some());
    }

    // frob:tests crates/frob-present/src/events.rs::emit_end
    #[test]
    fn stage_events_end_carries_duration_and_outcome() {
        let events =
            capture(|| emit_end("check.rules", Duration::from_millis(42), Outcome::Failed));
        assert_eq!(field(&events[0].1, "elapsed_ms"), Some("42"));
        assert_eq!(field(&events[0].1, "outcome"), Some("\"failed\""));
    }
}
