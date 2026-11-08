//! Spike: measure the corpus widths with cosmic-text and parley over bundled fonts.
//!
//! Usage: `text-shaping-spike corpus.json out.json font1.ttf font2.ttf font3.ttf`
//! Emits per-library, per-font widths (f32 bits as f64), per-string timing and a
//! determinism flag (two independent contexts must agree bit-for-bit).

use std::{fs, time::Instant};

use cosmic_text::{Attrs, Buffer, Family, FontSystem, Metrics, Shaping, fontdb};
use parley::{FontContext, FontFamily, LayoutContext, StyleProperty, fontique};
use serde_json::{Value, json};
use tracing::{info, warn};

const PASSES: usize = 20;

/// Load the three bundled fonts into a cosmic-text system with no system fonts.
fn cosmic_system(paths: &[String]) -> FontSystem {
    let mut db = fontdb::Database::new();
    for p in paths {
        db.load_font_file(p).expect("load font");
    }
    FontSystem::new_with_locale_and_db("en-US".into(), db)
}

/// Family name of a font file, via fontdb.
fn family_of(path: &str) -> String {
    let mut db = fontdb::Database::new();
    db.load_font_file(path).expect("load font");
    let name = db.faces().next().expect("face").families[0].0.clone();
    name
}

/// Width of `text` in px under cosmic-text (single unwrapped line).
fn cosmic_width(fs: &mut FontSystem, fam: &str, size: f32, text: &str) -> f32 {
    let mut buf = Buffer::new(fs, Metrics::new(size, size * 1.2));
    buf.set_size(None, None);
    buf.set_text(text, &Attrs::new().family(Family::Name(fam)), Shaping::Advanced, None);
    buf.shape_until_scroll(fs, false);
    buf.layout_runs().map(|r| r.line_w).fold(0.0, f32::max)
}

/// Build a parley font context holding only the bundled fonts.
fn parley_ctx(paths: &[String]) -> FontContext {
    let mut fc = FontContext {
        collection: fontique::Collection::new(fontique::CollectionOptions {
            shared: false,
            system_fonts: false,
        }),
        source_cache: fontique::SourceCache::default(),
    };
    for p in paths {
        let data = fs::read(p).expect("read font");
        fc.collection.register_fonts(fontique::Blob::from(data), None);
    }
    fc
}

/// Width of `text` in px under parley (single unwrapped line).
fn parley_width(fc: &mut FontContext, lc: &mut LayoutContext<()>, fam: &str, size: f32, text: &str) -> f32 {
    let mut b = lc.ranged_builder(fc, text, 1.0, true);
    b.push_default(StyleProperty::FontSize(size));
    b.push_default(StyleProperty::FontFamily(FontFamily::Source(format!("'{fam}'").into())));
    let mut l = b.build(text);
    l.break_all_lines(None);
    l.full_width()
}

fn main() {
    tracing_subscriber::fmt().json().init();
    let a: Vec<String> = std::env::args().collect();
    let corpus: Value = serde_json::from_str(&fs::read_to_string(&a[1]).unwrap()).unwrap();
    let size = corpus["size_px"].as_f64().unwrap() as f32;
    let strings: Vec<&str> = corpus["strings"].as_array().unwrap().iter().map(|s| s.as_str().unwrap()).collect();
    let fonts: Vec<String> = a[3..].to_vec();
    let fams: Vec<String> = fonts.iter().map(|p| family_of(p)).collect();
    info!(?fams, n = strings.len(), "spike start");

    let mut out = serde_json::Map::new();
    // cosmic-text
    let mut fs_a = cosmic_system(&fonts);
    let mut fs_b = cosmic_system(&fonts);
    let mut res = serde_json::Map::new();
    let mut det = true;
    let mut total_ns = 0u128;
    let mut calls = 0u128;
    for fam in &fams {
        let w: Vec<f32> = strings.iter().map(|s| cosmic_width(&mut fs_a, fam, size, s)).collect();
        let w2: Vec<f32> = strings.iter().map(|s| cosmic_width(&mut fs_b, fam, size, s)).collect();
        det &= w.iter().zip(&w2).all(|(x, y)| x.to_bits() == y.to_bits());
        let t = Instant::now();
        for _ in 0..PASSES {
            for s in &strings {
                std::hint::black_box(cosmic_width(&mut fs_a, fam, size, s));
            }
        }
        total_ns += t.elapsed().as_nanos();
        calls += (PASSES * strings.len()) as u128;
        res.insert(fam.clone(), json!(w));
    }
    let us = total_ns as f64 / calls as f64 / 1000.0;
    info!(lib = "cosmic-text", us_per_string = us, deterministic = det, "done");
    out.insert("cosmic-text".into(), json!({"widths": res, "us_per_string": us, "deterministic": det}));

    // parley
    let mut fc_a = parley_ctx(&fonts);
    let mut fc_b = parley_ctx(&fonts);
    let (mut lc_a, mut lc_b) = (LayoutContext::<()>::new(), LayoutContext::<()>::new());
    let mut res = serde_json::Map::new();
    let mut det = true;
    let mut total_ns = 0u128;
    let mut calls = 0u128;
    for fam in &fams {
        let w: Vec<f32> = strings.iter().map(|s| parley_width(&mut fc_a, &mut lc_a, fam, size, s)).collect();
        let w2: Vec<f32> = strings.iter().map(|s| parley_width(&mut fc_b, &mut lc_b, fam, size, s)).collect();
        det &= w.iter().zip(&w2).all(|(x, y)| x.to_bits() == y.to_bits());
        if w.iter().all(|x| *x == 0.0) {
            warn!(fam, "parley measured all zero: family not resolved");
        }
        let t = Instant::now();
        for _ in 0..PASSES {
            for s in &strings {
                std::hint::black_box(parley_width(&mut fc_a, &mut lc_a, fam, size, s));
            }
        }
        total_ns += t.elapsed().as_nanos();
        calls += (PASSES * strings.len()) as u128;
        res.insert(fam.clone(), json!(w));
    }
    let us = total_ns as f64 / calls as f64 / 1000.0;
    info!(lib = "parley", us_per_string = us, deterministic = det, "done");
    out.insert("parley".into(), json!({"widths": res, "us_per_string": us, "deterministic": det}));

    out.insert("families".into(), json!(fams));
    fs::write(&a[2], serde_json::to_string_pretty(&out).unwrap()).unwrap();
}
