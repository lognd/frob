//! The core pack gives the `ffi` atom a Python vocabulary and a Python callee detector.

use std::collections::BTreeSet;

use gob_ir::{Answer, core_pack, registry};

/// The Python `ffi` vocabulary names.
fn ffi_names() -> BTreeSet<&'static str> {
    core_pack::vocabs()
        .iter()
        .filter(|v| v.lang == "python" && v.kind == "ffi")
        .flat_map(|v| v.names.iter().copied())
        .collect()
}

// frob:ticket 01M65MN88MGXA6GBSVG5NA4SG2
#[test]
fn python_ffi_vocab_names_ctypes_cffi_and_dlopen() {
    let names = ffi_names();
    for callee in [
        "ctypes.CDLL",
        "ctypes.PyDLL",
        "ctypes.cdll.LoadLibrary",
        "ctypes.windll.kernel32",
        "ctypes.util.find_library",
        "cffi.FFI.dlopen",
        "dlopen",
    ] {
        assert!(
            core_pack::names_callee("python", &names, callee),
            "{callee}"
        );
    }
    assert!(!core_pack::names_callee("python", &names, "os.getcwd"));
}

// frob:ticket 01M65MN88MGXA6GBSVG5NA4SG2
#[test]
fn python_ffi_has_a_detector_row() {
    assert!(!matches!(
        registry::detectors("ffi", "python"),
        Answer::Unknown
    ));
}
