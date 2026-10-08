//! GRL compile-error goldens (grl-spec.md section 10), written before the compiler.
//!
//! `cases/GRLnnn.grl` is a rule file with exactly the mistake the code names;
//! `cases/GRLnnn.expected` is the full rustc-style rendering the compiler must
//! print for it, byte for byte (message, span, label, help, explain line, footer).
//! GRL016 is a test failure rather than a compile error, so its golden is the
//! `grimble rule test` rendering of a mismatched example.
//!
//! Two kinds of test run here:
//!
//! - **Live now, for every code:** the case set is complete, each input parses
//!   (the mistakes are semantic, so the syntax layer must accept them), and each
//!   golden is well formed (header code, `-->` position, quoted source lines and
//!   caret columns agree with the input, help and explain lines present, ASCII).
//! - **Per-code golden comparison:** `golden_grlNNN` renders the input through the
//!   code's checker and compares with the golden. A code whose checker has not
//!   landed is `pending`: its test is `#[ignore]`d with the reason and the ticket
//!   named, so `cargo nextest run` lists it by code as skipped-with-reason, and
//!   `--run-ignored all` runs it and fails loudly ("no checker"). The guard test
//!   `declared_status_matches_registry` fails if a checker is registered for a
//!   code still declared pending (or the reverse), so a stale flag cannot hide.
//!
//! To turn a code on: register its renderer in [`checker`], and flip its line in
//! the `goldens!` table from `pending` to `enabled`. Any difference, even one
//! byte, then fails with a line diff (see [`compare`]).

use std::fmt::Write as _;
use std::path::PathBuf;

use gob_plan::grl::parse;
use gob_text::FileInterner;

/// Every code with a golden: GRL001-GRL015 compile errors, the GRL016 test diff, and the
/// review-driven GRL017 (`certainly` in a negative position) and GRL018 (a word no `lang` answers).
const CODES: [&str; 18] = [
    "GRL001", "GRL002", "GRL003", "GRL004", "GRL005", "GRL006", "GRL007", "GRL008", "GRL009",
    "GRL010", "GRL011", "GRL012", "GRL013", "GRL014", "GRL015", "GRL016", "GRL017", "GRL018",
];

/// A checker: given the display path and the source of a rule file, the exact text to print.
type Render = fn(path: &str, source: &str) -> String;

/// The renderer of the compiler's output for `code`, once its checker has landed.
fn checker(code: &str) -> Option<Render> {
    // Each checker ticket adds its codes here, e.g. `"GRL001" => Some(gob_plan::...::render)`.
    match code {
        "GRL001" | "GRL003" | "GRL004" | "GRL005" | "GRL009" | "GRL010" | "GRL011" | "GRL012"
        | "GRL013" | "GRL014" | "GRL017" | "GRL018" => Some(gob_plan::check::compile_report),
        _ => None,
    }
}

/// One golden: the rule file, where it is shown from, and what must be printed.
struct Case {
    code: &'static str,
    path: String,
    input: String,
    expected: String,
}

fn cases_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/grl_errors/cases")
}

fn load(code: &'static str) -> Case {
    let read = |ext: &str| {
        let p = cases_dir().join(format!("{code}.{ext}"));
        std::fs::read_to_string(&p).unwrap_or_else(|e| panic!("{}: {e}", p.display()))
    };
    Case {
        code,
        path: format!("rules/{code}.grl"),
        input: read("grl"),
        expected: read("expected"),
    }
}

/// `Ok` when equal; otherwise the first differing byte and a line diff of the differing middle.
fn compare(expected: &str, actual: &str) -> Result<(), String> {
    if expected == actual {
        return Ok(());
    }
    let byte = expected
        .bytes()
        .zip(actual.bytes())
        .take_while(|(a, b)| a == b)
        .count();
    let e: Vec<&str> = expected.split('\n').collect();
    let a: Vec<&str> = actual.split('\n').collect();
    let head = e.iter().zip(&a).take_while(|(x, y)| x == y).count();
    let tail = e[head..]
        .iter()
        .rev()
        .zip(a[head..].iter().rev())
        .take_while(|(x, y)| x == y)
        .count();
    let mut out = format!("output differs from the golden at byte {byte}\n");
    for (i, l) in e[head..e.len() - tail].iter().enumerate() {
        let _ = writeln!(out, "- {:>3} | {l:?}", head + i + 1);
    }
    for (i, l) in a[head..a.len() - tail].iter().enumerate() {
        let _ = writeln!(out, "+ {:>3} | {l:?}", head + i + 1);
    }
    Err(out)
}

/// What kind of diagnostic a code is.
fn severity(code: &str) -> &'static str {
    if code == "GRL013" { "warning" } else { "error" }
}

/// Check that `case.expected` is a coherent rendering of a diagnostic for `case.input`.
fn validate(case: &Case) -> Result<(), String> {
    let (code, exp) = (case.code, &case.expected);
    if !exp.is_ascii() {
        return Err("golden is not ASCII".into());
    }
    if !exp.ends_with('\n') || exp.ends_with("\n\n") {
        return Err("golden must end with exactly one newline".into());
    }
    let src: Vec<&str> = case.input.split('\n').collect();
    let lines: Vec<&str> = exp.lines().collect();
    let sev = severity(code);
    let mut i = 0;
    let mut diags = 0;
    while i < lines.len() && lines[i].starts_with(&format!("{sev}[")) {
        i = validate_block(case, &src, &lines, i)?;
        diags += 1;
    }
    if diags == 0 {
        return Err(format!("no `{sev}[{code}]` block"));
    }
    let footer = lines.get(i).ok_or("missing footer line")?;
    if i + 1 != lines.len() || !(footer.starts_with("error: ") || footer.starts_with("warning: ")) {
        return Err(format!("bad footer at line {}: {footer:?}", i + 1));
    }
    if let Some(n) = footer.strip_prefix("error: aborting due to ") {
        let want = format!("{diags} previous error");
        if !n.starts_with(&want) {
            return Err(format!("footer {footer:?} does not count {diags} errors"));
        }
    }
    Ok(())
}

#[allow(clippy::too_many_lines)] // one linear line-classifier; splitting it would scatter the shared state
/// Validate one diagnostic starting at `lines[start]`; returns the index after its trailing blank line.
fn validate_block(
    case: &Case,
    src: &[&str],
    lines: &[&str],
    start: usize,
) -> Result<usize, String> {
    let code = case.code;
    let sev = severity(code);
    let at = |i: usize, m: &str| format!("line {}: {m}", i + 1);
    let head = lines[start];
    let want_head = format!("{sev}[{code}]: ");
    if !head.starts_with(&want_head) || head.len() == want_head.len() {
        return Err(at(start, "header must be `SEVERITY[CODE]: message`"));
    }
    let arrow = lines.get(start + 1).ok_or("missing `-->` line")?;
    let w = arrow.len() - arrow.trim_start().len();
    let loc = arrow
        .trim_start()
        .strip_prefix("--> ")
        .ok_or_else(|| at(start + 1, "expected `--> path:line:col`"))?;
    let mut parts = loc.rsplitn(3, ':');
    let col: usize = parts
        .next()
        .and_then(|s| s.parse().ok())
        .ok_or("bad column")?;
    let line: usize = parts
        .next()
        .and_then(|s| s.parse().ok())
        .ok_or("bad line")?;
    if parts.next() != Some(case.path.as_str()) {
        return Err(at(start + 1, &format!("path must be {}", case.path)));
    }
    let pad = " ".repeat(w + 1);
    let (mut helps, mut explains, mut primaries) = (0, 0, 0);
    let mut shown: Option<(usize, &str)> = None;
    let mut in_extra = false;
    let mut i = start + 2;
    while i < lines.len() && !lines[i].is_empty() {
        let l = lines[i];
        if l == "..." {
            // elided source lines
        } else if let Some(rest) = l.strip_prefix(&pad).and_then(|r| r.strip_prefix('|')) {
            if in_extra {
                return Err(at(i, "source or marker line after the `=` lines"));
            }
            let t = rest.trim_start();
            if t.starts_with('^') || t.starts_with('-') {
                let (ln, text) =
                    shown.ok_or_else(|| at(i, "marker line before any source line"))?;
                let col0 = l.find(['^', '-']).ok_or("no marker")? - (w + 3);
                let marks = &l[w + 3 + col0..];
                let run = marks
                    .chars()
                    .take_while(|c| *c == marks.as_bytes()[0] as char)
                    .count();
                let covered = text
                    .get(col0..col0 + run)
                    .ok_or_else(|| at(i, "marker outside the source line"))?;
                if covered.trim().is_empty() {
                    return Err(at(i, "marker covers only blanks"));
                }
                if marks.starts_with('^') {
                    primaries += 1;
                    if (ln, col0 + 1) != (line, col) {
                        return Err(at(
                            i,
                            &format!(
                                "primary marker is at {ln}:{} but `-->` says {line}:{col}",
                                col0 + 1
                            ),
                        ));
                    }
                }
            } else if !rest.is_empty() {
                return Err(at(i, "expected a marker line or a bare `|`"));
            }
        } else if let Some(rest) = l.strip_prefix(&pad).and_then(|r| r.strip_prefix("= ")) {
            in_extra = true;
            match rest.split_once(": ").map(|x| x.0) {
                Some("help" | "fix") => helps += 1,
                Some("explain") => {
                    explains += 1;
                    if rest != format!("explain: grimble explain {code}") {
                        return Err(at(
                            i,
                            "explain line must read `explain: grimble explain CODE`",
                        ));
                    }
                }
                Some("note" | "diff") => {}
                _ => return Err(at(i, "`=` line must be help, fix, note, diff or explain")),
            }
        } else if in_extra && l.starts_with(&format!("{pad}  ")) {
            // continuation of a multi-line `=` entry
        } else if let Some((n, text)) = l.split_once('|') {
            if w + 1 > l.len() || n.trim().is_empty() {
                return Err(at(i, "unrecognised line"));
            }
            let ln: usize = n
                .trim()
                .parse()
                .map_err(|_| at(i, "bad source line number"))?;
            let text = text.strip_prefix(' ').unwrap_or(text);
            let real = src
                .get(ln - 1)
                .ok_or_else(|| at(i, "source line past the end of the input"))?;
            if real.trim_end() != text {
                return Err(at(
                    i,
                    &format!("source line {ln} is {real:?} in the input, quoted as {text:?}"),
                ));
            }
            shown = Some((ln, *real));
        } else {
            return Err(at(i, "unrecognised line"));
        }
        i += 1;
    }
    if primaries != 1 {
        return Err(at(
            start,
            &format!("expected exactly one `^` span, found {primaries}"),
        ));
    }
    if helps == 0 {
        return Err(at(start, "no `= help:` line"));
    }
    if explains != 1 {
        return Err(at(start, "expected exactly one `= explain:` line"));
    }
    Ok(i + 1)
}

/// Run the golden for `code`: render through its checker and compare byte for byte.
fn run_golden(code: &'static str) {
    let case = load(code);
    let render = checker(code).unwrap_or_else(|| {
        panic!("{code}: no checker is registered yet (pending); see tests/grl_errors/main.rs")
    });
    let actual = render(&case.path, &case.input);
    if let Err(diff) = compare(&case.expected, &actual) {
        panic!("{code}: {diff}");
    }
}

macro_rules! golden_test {
    (pending, $name:ident, $code:literal, $why:literal) => {
        #[test]
        #[ignore = $why]
        fn $name() {
            run_golden($code);
        }
    };
    (enabled, $name:ident, $code:literal, $why:literal) => {
        #[test]
        fn $name() {
            run_golden($code);
        }
    };
}

macro_rules! status_flag {
    (enabled) => {
        true
    };
    (pending) => {
        false
    };
}

/// One line per code: status, test name, code, and the reason shown while pending.
macro_rules! goldens {
    ($($status:ident $name:ident $code:literal $why:literal;)*) => {
        /// `(code, enabled)` as declared in the table below.
        const DECLARED: &[(&str, bool)] = &[$(($code, status_flag!($status))),*];
        $(golden_test!($status, $name, $code, $why);)*
    };
}

goldens! {
    enabled golden_grl001 "GRL001" "landed (~E8Q56WW)";
    pending golden_grl002 "GRL002" "pending: GRL002 checker not landed (~APQDEAP)";
    enabled golden_grl003 "GRL003" "landed (~E8Q56WW)";
    enabled golden_grl004 "GRL004" "landed (~E8Q56WW)";
    enabled golden_grl005 "GRL005" "landed (~E8Q56WW)";
    pending golden_grl006 "GRL006" "pending: GRL006 checker not landed (~APQDEAP)";
    pending golden_grl007 "GRL007" "pending: GRL007 checker not landed (~APQDEAP)";
    pending golden_grl008 "GRL008" "pending: GRL008 checker not landed (~APQDEAP)";
    enabled golden_grl009 "GRL009" "landed (~ZKM5W7Y)";
    enabled golden_grl010 "GRL010" "landed (~ZKM5W7Y)";
    enabled golden_grl011 "GRL011" "landed (~ZKM5W7Y)";
    enabled golden_grl012 "GRL012" "landed (~ZKM5W7Y)";
    enabled golden_grl013 "GRL013" "landed (~E8Q56WW)";
    enabled golden_grl014 "GRL014" "landed (~ZKM5W7Y)";
    pending golden_grl015 "GRL015" "pending: GRL015 checker not landed (~16R03NG)";
    pending golden_grl016 "GRL016" "pending: GRL016 example runner not landed (grimble rule test)";
    enabled golden_grl017 "GRL017" "landed (~E8Q56WW)";
    enabled golden_grl018 "GRL018" "landed (~E8Q56WW)";
}

// frob:ticket 01M3ZX7D9CT156TR8J4YTQ622S
#[test]
fn every_code_has_a_case_and_the_table_lists_them_all() {
    let codes: Vec<&str> = DECLARED.iter().map(|d| d.0).collect();
    assert_eq!(
        codes, CODES,
        "the goldens! table must list every code in order"
    );
    for code in CODES {
        for ext in ["grl", "expected"] {
            let p = cases_dir().join(format!("{code}.{ext}"));
            assert!(p.is_file(), "missing {}", p.display());
        }
    }
    let on_disk = std::fs::read_dir(cases_dir()).expect("cases dir").count();
    assert_eq!(on_disk, CODES.len() * 2, "unexpected extra files in cases/");
}

#[test]
fn pending_codes_are_reported_by_code() {
    let pending: Vec<&str> = DECLARED.iter().filter(|d| !d.1).map(|d| d.0).collect();
    // Printed so `--nocapture` shows the list; the #[ignore] reasons show it in every run.
    println!(
        "GRL goldens pending ({}): {}",
        pending.len(),
        pending.join(" ")
    );
}

#[test]
fn declared_status_matches_registry() {
    for (code, enabled) in DECLARED {
        assert_eq!(
            checker(code).is_some(),
            *enabled,
            "{code}: the goldens! table says enabled={enabled} but the checker registry disagrees"
        );
    }
}

#[test]
fn every_input_parses_because_the_mistakes_are_semantic() {
    let mut files = FileInterner::new();
    for code in CODES {
        let case = load(code);
        let parsed = parse(files.intern(&case.path), &case.input);
        assert!(
            parsed.is_ok(),
            "{code}: syntax errors in the input: {:#?}",
            parsed.errors
        );
    }
}

#[test]
fn every_golden_is_well_formed_and_agrees_with_its_input() {
    let mut bad = Vec::new();
    for code in CODES {
        if let Err(e) = validate(&load(code)) {
            bad.push(format!("{code}: {e}"));
        }
    }
    assert!(bad.is_empty(), "malformed goldens:\n{}", bad.join("\n"));
}

#[test]
fn a_one_byte_difference_fails_and_prints_the_diff() {
    let case = load("GRL001");
    assert_eq!(compare(&case.expected, &case.expected), Ok(()));
    let off = case.expected.replace("`test`", "`tesy`");
    let diff = compare(&case.expected, &off).expect_err("one byte differs");
    assert!(diff.contains("differs from the golden at byte"), "{diff}");
    assert!(diff.contains("- ") && diff.contains("+ "), "{diff}");
    assert!(
        diff.contains("did you mean `test`?") && diff.contains("did you mean `tesy`?"),
        "{diff}"
    );
    let short = case.expected.trim_end_matches('\n');
    assert!(
        compare(&case.expected, short).is_err(),
        "a missing final newline is a difference"
    );
}

#[test]
fn validator_rejects_a_misplaced_caret() {
    let mut case = load("GRL001");
    case.expected = case.expected.replace(
        "  |                      ^^^^",
        "  |                       ^^^^",
    );
    assert!(validate(&case).is_err());
}
