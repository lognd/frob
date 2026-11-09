//! T1 solver integration (~G2AXW7M): the scene corpus solves byte-identically to committed
//! layout-solve baselines, and the LAYOUT, RESP and GX focus findings derived from the solver
//! output match committed findings baselines. No browser is involved.
//!
//! Set `CRUNK_UPDATE_BASELINES=1` to rewrite the baselines under `tests/corpus/baselines/`.

// frob:ticket 01M4CXREV41PNTSYVFFG2AXW7M

use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use crunk_layout::output::{LayoutSolve, SolvedNode};
use crunk_layout::solve::solve_scene_html;
use crunk_layout::style::TokenMap;
use crunk_layout::text::TextMeasurer;
use crunk_layout::{FocusGraph, InvalidReason};
use crunk_scene::parse_scene_html;

/// The viewports every corpus scene is solved at (width, height): a phone and a desktop.
const VIEWPORTS: [(f32, f32); 2] = [(375.0, 667.0), (1280.0, 800.0)];
/// Pixel tolerance when comparing solved rectangles.
const EPS: f32 = 0.5;

fn corpus_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/corpus")
}

/// The corpus scene stems; each is `tests/corpus/<stem>.scene.html` (a fixed list keeps
/// path-to-text conversion out of the test, per clippy.toml).
const SCENE_NAMES: [&str; 3] = ["card-row", "focus-trap", "menu"];

/// The corpus scenes as (name, html), sorted by name.
fn scenes() -> Vec<(String, String)> {
    SCENE_NAMES
        .iter()
        .map(|stem| {
            let path = corpus_dir().join(format!("{stem}.scene.html"));
            let html = std::fs::read_to_string(path).expect("read scene");
            ((*stem).to_owned(), html)
        })
        .collect()
}

fn solve_json(html: &str, vp: (f32, f32)) -> (LayoutSolve, String) {
    let doc = parse_scene_html(html).expect("parses");
    let solved =
        solve_scene_html(&doc, &TokenMap::new(), vp, &mut TextMeasurer::new()).expect("solves");
    let json = solved.doc.to_json().expect("serializes");
    (solved.doc, json)
}

/// Write `actual` to `path`, creating its directory.
fn write_baseline(path: &Path, actual: &str) {
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, actual).expect("write baseline");
}

/// Compare `actual` with the baseline file `name`; `CRUNK_UPDATE_BASELINES` rewrites it first.
fn check_baseline(name: &str, actual: &str) {
    let path = corpus_dir().join("baselines").join(name);
    std::env::var_os("CRUNK_UPDATE_BASELINES")
        .map(|_| write_baseline(&path, actual))
        .unwrap_or_default();
    let want = std::fs::read_to_string(&path).unwrap_or_else(|e| {
        panic!("missing baseline {name} ({e}); run with CRUNK_UPDATE_BASELINES=1")
    });
    assert_eq!(want, actual, "baseline {name} differs");
}

fn rect(n: &SolvedNode) -> (f32, f32, f32, f32) {
    (n.x, n.y, n.x + n.width, n.y + n.height)
}

/// LAYOUT001/002 and RESP findings read from a solved document.
fn layout_findings(doc: &LayoutSolve) -> Vec<String> {
    let mut out = Vec::new();
    let vw = doc.viewport_width;
    for n in &doc.nodes {
        let (l, t, r, b) = rect(n);
        if let Some(p) = n
            .parent
            .as_deref()
            .and_then(|id| doc.nodes.iter().find(|x| x.id == id))
        {
            let (pl, pt, pr, pb) = rect(p);
            if l < pl - EPS || t < pt - EPS || r > pr + EPS || b > pb + EPS {
                out.push(format!(
                    "LAYOUT001 {vw}: '{}' overflows its parent '{}'",
                    n.id, p.id
                ));
            }
        } else if r > vw + EPS {
            out.push(format!(
                "RESP001 {vw}: root '{}' is wider than the viewport",
                n.id
            ));
        }
        for sib in doc
            .nodes
            .iter()
            .filter(|s| s.parent == n.parent && s.id > n.id)
        {
            let (sl, st, sr, sb) = rect(sib);
            if l < sr - EPS && sl < r - EPS && t < sb - EPS && st < b - EPS {
                out.push(format!(
                    "LAYOUT002 {vw}: siblings '{}' and '{}' overlap",
                    n.id, sib.id
                ));
            }
        }
    }
    out
}

/// GX002-GX005 findings read from the focus graph of a scene.
fn focus_findings(html: &str) -> Vec<String> {
    let g = FocusGraph::from_scene(&parse_scene_html(html).expect("parses"));
    let name = |i: usize| g.nodes[i].label.clone();
    let mut out = Vec::new();
    out.extend(
        g.unreachable()
            .into_iter()
            .map(|i| format!("GX002 {} is unreachable", name(i))),
    );
    out.extend(
        g.traps()
            .into_iter()
            .map(|i| format!("GX003 {} is a focus trap", name(i))),
    );
    if !g.nodes.is_empty() && g.defaults.len() != 1 {
        out.push(format!("GX004 {} default focus targets", g.defaults.len()));
    }
    for bad in &g.invalid {
        let mut s = String::new();
        match &bad.reason {
            InvalidReason::UnknownTarget(id) | InvalidReason::UnfocusableTarget(id) => {
                write!(
                    s,
                    "GX005 {} {} names unusable '{id}'",
                    bad.label, bad.attribute
                )
                .unwrap();
            }
            InvalidReason::BadWrap(v) | InvalidReason::BadAxis(v) => {
                write!(
                    s,
                    "GX005 {} {} has bad value '{v}'",
                    bad.label, bad.attribute
                )
                .unwrap();
            }
        }
        out.push(s);
    }
    out
}

// frob:tests solve_scene_html
#[test]
fn corpus_solves_byte_identically_and_matches_baselines() {
    for (name, html) in scenes() {
        for vp in VIEWPORTS {
            let (_, a) = solve_json(&html, vp);
            let (_, b) = solve_json(&html, vp);
            assert_eq!(a, b, "{name} at {vp:?} is not deterministic");
            check_baseline(&format!("{name}.{}.layout.json", vp.0), &a);
        }
    }
}

// frob:tests FocusGraph.from_scene
#[test]
fn corpus_layout_resp_and_gx_findings_match_baselines() {
    for (name, html) in scenes() {
        let mut findings = Vec::new();
        for vp in VIEWPORTS {
            findings.extend(layout_findings(&solve_json(&html, vp).0));
        }
        findings.extend(focus_findings(&html));
        let mut text = serde_json::to_string_pretty(&findings).expect("json");
        text.push('\n');
        check_baseline(&format!("{name}.findings.json"), &text);
    }
}

#[test]
fn corpus_findings_fire_where_the_scenes_are_broken() {
    let all = |n: &str| {
        let html = scenes().into_iter().find(|(s, _)| s == n).expect("scene").1;
        let mut f = layout_findings(&solve_json(&html, VIEWPORTS[0]).0);
        f.extend(focus_findings(&html));
        f
    };
    assert!(
        all("menu").iter().all(|f| !f.starts_with("GX")),
        "menu is a clean focus list"
    );
    assert!(all("card-row").iter().any(|f| f.starts_with("RESP001")));
    let trap = all("focus-trap");
    for code in ["GX003", "GX005"] {
        assert!(
            trap.iter().any(|f| f.starts_with(code)),
            "{code} in {trap:?}"
        );
    }
}
