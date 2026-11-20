//! Phase 5 e2e: the render corpus through both engines, with solver-browser parity, VIS001 and
//! axe findings in one report, and every tier that could not run reported as not run.
//!
//! The solver half is `crunk render --engine solve`; the browser half is the gallery renderer the
//! `--engine browser` verb is built on (PNG and measured boxes), with axe-core driven through the
//! same Playwright script. A browser tier that cannot run is `NotRun` with its reason: never an
//! empty finding list, never green, and the run says it is skipped. With Playwright installed the
//! first test checks the real findings; without it that test logs the skip notice and returns,
//! unless `CRUNK_REQUIRE_PLAYWRIGHT` is set (as in the playwright CI job), which fails it instead.

// frob:ticket 01M5XCXVVHQ2SMQFAJVWPZ2BDG

use std::path::{Path, PathBuf};

use crunk_gallery::a11y::{A11yError, AxeScanner, PlaywrightAxe, check_a11y};
use crunk_gallery::boxes::{BoxesError, capture_boxes};
use crunk_gallery::cells::Cell;
use crunk_gallery::parity::{DEFAULT_TOLERANCE_PX, compare, parse_solver};
use crunk_gallery::render::{RenderError, RenderOptions, render};
use crunk_gallery::visual::{Image, Thresholds, check_visual};
use crunk_spec::DesignSpec;
use gob_cli::run_for_test;
use gob_exec::Program;

/// What one tier produced.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Status {
    /// The tier ran; each entry is one finding (empty: it ran and found nothing).
    Ran(Vec<String>),
    /// The tier could not run, and why.
    NotRun(String),
}

impl Status {
    fn is_not_run(&self) -> bool {
        matches!(self, Self::NotRun(_))
    }

    fn findings(&self) -> &[String] {
        match self {
            Self::Ran(found) => found,
            Self::NotRun(_) => &[],
        }
    }
}

/// The combined report: one section per tier.
#[derive(Debug, Clone, PartialEq, Eq)]
struct EngineReport {
    parity: Status,
    vis: Status,
    axe: Status,
}

impl EngineReport {
    fn tiers(&self) -> [(&'static str, &Status); 3] {
        [
            ("parity", &self.parity),
            ("vis", &self.vis),
            ("axe", &self.axe),
        ]
    }

    /// Green only when every tier ran and none found anything: not run is never green.
    fn green(&self) -> bool {
        self.tiers()
            .iter()
            .all(|(_, s)| matches!(s, Status::Ran(f) if f.is_empty()))
    }

    /// The notice that the job is skipped, when any tier did not run.
    fn skip_notice(&self) -> Option<String> {
        let skipped: Vec<&str> = self
            .tiers()
            .iter()
            .filter(|(_, s)| s.is_not_run())
            .map(|(name, _)| *name)
            .collect();
        (!skipped.is_empty()).then(|| {
            format!(
                "render tiers skipped, not passed: {} did not run",
                skipped.join(", ")
            )
        })
    }

    /// The one report: a section per tier, findings under it, or the not-run reason.
    fn text(&self) -> String {
        let mut lines = Vec::new();
        for (name, status) in self.tiers() {
            match status {
                Status::NotRun(why) => lines.push(format!("{name}: not run ({why})")),
                Status::Ran(found) => {
                    lines.push(format!("{name}: {} finding(s)", found.len()));
                    lines.extend(found.iter().map(|f| format!("  {f}")));
                }
            }
        }
        lines.push(String::new());
        lines.join("\n")
    }
}

/// Why a tier stopped: Playwright (or axe) is absent, or something is actually broken.
enum Stop {
    NotRun(String),
    Failed(String),
}

impl From<RenderError> for Stop {
    fn from(e: RenderError) -> Self {
        match e {
            RenderError::PlaywrightMissing { reason, remedy } => Self::NotRun(format!(
                "playwright unavailable: {reason}; install: {remedy}"
            )),
            other => Self::Failed(other.to_string()),
        }
    }
}

impl From<BoxesError> for Stop {
    fn from(e: BoxesError) -> Self {
        match e {
            BoxesError::Render(r) => r.into(),
            other => Self::Failed(other.to_string()),
        }
    }
}

impl From<A11yError> for Stop {
    fn from(e: A11yError) -> Self {
        match e {
            A11yError::Render(r) => r.into(),
            A11yError::AxeMissing { remedy } => {
                Self::NotRun(format!("axe-core unavailable; install: {remedy}"))
            }
            other => Self::Failed(other.to_string()),
        }
    }
}

fn label(cell: &Cell) -> String {
    format!("{}/{} on {}", cell.screen, cell.state, cell.platform)
}

/// The corpus: a copy of the committed fixture project in a scratch directory.
struct Corpus {
    root: PathBuf,
    spec: DesignSpec,
    _guard: tempfile::TempDir,
}

/// Every file under `dir`, found by walking a worklist of directories.
fn files_in(dir: &Path) -> Vec<PathBuf> {
    let (mut files, mut todo) = (Vec::new(), vec![dir.to_path_buf()]);
    while let Some(next) = todo.pop() {
        let (dirs, plain): (Vec<_>, Vec<_>) = std::fs::read_dir(&next)
            .expect("read dir")
            .flatten()
            .map(|e| e.path())
            .partition(|p| p.is_dir());
        todo.extend(dirs);
        files.extend(plain);
    }
    files
}

fn copy_dir(from: &Path, to: &Path) {
    for src in files_in(from) {
        let dst = to.join(src.strip_prefix(from).expect("under the fixture"));
        std::fs::create_dir_all(dst.parent().expect("parent")).expect("create dir");
        std::fs::copy(&src, &dst).expect("copy fixture");
    }
}

impl Corpus {
    fn open() -> Self {
        // Inside the workspace so Node resolves `playwright` the way CI installs it.
        let target = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../target");
        std::fs::create_dir_all(&target).expect("target");
        let guard = tempfile::tempdir_in(&target).expect("tempdir");
        let root = guard.path().join("corpus");
        copy_dir(
            &Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/render_corpus"),
            &root,
        );
        let text = std::fs::read_to_string(root.join("crunk.toml")).expect("crunk.toml");
        let spec = crunk_spec::parse_spec(&text, &root.join("crunk.toml"), &root).expect("spec");
        Self {
            root,
            spec,
            _guard: guard,
        }
    }

    /// The spec with the cell's screen entry pointed at its scene file, as `--engine browser` does.
    fn spec_for(&self, cell: &Cell) -> DesignSpec {
        let scene = self
            .root
            .join(format!("design/scenes/{}.scene.html", cell.screen));
        let mut spec = self.spec.clone();
        if let Some(screen) = spec.screens.get_mut(&cell.screen) {
            screen.entry = crunk::render_browser::file_url(&scene);
        }
        spec
    }

    fn design_image(&self, cell: &Cell) -> Image {
        let path = self.root.join(format!("design/refs/{}.png", cell.screen));
        png::decode(&std::fs::read(path).expect("design image")).expect("design png")
    }
}

/// The solver's layout documents, one per cell, from `crunk render --engine solve`.
fn solve(corpus: &Corpus) -> Vec<(Cell, String)> {
    let (code, out, err) = run_for_test(
        &crunk::cli(),
        &["render", "--engine", "solve", "--json"],
        &corpus.root,
    );
    assert_eq!(code, 0, "{out} {err}");
    let env: serde_json::Value = serde_json::from_str(&out).expect("json envelope");
    env["data"]["cells"]
        .as_array()
        .expect("cells")
        .iter()
        .map(|c| {
            let text = |k: &str| c[k].as_str().expect(k).to_owned();
            let cell = Cell {
                screen: text("screen"),
                state: text("state"),
                platform: text("platform"),
            };
            let layout = std::fs::read_to_string(corpus.root.join(text("path"))).expect("layout");
            (cell, layout)
        })
        .collect()
}

/// Run `per_cell` over every cell; the first `NotRun` makes the whole tier not run.
fn tier(
    cells: &[(Cell, String)],
    mut per_cell: impl FnMut(&Cell, &str) -> Result<Vec<String>, Stop>,
) -> Status {
    let mut found = Vec::new();
    for (cell, layout) in cells {
        match per_cell(cell, layout) {
            Ok(mut f) => found.append(&mut f),
            Err(Stop::NotRun(why)) => return Status::NotRun(why),
            Err(Stop::Failed(why)) => panic!("{}: {why}", label(cell)),
        }
    }
    Status::Ran(found)
}

/// Both engines over the corpus into one report; `node` is the program that runs Playwright.
fn run_tiers(corpus: &Corpus, node: Program) -> EngineReport {
    let cells = solve(corpus);
    let mut opts = RenderOptions::new(corpus.root.join(".stage"));
    opts.node = node;
    let parity = tier(&cells, |cell, layout| {
        let solver = parse_solver(layout).map_err(Stop::Failed)?;
        let ids: Vec<String> = solver.nodes.iter().map(|n| n.id.clone()).collect();
        let browser = capture_boxes(&corpus.spec_for(cell), cell, &ids, &opts)?;
        let report = compare(&solver, &browser, DEFAULT_TOLERANCE_PX);
        Ok(report
            .mismatches
            .iter()
            .map(|m| format!("{}: {m}", label(cell)))
            .collect())
    });
    let vis = tier(&cells, |cell, _| {
        let spec = corpus.spec_for(cell);
        let rendered = render(&spec, std::slice::from_ref(cell), &opts)?
            .results
            .into_iter()
            .next()
            .ok_or_else(|| Stop::Failed("the renderer returned no result".to_owned()))?
            .outcome?;
        let build_bytes = std::fs::read(opts.out_dir.join(&rendered.path)).expect("screenshot");
        let build = png::decode(&build_bytes).map_err(Stop::Failed)?;
        let diff = format!("{}.diff.png", cell.screen);
        Ok(check_visual(
            &spec,
            cell,
            &corpus.design_image(cell),
            &build,
            &Thresholds::default(),
            &diff,
        )
        .map(|f| format!("{} {}", f.rule, f.message))
        .into_iter()
        .collect())
    });
    let scanner = PlaywrightAxe::new(opts.clone());
    let axe = tier(&cells, |cell, _| {
        let found = check_a11y(&corpus.spec_for(cell), cell, &scanner as &dyn AxeScanner)?;
        Ok(found
            .iter()
            .map(|f| {
                format!(
                    "{}: axe {} at {}",
                    label(cell),
                    f.rule,
                    f.node.as_deref().unwrap_or("(page)")
                )
            })
            .collect())
    });
    EngineReport { parity, vis, axe }
}

fn init_logging() {
    let installed = tracing_subscriber::fmt()
        .with_test_writer()
        .with_max_level(tracing::Level::DEBUG)
        .try_init();
    if installed.is_err() {
        tracing::debug!("a test logger was already installed");
    }
}

fn findings_for<'a>(status: &'a Status, screen: &str) -> Vec<&'a String> {
    let prefix = format!("{screen}/");
    status
        .findings()
        .iter()
        .filter(|f| f.starts_with(&prefix) || f.contains(&format!(" {prefix}")))
        .collect()
}

// frob:tests crates/crunk/src/render_browser.rs::file_url
#[test]
fn both_engines_report_parity_vis_and_axe_findings_in_one_report() {
    init_logging();
    let corpus = Corpus::open();
    let report = run_tiers(
        &corpus,
        Program::Tool {
            name: "node".to_owned(),
        },
    );
    if let Some(notice) = report.skip_notice() {
        assert!(
            std::env::var_os("CRUNK_REQUIRE_PLAYWRIGHT").is_none(),
            "playwright required but a tier did not run: {notice}\n{}",
            report.text()
        );
        tracing::warn!("{notice}\n{}", report.text());
        return;
    }
    let text = report.text();
    tracing::info!("{text}");
    // One report, three sections, all ran.
    for name in ["parity:", "vis:", "axe:"] {
        assert!(text.contains(name), "{text}");
    }
    assert!(!text.contains("not run"), "{text}");
    // The clean screen is clean in every tier.
    for status in [&report.parity, &report.vis, &report.axe] {
        assert!(findings_for(status, "clean").is_empty(), "{text}");
    }
    // The broken screen is found by every tier, by name.
    let parity = findings_for(&report.parity, "broken");
    assert!(parity.iter().any(|f| f.contains("node `card`")), "{text}");
    let vis = findings_for(&report.vis, "broken");
    assert!(
        vis.len() == 1 && vis[0].contains("VIS001") && vis[0].contains("differs from its design"),
        "{text}"
    );
    let axe = findings_for(&report.axe, "broken");
    for rule in ["color-contrast", "image-alt"] {
        assert!(
            axe.iter().any(|f| f.contains(&format!("axe {rule} "))),
            "{text}"
        );
    }
    assert!(!report.green(), "{text}");
    assert_eq!(report.skip_notice(), None);
}

// frob:tests crates/crunk-gallery/src/render/playwright.rs::probe
#[test]
fn playwright_absent_leaves_every_tier_not_run_never_green_with_a_skip_notice() {
    init_logging();
    let corpus = Corpus::open();
    let report = run_tiers(
        &corpus,
        Program::Tool {
            name: "crunk-no-such-node-program".to_owned(),
        },
    );
    for (name, status) in report.tiers() {
        let Status::NotRun(why) = status else {
            panic!("{name} must be not run without playwright: {report:?}");
        };
        assert!(why.contains("playwright unavailable"), "{name}: {why}");
        assert!(status.findings().is_empty());
    }
    assert!(!report.green(), "an absent browser is not a pass");
    let notice = report.skip_notice().expect("a skip notice");
    assert!(notice.contains("parity, vis, axe"), "{notice}");
    let text = report.text();
    for name in ["parity: not run", "vis: not run", "axe: not run"] {
        assert!(text.contains(name), "{text}");
    }
    assert!(!text.contains("0 finding(s)"), "never a zero: {text}");
}

#[test]
fn a_tier_that_ran_clean_is_green_and_any_not_run_tier_is_not() {
    let clean = EngineReport {
        parity: Status::Ran(Vec::new()),
        vis: Status::Ran(Vec::new()),
        axe: Status::Ran(Vec::new()),
    };
    assert!(clean.green());
    assert_eq!(clean.skip_notice(), None);
    let partial = EngineReport {
        axe: Status::NotRun("axe-core unavailable".to_owned()),
        ..clean.clone()
    };
    assert!(!partial.green());
    assert_eq!(
        partial.skip_notice().as_deref(),
        Some("render tiers skipped, not passed: axe did not run")
    );
    let found = EngineReport {
        vis: Status::Ran(vec!["x".to_owned()]),
        ..clean
    };
    assert!(!found.green());
    assert_eq!(found.skip_notice(), None);
}

#[test]
fn the_committed_design_images_decode_to_their_viewport() {
    let corpus = Corpus::open();
    for screen in ["clean", "broken"] {
        let cell = Cell {
            screen: screen.to_owned(),
            state: "default".to_owned(),
            platform: "chromium-desktop".to_owned(),
        };
        let image = corpus.design_image(&cell);
        assert_eq!((image.width(), image.height()), (320, 200), "{screen}");
    }
    let clean = corpus.design_image(&Cell {
        screen: "clean".to_owned(),
        state: "default".to_owned(),
        platform: "chromium-desktop".to_owned(),
    });
    assert_eq!(&clean.pixels()[..4], &[0x22, 0x33, 0x55, 0xff], "header");
}

/// A minimal PNG reader for the 8-bit, non-interlaced RGB and RGBA screenshots Chromium writes,
/// with its own inflate: the workspace has no image or zlib dependency and a test needs none.
mod png {
    use crunk_gallery::visual::Image;

    struct Bits<'a> {
        data: &'a [u8],
        pos: usize,
        bit: u32,
    }

    impl Bits<'_> {
        fn one(&mut self) -> Result<u32, String> {
            let byte = *self.data.get(self.pos).ok_or("inflate: out of data")?;
            let b = u32::from((byte >> self.bit) & 1);
            self.bit += 1;
            if self.bit == 8 {
                self.bit = 0;
                self.pos += 1;
            }
            Ok(b)
        }

        fn take(&mut self, n: u32) -> Result<u32, String> {
            let mut v = 0;
            for i in 0..n {
                v |= self.one()? << i;
            }
            Ok(v)
        }

        fn align(&mut self) {
            if self.bit != 0 {
                self.bit = 0;
                self.pos += 1;
            }
        }
    }

    struct Huff {
        count: [u16; 16],
        symbol: Vec<u16>,
    }

    impl Huff {
        fn new(lengths: &[u8]) -> Self {
            let mut count = [0u16; 16];
            for &l in lengths {
                count[usize::from(l)] += 1;
            }
            count[0] = 0;
            let mut offs = [0u16; 16];
            for len in 1..15 {
                offs[len + 1] = offs[len] + count[len];
            }
            let mut symbol = vec![0u16; lengths.len()];
            for (s, &l) in lengths.iter().enumerate() {
                if l != 0 {
                    symbol[usize::from(offs[usize::from(l)])] =
                        u16::try_from(s).expect("symbol fits");
                    offs[usize::from(l)] += 1;
                }
            }
            Self { count, symbol }
        }

        fn decode(&self, bits: &mut Bits<'_>) -> Result<u16, String> {
            let (mut code, mut first, mut index) = (0i32, 0i32, 0i32);
            for len in 1..16 {
                code |= i32::try_from(bits.one()?).expect("bit");
                let count = i32::from(self.count[len]);
                if code - count < first {
                    let at = usize::try_from(index + (code - first)).map_err(|e| e.to_string())?;
                    return self
                        .symbol
                        .get(at)
                        .copied()
                        .ok_or("inflate: bad code".into());
                }
                index += count;
                first = (first + count) << 1;
                code <<= 1;
            }
            Err("inflate: code too long".to_owned())
        }
    }

    const LBASE: [u16; 29] = [
        3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115,
        131, 163, 195, 227, 258,
    ];
    const LEXT: [u8; 29] = [
        0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0,
    ];
    const DBASE: [u16; 30] = [
        1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537,
        2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577,
    ];
    const DEXT: [u8; 30] = [
        0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12,
        13, 13,
    ];
    const CL_ORDER: [usize; 19] = [
        16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15,
    ];

    fn fixed() -> (Huff, Huff) {
        let mut l = [8u8; 288];
        l[144..256].fill(9);
        l[256..280].fill(7);
        (Huff::new(&l), Huff::new(&[5u8; 30]))
    }

    fn dynamic(bits: &mut Bits<'_>) -> Result<(Huff, Huff), String> {
        let nlen = usize::try_from(bits.take(5)? + 257).map_err(|e| e.to_string())?;
        let ndist = usize::try_from(bits.take(5)? + 1).map_err(|e| e.to_string())?;
        let ncode = usize::try_from(bits.take(4)? + 4).map_err(|e| e.to_string())?;
        let mut cl = [0u8; 19];
        for &slot in CL_ORDER.iter().take(ncode) {
            cl[slot] = u8::try_from(bits.take(3)?).map_err(|e| e.to_string())?;
        }
        let clh = Huff::new(&cl);
        let mut lengths = vec![0u8; nlen + ndist];
        let mut i = 0;
        while i < nlen + ndist {
            let sym = clh.decode(bits)?;
            let (value, repeat) = match sym {
                0..=15 => (u8::try_from(sym).expect("len"), 1),
                16 => {
                    let prev = *lengths
                        .get(i.wrapping_sub(1))
                        .ok_or("inflate: no previous")?;
                    (prev, 3 + bits.take(2)?)
                }
                17 => (0, 3 + bits.take(3)?),
                _ => (0, 11 + bits.take(7)?),
            };
            for _ in 0..repeat {
                *lengths.get_mut(i).ok_or("inflate: too many lengths")? = value;
                i += 1;
            }
        }
        Ok((Huff::new(&lengths[..nlen]), Huff::new(&lengths[nlen..])))
    }

    fn codes(
        bits: &mut Bits<'_>,
        out: &mut Vec<u8>,
        lit: &Huff,
        dist: &Huff,
    ) -> Result<(), String> {
        loop {
            let sym = usize::from(lit.decode(bits)?);
            match sym {
                0..=255 => out.push(u8::try_from(sym).expect("byte")),
                256 => return Ok(()),
                _ => {
                    let k = sym - 257;
                    let (base, extra) = (
                        *LBASE.get(k).ok_or("inflate: bad length")?,
                        *LEXT.get(k).ok_or("inflate: bad length")?,
                    );
                    let len = usize::from(base)
                        + usize::try_from(bits.take(u32::from(extra))?).expect("n");
                    let d = usize::from(dist.decode(bits)?);
                    let (dbase, dextra) = (
                        *DBASE.get(d).ok_or("inflate: bad distance")?,
                        *DEXT.get(d).ok_or("inflate: bad distance")?,
                    );
                    let back = usize::from(dbase)
                        + usize::try_from(bits.take(u32::from(dextra))?).expect("n");
                    let start = out
                        .len()
                        .checked_sub(back)
                        .ok_or("inflate: distance too far")?;
                    for j in 0..len {
                        out.push(out[start + j]);
                    }
                }
            }
        }
    }

    /// The decompressed bytes of a zlib stream (its checksum is not verified).
    fn inflate(zlib: &[u8]) -> Result<Vec<u8>, String> {
        let mut bits = Bits {
            data: zlib.get(2..).ok_or("zlib: too short")?,
            pos: 0,
            bit: 0,
        };
        let mut out = Vec::new();
        loop {
            let last = bits.take(1)?;
            match bits.take(2)? {
                0 => {
                    bits.align();
                    let head = bits
                        .data
                        .get(bits.pos..bits.pos + 4)
                        .ok_or("stored: short")?;
                    let len = usize::from(u16::from_le_bytes([head[0], head[1]]));
                    let body = bits
                        .data
                        .get(bits.pos + 4..bits.pos + 4 + len)
                        .ok_or("stored: short")?;
                    out.extend_from_slice(body);
                    bits.pos += 4 + len;
                }
                1 => {
                    let (l, d) = fixed();
                    codes(&mut bits, &mut out, &l, &d)?;
                }
                2 => {
                    let (l, d) = dynamic(&mut bits)?;
                    codes(&mut bits, &mut out, &l, &d)?;
                }
                _ => return Err("inflate: bad block type".to_owned()),
            }
            if last == 1 {
                return Ok(out);
            }
        }
    }

    fn be32(b: &[u8]) -> usize {
        usize::try_from(u32::from_be_bytes([b[0], b[1], b[2], b[3]])).expect("u32 fits usize")
    }

    fn paeth(a: u8, b: u8, c: u8) -> u8 {
        let (ia, ib, ic) = (i32::from(a), i32::from(b), i32::from(c));
        let p = ia + ib - ic;
        let (pa, pb, pc) = ((p - ia).abs(), (p - ib).abs(), (p - ic).abs());
        if pa <= pb && pa <= pc {
            a
        } else if pb <= pc {
            b
        } else {
            c
        }
    }

    /// Decode an 8-bit RGB or RGBA, non-interlaced PNG into an RGBA [`Image`].
    pub fn decode(bytes: &[u8]) -> Result<Image, String> {
        if bytes.get(..8) != Some(&[0x89, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a]) {
            return Err("not a PNG".to_owned());
        }
        let (mut pos, mut header, mut idat) = (8, None, Vec::new());
        while pos + 8 <= bytes.len() {
            let len = be32(&bytes[pos..]);
            let kind = &bytes[pos + 4..pos + 8];
            let body = bytes
                .get(pos + 8..pos + 8 + len)
                .ok_or("png: chunk past end")?;
            match kind {
                b"IHDR" => header = Some(body.to_vec()),
                b"IDAT" => idat.extend_from_slice(body),
                _ => {}
            }
            pos += 12 + len;
        }
        let h = header.ok_or("png: no IHDR")?;
        let (w, ht) = (be32(&h[0..4]), be32(&h[4..8]));
        let channels = match (h[8], h[9], h[12]) {
            (8, 2, 0) => 3,
            (8, 6, 0) => 4,
            other => return Err(format!("png: unsupported format {other:?}")),
        };
        let raw = inflate(&idat)?;
        let stride = w * channels;
        if raw.len() != (stride + 1) * ht {
            return Err("png: wrong amount of pixel data".to_owned());
        }
        let mut rows = vec![0u8; stride * ht];
        for y in 0..ht {
            let filter = raw[y * (stride + 1)];
            for x in 0..stride {
                let cur = raw[y * (stride + 1) + 1 + x];
                let left = if x >= channels {
                    rows[y * stride + x - channels]
                } else {
                    0
                };
                let up = if y > 0 { rows[(y - 1) * stride + x] } else { 0 };
                let corner = if x >= channels && y > 0 {
                    rows[(y - 1) * stride + x - channels]
                } else {
                    0
                };
                let add = match filter {
                    0 => 0,
                    1 => left,
                    2 => up,
                    3 => u8::try_from(u16::midpoint(u16::from(left), u16::from(up))).expect("avg"),
                    4 => paeth(left, up, corner),
                    other => return Err(format!("png: bad filter {other}")),
                };
                rows[y * stride + x] = cur.wrapping_add(add);
            }
        }
        let rgba: Vec<u8> = rows
            .chunks(channels)
            .flat_map(|px| [px[0], px[1], px[2], px.get(3).copied().unwrap_or(255)])
            .collect();
        let dim = |n: usize| u32::try_from(n).map_err(|e| e.to_string());
        Image::new(dim(w)?, dim(ht)?, rgba).map_err(|e| e.to_string())
    }
}
