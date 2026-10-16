//! `frob tour`: all stops in order off a terminal, next and previous controls on one.
// frob:ticket 01M3ZX88BP9P0ZWPMJ5J5SBSMN

use std::io::Cursor;
use std::path::Path;
use std::process::Output;

use frob_cli::tour_cmd::{Opener, session, split_stops};
use serde_json::Value;

use crate::common;

const SAMPLE: &str = "<!-- generated -->\n# Tour\n\nintro\n\n## Stop 1: first\n\nalpha [a](docs/a.md) and [web](https://x.test/y)\n\n## Stop 2: second\n\nbeta\n\n## Stop 3: third\n\ngamma [g](g.md#top)\n\n## Notes\n\n- not a stop\n";

struct Recorder(Vec<String>);

impl Opener for Recorder {
    fn open(&mut self, path: &str) -> Result<(), String> {
        self.0.push(path.to_owned());
        Ok(())
    }
}

fn run_session(script: &str) -> (String, Vec<String>) {
    let stops = split_stops(SAMPLE);
    let mut out = Vec::new();
    let mut rec = Recorder(Vec::new());
    session(
        &stops,
        &mut Cursor::new(script.to_owned()),
        &mut out,
        &mut rec,
    )
    .expect("session");
    (String::from_utf8(out).expect("utf8"), rec.0)
}

#[test]
fn split_stops_keeps_order_links_and_drops_notes() {
    let stops = split_stops(SAMPLE);
    let titles: Vec<_> = stops.iter().map(|s| s.title.as_str()).collect();
    assert_eq!(titles, ["Stop 1: first", "Stop 2: second", "Stop 3: third"]);
    assert_eq!(stops[0].links, ["docs/a.md"]);
    assert_eq!(stops[2].links, ["g.md"]);
    assert!(!stops[2].body.contains("not a stop"));
}

#[test]
fn tty_session_starts_at_stop_one_and_moves_with_next_and_previous() {
    let (out, _) = run_session("n\nn\np\nq\n");
    let shown: Vec<_> = out.lines().filter(|l| l.starts_with('[')).collect();
    assert_eq!(shown, ["[1/3]", "[2/3]", "[3/3]", "[2/3]"]);
    assert!(out.find("alpha").expect("stop 1") < out.find("beta").expect("stop 2"));
}

#[test]
fn session_stops_at_the_ends_and_opens_links() {
    let (out, opened) = run_session("p\no 1\no 9\nn\nn\nn\nq\n");
    assert!(out.contains("This is the first stop."));
    assert!(out.contains("This is the last stop."));
    assert!(out.contains("unknown command `o 9`"));
    assert_eq!(opened, ["docs/a.md"]);
}

#[test]
fn end_of_input_quits() {
    let (out, _) = run_session("");
    assert_eq!(out.matches("[1/3]").count(), 1);
}

fn frob(cwd: &Path, args: &[&str]) -> Output {
    common::frob_command()
        .current_dir(cwd)
        .args(args)
        .output()
        .expect("run frob")
}

fn git(cwd: &Path, args: &[&str]) {
    let st = std::process::Command::new("git")
        .args(args)
        .current_dir(cwd)
        .status()
        .expect("git");
    assert!(st.success(), "git {args:?}");
}

#[test]
fn non_tty_prints_every_stop_in_order_and_json_lists_them() {
    let dir = common::git_repo();
    let p = dir.path();
    std::fs::write(p.join("code.txt"), "code\n").expect("write");
    std::fs::write(p.join("frob.toml"), "[tickets]\nref_mode = \"orphan\"\n").expect("config");
    git(p, &["add", "-A"]);
    git(p, &["commit", "-qm", "code"]);
    for args in [
        vec!["ticket", "branch", "init"],
        vec!["ticket", "new", "--title", "Alpha", "--type", "epic"],
        vec!["ticket", "reindex"],
    ] {
        let out = frob(p, &args);
        assert_eq!(
            out.status.code(),
            Some(0),
            "{args:?}: {}",
            String::from_utf8_lossy(&out.stdout)
        );
    }
    let out = frob(p, &["tour"]);
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout).into_owned();
    let at: Vec<_> = (1..=5)
        .map(|n| {
            text.find(&format!("## Stop {n}:"))
                .unwrap_or_else(|| panic!("stop {n} in {text}"))
        })
        .collect();
    assert!(
        at.windows(2).all(|w| w[0] < w[1]),
        "stops out of order: {at:?}"
    );

    let out = frob(p, &["--json", "tour"]);
    let v: Value = serde_json::from_slice(&out.stdout).expect("json");
    assert_eq!(v["data"]["stops"].as_array().map(Vec::len), Some(5));
    assert_eq!(v["data"]["interactive"], false);
}
