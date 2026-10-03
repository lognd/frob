//! `command_line` round trip: for random argv, a reference splitter of each shell returns the argv exactly.
// frob:ticket 01M41RK1G648EJJNRK4G5RJY40

use gob_exec::{Arg, Shell, command_line};
use proptest::prelude::*;

/// POSIX `sh` word splitting for the subset `command_line` emits: bare words, single quotes, backslash outside quotes.
fn split_posix(line: &str) -> Vec<String> {
    let (mut out, mut cur) = (Vec::new(), String::new());
    let (mut started, mut single) = (false, false);
    let mut chars = line.chars();
    while let Some(c) = chars.next() {
        match (single, c) {
            (true, '\'') => single = false,
            (true, c) => cur.push(c),
            (false, '\'') => {
                single = true;
                started = true;
            }
            (false, '\\') => {
                cur.push(chars.next().expect("escaped char"));
                started = true;
            }
            (false, ' ') => {
                if started {
                    out.push(std::mem::take(&mut cur));
                    started = false;
                }
            }
            (false, c) => {
                cur.push(c);
                started = true;
            }
        }
    }
    assert!(!single, "unterminated quote in {line:?}");
    if started {
        out.push(cur);
    }
    out
}

/// PowerShell splitting for the emitted subset: an optional `& `, bare words and single-quoted strings with doubled quotes.
fn split_powershell(line: &str) -> Vec<String> {
    let is_q = |c: char| matches!(c, '\'' | '\u{2018}' | '\u{2019}' | '\u{201A}' | '\u{201B}');
    let line = line.strip_prefix("& ").unwrap_or(line);
    let chars: Vec<char> = line.chars().collect();
    let (mut out, mut i) = (Vec::new(), 0);
    while i < chars.len() {
        if chars[i] == ' ' {
            i += 1;
        } else if is_q(chars[i]) {
            let mut cur = String::new();
            i += 1;
            loop {
                let c = chars[i];
                if is_q(c) {
                    if chars.get(i + 1) == Some(&c) {
                        cur.push(c);
                        i += 2;
                        continue;
                    }
                    i += 1;
                    break;
                }
                cur.push(c);
                i += 1;
            }
            out.push(cur);
        } else {
            let start = i;
            while i < chars.len() && chars[i] != ' ' {
                i += 1;
            }
            out.push(chars[start..i].iter().collect());
        }
    }
    out
}

/// `cmd.exe` caret removal, then `CommandLineToArgvW` splitting.
fn split_cmd(line: &str) -> Vec<String> {
    let mut uncaret = String::new();
    let mut chars = line.chars();
    while let Some(c) = chars.next() {
        if c == '^' {
            uncaret.extend(chars.next());
        } else {
            uncaret.push(c);
        }
    }
    split_argv_w(&uncaret)
}

fn split_argv_w(line: &str) -> Vec<String> {
    let chars: Vec<char> = line.chars().collect();
    let (mut out, mut cur) = (Vec::new(), String::new());
    let (mut i, mut in_q, mut started) = (0, false, false);
    while i < chars.len() {
        let c = chars[i];
        if c == '\\' {
            let mut n = 0;
            while chars.get(i) == Some(&'\\') {
                n += 1;
                i += 1;
            }
            started = true;
            if chars.get(i) == Some(&'"') {
                cur.extend(std::iter::repeat_n('\\', n / 2));
                if n % 2 == 1 {
                    cur.push('"');
                    i += 1;
                }
            } else {
                cur.extend(std::iter::repeat_n('\\', n));
            }
        } else if c == '"' {
            in_q = !in_q;
            started = true;
            i += 1;
        } else if (c == ' ' || c == '\t') && !in_q {
            if started {
                out.push(std::mem::take(&mut cur));
                started = false;
            }
            i += 1;
        } else {
            cur.push(c);
            started = true;
            i += 1;
        }
    }
    if started {
        out.push(cur);
    }
    out
}

fn args(argv: &[String]) -> Vec<Arg> {
    argv.iter().map(|s| Arg::from(s.as_str())).collect()
}

/// Awkward fragments proptest mixes: spaces, quotes, backslashes, drive letters, `$`, `%`, non-ASCII.
fn word() -> impl Strategy<Value = String> {
    let frag = prop_oneof![
        Just(" ".to_owned()),
        Just("'".to_owned()),
        Just("\"".to_owned()),
        Just("\\".to_owned()),
        Just("\\\\".to_owned()),
        Just("C:\\Program Files\\x".to_owned()),
        Just("D:/a/b".to_owned()),
        Just("$HOME".to_owned()),
        Just("%PATH%".to_owned()),
        Just("^&|<>()!".to_owned()),
        Just("\u{2019}".to_owned()),
        Just("caf\u{e9} \u{65e5}\u{672c}".to_owned()),
        "[a-zA-Z0-9_./=-]{0,6}",
    ];
    proptest::collection::vec(frag, 0..6).prop_map(|v| v.concat())
}

fn argv() -> impl Strategy<Value = Vec<String>> {
    proptest::collection::vec(word(), 1..6)
}

proptest! {
    #[test]
    fn posix_round_trips(v in argv()) {
        prop_assert_eq!(split_posix(&command_line(Shell::Posix, &args(&v))), v);
    }

    #[test]
    fn git_for_windows_sh_round_trips(v in argv()) {
        prop_assert_eq!(split_posix(&command_line(Shell::GitForWindowsSh, &args(&v))), v);
    }

    #[test]
    fn powershell_round_trips(v in argv()) {
        prop_assert_eq!(split_powershell(&command_line(Shell::PowerShell, &args(&v))), v);
    }

    #[test]
    fn cmd_round_trips(v in argv()) {
        prop_assert_eq!(split_cmd(&command_line(Shell::Cmd, &args(&v))), v);
    }
}

#[test]
fn known_lines_for_the_merge_driver() {
    let argv: Vec<Arg> = [
        r"C:\Program Files\frob\frob.exe",
        "merge-driver",
        "%O",
        "%A",
        "%B",
        "%P",
    ]
    .into_iter()
    .map(Arg::from)
    .collect();
    assert_eq!(
        command_line(Shell::GitForWindowsSh, &argv),
        r"'C:\Program Files\frob\frob.exe' merge-driver %O %A %B %P"
    );
    assert_eq!(
        command_line(
            Shell::Posix,
            &[Arg::from("/usr/bin/frob"), Arg::from("it's")]
        ),
        r"/usr/bin/frob 'it'\''s'"
    );
    assert_eq!(
        command_line(
            Shell::PowerShell,
            &[Arg::from(r"C:\x y\f.exe"), Arg::from("a")]
        ),
        r"& 'C:\x y\f.exe' a"
    );
    assert_eq!(command_line(Shell::Posix, &[Arg::from("")]), "''");
}

// frob:tests crates/gob-exec/src/cmdline.rs::Arg.new
#[test]
fn arg_new_wraps_an_os_string_and_exposes_it() {
    let a = Arg::new(std::ffi::OsString::from("x y"));
    assert_eq!(a.as_os_str(), std::ffi::OsStr::new("x y"));
    assert_eq!(command_line(Shell::Posix, &[a]), "'x y'");
}
