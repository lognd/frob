//! The bundled font table: the only fonts the solver can measure with (determinism, D113).

// frob:ticket 01M5XCWY5RFEP343E8Z6XH9D6C

use parley::{FontContext, fontique};

/// The family used for glyphs missing from the requested font.
pub const FALLBACK_FONT: &str = "DejaVu Sans";

/// Bundled families and their font bytes (licenses live beside the files in `fonts/`).
const BUNDLED: [(&str, &[u8]); 3] = [
    ("DejaVu Sans", include_bytes!("../../fonts/DejaVuSans.ttf")),
    (
        "Liberation Serif",
        include_bytes!("../../fonts/LiberationSerif-Regular.ttf"),
    ),
    ("Lato", include_bytes!("../../fonts/Lato-Regular.ttf")),
];

/// Names of the bundled font families.
pub fn bundled_fonts() -> Vec<&'static str> {
    BUNDLED.iter().map(|(name, _)| *name).collect()
}

/// Whether `name` is a bundled family.
pub(crate) fn is_bundled(name: &str) -> bool {
    BUNDLED.iter().any(|(n, _)| *n == name)
}

/// A parley font context holding only the bundled fonts, plus each family's blob id.
pub(crate) fn bundled_context() -> (FontContext, Vec<(&'static str, u64)>) {
    let mut fc = FontContext {
        collection: fontique::Collection::new(fontique::CollectionOptions {
            shared: false,
            system_fonts: false,
        }),
        source_cache: fontique::SourceCache::default(),
    };
    let mut ids = Vec::new();
    for (name, data) in BUNDLED {
        let blob = fontique::Blob::new(std::sync::Arc::new(data));
        ids.push((name, blob.id()));
        fc.collection.register_fonts(blob, None);
    }
    tracing::debug!(fonts = ids.len(), "bundled font context built");
    (fc, ids)
}
