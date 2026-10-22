//! Panic containment: run a closure so a panic becomes a value, never an aborted corpus run.
//!
//! `catch_unwind` alone leaves the default hook printing every contained panic to stderr, and the
//! hook is process-global while `cargo test` runs tests on parallel threads. A single wrapper hook
//! is installed once; it stays silent only for panics on a thread that is inside [`contained`]
//! (tracked in a thread-local) and delegates to the previous hook for every other thread, so a
//! genuine failure in a sibling test still prints.

// frob:ticket 01M48PC1C64V7SN640NSASXGW5

use std::any::Any;
use std::cell::{Cell, RefCell};
use std::panic::{AssertUnwindSafe, PanicHookInfo, catch_unwind};
use std::sync::Once;

thread_local! {
    /// True while this thread is inside [`contained`]; the wrapper hook stays silent then.
    static CONTAINING: Cell<bool> = const { Cell::new(false) };
    /// `file:line` of the most recent contained panic on this thread.
    static LOCATION: RefCell<Option<String>> = const { RefCell::new(None) };
}

static INSTALL: Once = Once::new();

/// A panic caught from a case runner.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Panicked {
    /// The panic message; a placeholder when the payload is neither `&str` nor `String`.
    pub message: String,
    /// Source `file:line` of the panic, when the hook saw it.
    pub location: Option<String>,
}

/// Install the thread-aware wrapper hook once per process.
fn install_hook() {
    INSTALL.call_once(|| {
        let previous = std::panic::take_hook();
        std::panic::set_hook(Box::new(move |info: &PanicHookInfo<'_>| {
            if CONTAINING.with(Cell::get) {
                let at = info
                    .location()
                    .map(|l| format!("{}:{}", l.file(), l.line()));
                LOCATION.with(|c| *c.borrow_mut() = at);
            } else {
                previous(info);
            }
        }));
        tracing::debug!("installed the mdtest panic containment hook");
    });
}

/// Render a panic payload: `&str` and `String` as written, anything else as a placeholder.
fn payload_message(payload: &(dyn Any + Send)) -> String {
    payload
        .downcast_ref::<&str>()
        .map(|s| (*s).to_owned())
        .or_else(|| payload.downcast_ref::<String>().cloned())
        .unwrap_or_else(|| "<non-string panic payload>".to_owned())
}

/// Run `f`, turning a panic into [`Panicked`]; `f` need not be `UnwindSafe` (its state is discarded on panic).
pub fn contained<T>(f: impl FnOnce() -> T) -> Result<T, Panicked> {
    install_hook();
    let was = CONTAINING.with(|c| c.replace(true));
    LOCATION.with(|c| *c.borrow_mut() = None);
    let out = catch_unwind(AssertUnwindSafe(f));
    CONTAINING.with(|c| c.set(was));
    out.map_err(|payload| {
        let panicked = Panicked {
            message: payload_message(payload.as_ref()),
            location: LOCATION.with(|c| c.borrow_mut().take()),
        };
        tracing::debug!(message = %panicked.message, location = ?panicked.location, "contained a case panic");
        panicked
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-mdtest/src/contain.rs::contained
    #[test]
    fn string_and_str_payloads_are_read() {
        let a = contained(|| -> () { panic!("boom {}", 1) }).unwrap_err();
        assert_eq!(a.message, "boom 1");
        let b = contained(|| -> () { panic!("static") }).unwrap_err();
        assert_eq!(b.message, "static");
        assert!(b.location.is_some_and(|l| l.contains("contain.rs")));
    }

    // frob:tests crates/gob-mdtest/src/contain.rs::contained
    #[test]
    fn non_string_payload_gets_a_placeholder() {
        let p = contained(|| -> () { std::panic::panic_any(42_u32) }).unwrap_err();
        assert_eq!(p.message, "<non-string panic payload>");
    }

    // frob:tests crates/gob-mdtest/src/contain.rs::contained
    #[test]
    fn success_passes_through_and_flag_is_restored() {
        assert_eq!(contained(|| 7).unwrap(), 7);
        assert!(!CONTAINING.with(Cell::get));
        let nested = contained(|| contained(|| -> () { panic!("inner") }).is_err()).unwrap();
        assert!(nested);
        assert!(!CONTAINING.with(Cell::get));
    }
}
