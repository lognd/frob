//! The E-STATE-TRACKED refusal (security.md 2.2).

use gob_diagnostics::{ExitCode, Refusal, RefusalClass};

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
#[test]
fn state_tracked_refusal_exits_3_and_names_files() {
    let r = Refusal::state_tracked(&[".frob/cache.sqlite".to_owned(), ".crunk/x".to_owned()]);
    assert_eq!(r.code, "E-STATE-TRACKED");
    assert_eq!(r.class, RefusalClass::GuardNeedsAction);
    assert_eq!(r.exit_code(), ExitCode::Refused);
    assert_eq!(r.exit_code() as i32, 3);
    assert!(r.message.contains(".frob/cache.sqlite"));
    assert!(r.message.contains(".crunk/x"));
}
