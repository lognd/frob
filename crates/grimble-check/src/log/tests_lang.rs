//! LOG001/LOG002 fixtures for the Java, C/C++ and Bash scanners.

// frob:ticket 01M63G1MW58WP8VBQ7T6NKDAMD

use gob_languages::Language;
use grimble_lints::pass::PathFile;

use super::pass::{LogOptions, analyze};

/// The (rule, anchor) pairs of the findings for one file.
fn run(path: &str, language: Language, text: &str) -> Vec<(String, String)> {
    let files = [PathFile {
        path,
        language,
        text,
    }];
    analyze(&files, &LogOptions::default())
        .findings
        .into_iter()
        .map(|f| (f.rule.to_owned(), f.anchor))
        .collect()
}

/// The LOG001 atom ids hit in `text`.
fn atoms(path: &str, language: Language, text: &str) -> Vec<String> {
    run(path, language, text)
        .into_iter()
        .filter(|(r, _)| r == "LOG001")
        .map(|(_, a)| a.split(':').nth(1).unwrap_or_default().to_owned())
        .collect()
}

fn java(text: &str) -> Vec<String> {
    atoms("A.java", Language::Java, text)
}

fn c(text: &str) -> Vec<String> {
    atoms("a.c", Language::C, text)
}

fn cpp(text: &str) -> Vec<String> {
    atoms("a.cpp", Language::Cpp, text)
}

fn sh(text: &str) -> Vec<String> {
    atoms("a.sh", Language::Shell, text)
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn java_system_out_and_err_are_direct_output() {
    let hits = java("class A { void f() { System.out.println(\"x\"); System.err.print(1); } }");
    assert_eq!(hits.len(), 2, "{hits:?}");
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn java_print_stack_trace_and_import_aliases() {
    assert_eq!(
        java("class A { void f(Exception e) { e.printStackTrace(); } }").len(),
        1
    );
    assert!(java("class A { void f(Exception e) { e.printStackTrace(log); } }").is_empty());
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn java_shadowing_strings_and_comments_are_clean() {
    assert!(java("class A { void f() { String s = \"System.out.println(1)\"; } }").is_empty());
    assert!(java("class A { /* System.out.println(1); */ }").is_empty());
    assert!(java("class A { void f(Object System) { System.out.println(1); } }").is_empty());
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn java_logging_import_satisfies_log002() {
    let with = run(
        "A.java",
        Language::Java,
        "import org.slf4j.Logger;\nclass A { Logger l; void f() { System.out.println(1); } }",
    );
    assert!(with.iter().all(|(r, _)| r != "LOG002"), "{with:?}");
    let without = run(
        "A.java",
        Language::Java,
        "class A { void f() { System.out.println(1); } }",
    );
    assert!(without.iter().any(|(r, _)| r == "LOG002"), "{without:?}");
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn c_stdio_calls_and_stream_arguments() {
    assert_eq!(c("int main(void){ printf(\"x\"); return 0; }").len(), 1);
    assert_eq!(
        c("void f(void){ fprintf(stderr, \"x\"); }"),
        ["c.stdio-stream"]
    );
    assert!(c("void f(FILE *out){ fprintf(out, \"x\"); }").is_empty());
    assert_eq!(c("void f(void){ perror(\"x\"); }"), ["c.stderr-helpers"]);
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn c_fd_writes_macros_shadowing_and_noise() {
    assert_eq!(c("void f(void){ write(2, \"x\", 1); }"), ["c.fd-write"]);
    assert!(c("void f(int fd){ write(fd, \"x\", 1); }").is_empty());
    assert_eq!(
        c("#define LOG(m) fprintf(stderr, \"%s\", m)\n"),
        ["c.stdio-stream"]
    );
    assert!(c("void printf(const char*s){}\nvoid f(void){ printf(\"x\"); }").is_empty());
    assert!(c("/* printf(\"x\"); */ const char *s = \"printf(1)\";").is_empty());
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn cpp_streams_and_using_declarations() {
    assert_eq!(
        cpp("#include <iostream>\nvoid f(){ std::cout << 1 << 2; }"),
        ["c.cpp-streams"]
    );
    assert_eq!(
        cpp("using namespace std;\nvoid f(){ cerr << 1; }"),
        ["c.cpp-streams"]
    );
    assert_eq!(
        cpp("using std::clog;\nvoid f(){ clog << 1; }"),
        ["c.cpp-streams"]
    );
    assert!(cpp("void f(std::ostream& cout){ cout << 1; }").is_empty());
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn c_logging_include_satisfies_log002() {
    let with = run(
        "a.cpp",
        Language::Cpp,
        "#include <spdlog/spdlog.h>\nvoid f(){ std::cout << 1; }",
    );
    assert!(with.iter().all(|(r, _)| r != "LOG002"), "{with:?}");
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn bash_echo_printf_and_redirects() {
    assert_eq!(sh("echo hi\n"), ["sh.echo"]);
    assert_eq!(sh("printf '%s' hi\n"), ["sh.printf"]);
    assert!(sh("printf -v x '%s' hi\n").is_empty());
    assert_eq!(sh("echo hi >&2\n"), ["sh.stderr-redirect"]);
    assert_eq!(sh("echo hi > /dev/stderr\n"), ["sh.stderr-redirect"]);
    assert_eq!(sh("foo 2>&1\n"), ["sh.stderr-redirect"]);
    assert_eq!(sh("echo hi >/dev/fd/2\n"), ["sh.fd-write"]);
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn bash_captured_and_redirected_output_is_clean() {
    assert!(sh("x=$(echo hi)\n").is_empty());
    assert!(sh("echo hi | grep h\n").is_empty());
    assert!(sh("echo hi > out.txt\n").is_empty());
    assert!(sh("foo >/dev/null 2>&1\n").is_empty());
    assert!(sh("# echo hi\nx='echo hi'\n").is_empty());
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn bash_logger_is_sanctioned_and_functions_shadow_or_wrap() {
    let out = run("a.sh", Language::Shell, "logger -t x hi\necho hi\n");
    assert!(out.iter().all(|(r, _)| r != "LOG002"), "{out:?}");
    assert!(sh("echo() { :; }\necho hi\n").is_empty());
    let wrapped = sh("die() { echo \"$1\" >&2; }\ndie boom\n");
    assert!(wrapped.contains(&"sh.die".to_owned()), "{wrapped:?}");
}

// frob:ticket 01M63G1NFTCN016KS8PT3JQNPF
// frob:tests crates/grimble-check/src/log/catalogue.rs::Atom
#[test]
fn python_stream_sinks_fire_only_for_a_std_stream_destination() {
    let py = |t: &str| atoms("a.py", Language::Python, t);
    assert_eq!(
        py("import json, sys\njson.dump({}, sys.stdout)\n"),
        ["py.json-dump"]
    );
    assert_eq!(
        py("import json, sys\nout = sys.stderr\njson.dump({}, out)\n"),
        ["py.json-dump"]
    );
    assert_eq!(
        py("import shutil, sys\nshutil.copyfileobj(src, sys.stdout)\n"),
        ["py.shutil"]
    );
    assert_eq!(
        py("import csv, sys\nw = csv.writer(sys.stdout)\n"),
        ["py.csv-writer"]
    );
    assert!(py("import json\njson.dump({}, fh)\n").is_empty());
    assert!(py("import csv\nw = csv.writer(fh)\n").is_empty());
}

/// The number of unresolved LOG001 reports for `text`.
fn unresolved(path: &str, language: Language, text: &str) -> usize {
    run(path, language, text)
        .into_iter()
        .filter(|(r, a)| r == "LOG001" && a.contains(":dynamic:"))
        .count()
}

// frob:tests crates/grimble-check/src/log/catalogue.rs::Group.mode_unresolved
#[test]
fn open_with_a_non_constant_mode_is_unresolved_not_guessed() {
    let py = |t: &str| unresolved("a.py", Language::Python, t);
    assert_eq!(py("def f(p, m):\n    open(p, m)\n"), 1);
    assert_eq!(py("def f(p, m):\n    open(p, mode=m)\n"), 1);
    assert_eq!(py("m = 'r'\nopen('x', m)\n"), 0);
    assert_eq!(py("open('x')\nopen('x', 'r')\n"), 0);
}

// frob:tests crates/grimble-check/src/log/catalogue.rs::Group.mode_unresolved
#[test]
fn js_open_sync_with_a_non_constant_mode_is_unresolved() {
    let js = |t: &str| unresolved("a.js", Language::JavaScript, t);
    assert_eq!(
        js("const fs = require('fs');\nfunction f(p, m) { fs.openSync(p, m); }"),
        1
    );
    assert_eq!(js("const fs = require('fs');\nfs.openSync('p', 'r');"), 0);
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn js_dynamic_console_member_is_unresolved() {
    let js = |t: &str| unresolved("a.js", Language::JavaScript, t);
    assert_eq!(js("function f(name) { console[name]('x'); }"), 1);
    assert_eq!(js("console['log']('x');"), 0);
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn bash_dynamic_descriptor_redirect_is_unresolved() {
    let sh = |t: &str| unresolved("a.sh", Language::Shell, t);
    assert_eq!(sh("echo hi >&$fd\n"), 1);
    assert_eq!(sh("echo hi > /dev/fd/$n\n"), 1);
    assert_eq!(sh("echo hi >&2\n"), 0);
    assert_eq!(sh("echo hi > \"$file\"\n"), 0);
}

// frob:tests crates/grimble-check/src/log/pass.rs::analyze
#[test]
fn rust_macro_rules_body_is_scanned_and_extern_c_is_an_atom() {
    let rs = |t: &str| atoms("a.rs", Language::Rust, t);
    let m = rs("macro_rules! say { ($x:expr) => { println!(\"{}\", $x) }; }");
    assert_eq!(m.len(), 1, "{m:?}");
    assert!(rs("macro_rules! say { ($x:expr) => { $x }; }").is_empty());
    let e = rs("extern \"C\" { fn puts(s: *const u8) -> i32; }");
    assert_eq!(e, ["rust.extern-c"], "{e:?}");
}
