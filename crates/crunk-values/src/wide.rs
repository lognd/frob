//! CSS Color 4 functions (`oklch`, `oklab`, `lab`, `lch`, `hwb`, `color()`), OKLab math and gamut
//! mapping. Everything lands in 0-1 sRGB through the CSS Color 4 gamut-mapping algorithm.

// frob:ticket 01M48NF9E0WTVHPA4XQ3200J6N

#![allow(
    clippy::doc_markdown,
    reason = "colour-science names (OKLab, deltaE_OK, ProPhoto) are proper nouns, not code"
)]

use crate::color::Color;
use crate::error::ColorError;
use crate::num::{parse_number, split_number};

/// A 3x3 matrix, row major.
type Mat = [[f64; 3]; 3];

/// XYZ (D65) to linear sRGB.
const XYZ_TO_LIN_SRGB: Mat = [
    [
        3.240_969_941_904_522_6,
        -1.537_383_177_570_094,
        -0.498_610_760_293_003_4,
    ],
    [
        -0.969_243_636_280_879_6,
        1.875_967_501_507_720_7,
        0.041_555_057_407_175_59,
    ],
    [
        0.055_630_079_696_993_66,
        -0.203_976_958_888_976_52,
        1.056_971_514_242_878_6,
    ],
];
/// Linear sRGB to XYZ (D65).
const LIN_SRGB_TO_XYZ: Mat = [
    [
        0.412_390_799_265_959_34,
        0.357_584_339_383_878,
        0.180_480_788_401_834_3,
    ],
    [
        0.212_639_005_871_510_27,
        0.715_168_678_767_756,
        0.072_192_315_360_733_71,
    ],
    [
        0.019_330_818_715_591_82,
        0.119_194_779_794_625_98,
        0.950_532_152_249_660_7,
    ],
];
/// Linear Display P3 to XYZ (D65).
const LIN_P3_TO_XYZ: Mat = [
    [
        0.486_570_948_648_216_2,
        0.265_667_693_169_093_06,
        0.198_217_285_234_362_5,
    ],
    [
        0.228_974_564_069_748_8,
        0.691_738_521_836_506_9,
        0.079_286_914_093_745,
    ],
    [0.0, 0.045_113_381_858_902_64, 1.043_944_368_900_976],
];
/// Linear A98 RGB to XYZ (D65).
const LIN_A98_TO_XYZ: Mat = [
    [
        0.576_669_042_910_130_5,
        0.185_558_237_906_546_3,
        0.188_228_646_234_994_7,
    ],
    [
        0.297_344_975_250_536_05,
        0.627_363_566_255_466_1,
        0.075_291_458_493_997_8,
    ],
    [
        0.027_031_361_386_412_34,
        0.070_688_852_535_827_1,
        0.991_337_536_837_638_8,
    ],
];
/// Linear Rec. 2020 to XYZ (D65).
const LIN_REC2020_TO_XYZ: Mat = [
    [
        0.636_958_048_301_291_4,
        0.144_616_903_586_208_32,
        0.168_880_975_164_172_1,
    ],
    [
        0.262_700_212_011_267_1,
        0.677_998_071_518_870_8,
        0.059_301_716_469_861_96,
    ],
    [0.0, 0.028_072_693_049_087_428, 1.060_985_057_710_791],
];
/// Linear ProPhoto RGB to XYZ (D50).
const LIN_PROPHOTO_TO_XYZ_D50: Mat = [
    [
        0.797_760_489_672_302_7,
        0.135_185_837_175_740_31,
        0.031_349_349_581_524_8,
    ],
    [
        0.288_071_128_229_293_4,
        0.711_843_217_810_102_1,
        0.000_085_653_960_605_259,
    ],
    [0.0, 0.0, 0.825_104_602_510_460_1],
];
/// Bradford adaptation, XYZ D50 to XYZ D65.
const D50_TO_D65: Mat = [
    [
        0.955_473_452_704_218_2,
        -0.023_098_536_874_261_423,
        0.063_259_308_661_021_7,
    ],
    [
        -0.028_369_706_963_208_136,
        1.009_995_458_005_822_6,
        0.021_041_398_966_943_008,
    ],
    [
        0.012_314_001_688_319_899,
        -0.020_507_696_433_477_912,
        1.330_365_936_608_075_3,
    ],
];
/// XYZ (D65) to the OKLab cone response.
const XYZ_TO_LMS: Mat = [
    [
        0.819_022_437_996_703,
        0.361_906_260_052_890_4,
        -0.128_873_781_520_987_9,
    ],
    [
        0.032_983_653_932_388_5,
        0.929_286_861_586_340_3,
        0.036_144_666_350_642_4,
    ],
    [
        0.048_177_189_359_626_6,
        0.264_239_531_752_730_8,
        0.633_547_828_469_430_9,
    ],
];
/// Cone response (cube-rooted) to OKLab.
const LMS_TO_OKLAB: Mat = [
    [
        0.210_454_268_309_314,
        0.793_617_774_702_305_4,
        -0.004_072_043_011_619_3,
    ],
    [
        1.977_998_532_431_168_4,
        -2.428_592_242_048_58,
        0.450_593_709_617_411,
    ],
    [
        0.025_904_042_465_547_8,
        0.782_771_712_457_529_6,
        -0.808_675_754_923_077_4,
    ],
];
/// OKLab to cube-rooted cone response.
const OKLAB_TO_LMS: Mat = [
    [1.0, 0.396_337_777_376_174_9, 0.215_803_757_309_913_6],
    [1.0, -0.105_561_345_815_658_6, -0.063_854_172_825_813_3],
    [1.0, -0.089_484_177_529_811_9, -1.291_485_548_019_409_2],
];
/// Cone response to XYZ (D65).
const LMS_TO_XYZ: Mat = [
    [
        1.226_879_875_845_924_3,
        -0.557_814_994_460_217_1,
        0.281_391_045_665_964_7,
    ],
    [
        -0.040_575_745_214_800_8,
        1.112_286_803_280_317,
        -0.071_711_058_065_516_4,
    ],
    [
        -0.076_372_936_674_660_1,
        -0.421_493_332_402_293_3,
        1.586_924_019_836_781_6,
    ],
];

/// CIE epsilon (216/24389) and kappa (24389/27) for Lab.
const LAB_EPSILON: f64 = 216.0 / 24389.0;
/// See [`LAB_EPSILON`].
const LAB_KAPPA: f64 = 24389.0 / 27.0;
/// D50 reference white in XYZ.
const WHITE_D50: [f64; 3] = [0.345_7 / 0.358_5, 1.0, (1.0 - 0.345_7 - 0.358_5) / 0.358_5];

/// Just-noticeable difference in deltaE_OK the gamut-mapping algorithm tolerates.
const JND: f64 = 0.02;
/// Chroma search precision of the gamut-mapping algorithm.
const MAP_EPSILON: f64 = 0.0001;
/// Slack when deciding a linear channel is inside `[0, 1]`.
const GAMUT_SLACK: f64 = 1e-6;

/// Multiplies a matrix by a column vector.
pub(crate) fn mul(m: &Mat, v: [f64; 3]) -> [f64; 3] {
    let row = |r: &[f64; 3]| r[0] * v[0] + r[1] * v[1] + r[2] * v[2];
    [row(&m[0]), row(&m[1]), row(&m[2])]
}

/// The sRGB transfer function, linear to encoded (sign preserving).
fn lin_to_srgb(c: f64) -> f64 {
    let a = c.abs();
    if a <= 0.003_130_8 {
        12.92 * c
    } else {
        c.signum() * (1.055 * a.powf(1.0 / 2.4) - 0.055)
    }
}

/// The sRGB transfer function, encoded to linear (sign preserving).
pub(crate) fn srgb_to_lin(c: f64) -> f64 {
    let a = c.abs();
    if a <= 0.040_45 {
        c / 12.92
    } else {
        c.signum() * ((a + 0.055) / 1.055).powf(2.4)
    }
}

/// Linear sRGB to OKLab `[L, a, b]`.
pub(crate) fn linear_srgb_to_oklab(rgb: [f64; 3]) -> [f64; 3] {
    let lms = mul(&XYZ_TO_LMS, mul(&LIN_SRGB_TO_XYZ, rgb));
    mul(&LMS_TO_OKLAB, lms.map(f64::cbrt))
}

/// OKLab `[L, a, b]` to linear sRGB (may leave `[0, 1]`).
pub(crate) fn oklab_to_linear_srgb(lab: [f64; 3]) -> [f64; 3] {
    let lms = mul(&OKLAB_TO_LMS, lab).map(|v| v * v * v);
    mul(&XYZ_TO_LIN_SRGB, mul(&LMS_TO_XYZ, lms))
}

/// deltaE_OK: the Euclidean distance of two OKLab triples.
pub(crate) fn delta_ok(a: [f64; 3], b: [f64; 3]) -> f64 {
    ((a[0] - b[0]).powi(2) + (a[1] - b[1]).powi(2) + (a[2] - b[2]).powi(2)).sqrt()
}

/// True when every linear channel is inside `[0, 1]` (within [`GAMUT_SLACK`]).
fn in_gamut(rgb: [f64; 3]) -> bool {
    rgb.iter()
        .all(|c| *c >= -GAMUT_SLACK && *c <= 1.0 + GAMUT_SLACK)
}

/// Clamps each linear channel to `[0, 1]`.
fn clip(rgb: [f64; 3]) -> [f64; 3] {
    rgb.map(|c| c.clamp(0.0, 1.0))
}

/// CSS Color 4 gamut mapping (section 13.2): reduce OKLCH chroma until the clipped color is
/// within a just-noticeable difference of the candidate. Input and output are linear sRGB.
fn gamut_map(origin: [f64; 3]) -> [f64; 3] {
    let [l, a, b] = linear_srgb_to_oklab(origin);
    if l >= 1.0 {
        return [1.0; 3];
    }
    if l <= 0.0 {
        return [0.0; 3];
    }
    if in_gamut(origin) {
        return clip(origin);
    }
    let mut clipped = clip(origin);
    if delta_ok(linear_srgb_to_oklab(clipped), [l, a, b]) < JND {
        return clipped;
    }
    let (chroma, hue) = (a.hypot(b), b.atan2(a));
    let (mut min, mut max) = (0.0_f64, chroma);
    let mut min_in_gamut = true;
    while max - min > MAP_EPSILON {
        let probe = f64::midpoint(min, max);
        let candidate = [l, probe * hue.cos(), probe * hue.sin()];
        let rgb = oklab_to_linear_srgb(candidate);
        if min_in_gamut && in_gamut(rgb) {
            min = probe;
            continue;
        }
        clipped = clip(rgb);
        let error = delta_ok(linear_srgb_to_oklab(clipped), candidate);
        if error < JND {
            if JND - error < MAP_EPSILON {
                return clipped;
            }
            min_in_gamut = false;
            min = probe;
        } else {
            max = probe;
        }
    }
    clipped
}

/// Builds a [`Color`] from linear sRGB of any gamut, mapping it into sRGB.
pub(crate) fn color_from_linear(rgb: [f64; 3], alpha: f64) -> Color {
    let [r, g, b] = gamut_map(rgb).map(lin_to_srgb);
    Color::new(
        r.clamp(0.0, 1.0),
        g.clamp(0.0, 1.0),
        b.clamp(0.0, 1.0),
        alpha.clamp(0.0, 1.0),
    )
}

impl Color {
    /// This color as OKLab `[L, a, b]` (L 0-1), alpha ignored.
    pub fn to_oklab(self) -> [f64; 3] {
        linear_srgb_to_oklab([self.r, self.g, self.b].map(srgb_to_lin))
    }

    /// deltaE_OK, the Euclidean OKLab distance (about 0.02 is a just-noticeable difference);
    /// alpha ignored.
    pub fn delta_e_ok(self, other: Self) -> f64 {
        delta_ok(self.to_oklab(), other.to_oklab())
    }
}

/// Splits `inner` into three main tokens and an optional alpha token (space syntax only).
fn split_args(inner: &str) -> Option<([&str; 3], Option<&str>)> {
    let (main, alpha) = match inner.split_once('/') {
        Some((main, alpha)) if !alpha.contains('/') => (main, Some(alpha.trim())),
        Some(_) => return None,
        None => (inner, None),
    };
    let mut tokens = main.split_whitespace();
    let found = [tokens.next()?, tokens.next()?, tokens.next()?];
    tokens.next().is_none().then_some((found, alpha))
}

/// A component: `none`, a number, or a percent resolved against `percent_of`.
fn component(token: &str, percent_of: f64) -> Option<f64> {
    if token == "none" {
        return Some(0.0);
    }
    match token.strip_suffix('%') {
        Some(num) => parse_number(num).map(|v| v / 100.0 * percent_of),
        None => parse_number(token),
    }
}

/// A hue angle in degrees: `none`, a bare number, or `deg`/`grad`/`rad`/`turn`.
fn hue(token: &str) -> Option<f64> {
    if token == "none" {
        return Some(0.0);
    }
    let (value, unit) = split_number(token)?;
    let degrees = match unit {
        "" | "deg" => value,
        "grad" => value * 0.9,
        "rad" => value.to_degrees(),
        "turn" => value * 360.0,
        _ => return None,
    };
    Some(degrees.rem_euclid(360.0))
}

/// The alpha token: `none`, a number or a percent, clamped to `[0, 1]`.
fn alpha(token: Option<&str>) -> Option<f64> {
    token.map_or(Some(1.0), |t| component(t, 1.0).map(|v| v.clamp(0.0, 1.0)))
}

/// Lab (D50) to linear sRGB.
fn lab_to_linear(l: f64, a: f64, b: f64) -> [f64; 3] {
    let f1 = (l + 16.0) / 116.0;
    let f0 = a / 500.0 + f1;
    let f2 = f1 - b / 200.0;
    let cubed = |f: f64| {
        if f.powi(3) > LAB_EPSILON {
            f.powi(3)
        } else {
            (116.0 * f - 16.0) / LAB_KAPPA
        }
    };
    let y = if l > LAB_KAPPA * LAB_EPSILON {
        f1.powi(3)
    } else {
        l / LAB_KAPPA
    };
    let xyz50 = [
        cubed(f0) * WHITE_D50[0],
        y * WHITE_D50[1],
        cubed(f2) * WHITE_D50[2],
    ];
    mul(&XYZ_TO_LIN_SRGB, mul(&D50_TO_D65, xyz50))
}

/// Polar to rectangular for LCH and OKLCH.
fn polar(chroma: f64, hue_degrees: f64) -> (f64, f64) {
    let radians = hue_degrees.to_radians();
    (chroma * radians.cos(), chroma * radians.sin())
}

/// `lab()` / `lch()` / `oklab()` / `oklch()` / `hwb()`: the parsed color or `None` when malformed.
fn parse_named(name: &str, inner: &str) -> Option<Color> {
    let (t, a) = split_args(inner)?;
    let alpha = alpha(a)?;
    let rgb = match name {
        "oklab" => {
            let l = component(t[0], 1.0)?.clamp(0.0, 1.0);
            oklab_to_linear_srgb([l, component(t[1], 0.4)?, component(t[2], 0.4)?])
        }
        "oklch" => {
            let l = component(t[0], 1.0)?.clamp(0.0, 1.0);
            let (ca, cb) = polar(component(t[1], 0.4)?.max(0.0), hue(t[2])?);
            oklab_to_linear_srgb([l, ca, cb])
        }
        "lab" => {
            let l = component(t[0], 100.0)?.clamp(0.0, 100.0);
            lab_to_linear(l, component(t[1], 125.0)?, component(t[2], 125.0)?)
        }
        "lch" => {
            let l = component(t[0], 100.0)?.clamp(0.0, 100.0);
            let (ca, cb) = polar(component(t[1], 150.0)?.max(0.0), hue(t[2])?);
            lab_to_linear(l, ca, cb)
        }
        "hwb" => return hwb(t, alpha),
        _ => return None,
    };
    Some(color_from_linear(rgb, alpha))
}

/// `hwb(h w b)`: HSL's hue wheel with whiteness and blackness mixed in (already sRGB).
fn hwb(t: [&str; 3], alpha: f64) -> Option<Color> {
    let h = hue(t[0])? / 360.0;
    let pct = |token: &str| {
        if token == "none" {
            Some(0.0)
        } else {
            component(token.strip_suffix('%').map(|_| token)?, 1.0).map(|v| v.clamp(0.0, 1.0))
        }
    };
    let (white, black) = (pct(t[1])?, pct(t[2])?);
    if white + black >= 1.0 {
        let gray = white / (white + black);
        return Some(Color::new(gray, gray, gray, alpha));
    }
    // The hsl(h, 100%, 50%) wheel (channel offsets 0, 8, 4), scaled by whiteness and blackness.
    let channel = |offset: f64| {
        let k = (offset + h * 12.0).rem_euclid(12.0);
        let wheel = 0.5 - 0.5 * (k - 3.0).min(9.0 - k).clamp(-1.0, 1.0);
        wheel * (1.0 - white - black) + white
    };
    Some(Color::new(channel(0.0), channel(8.0), channel(4.0), alpha))
}

/// `color(<space> c1 c2 c3 [/ alpha])` for the predefined RGB and XYZ spaces.
fn parse_color_fn(inner: &str) -> Option<Color> {
    let (space, rest) = inner.trim().split_once(char::is_whitespace)?;
    let (t, a) = split_args(rest)?;
    let alpha = alpha(a)?;
    let c = [
        component(t[0], 1.0)?,
        component(t[1], 1.0)?,
        component(t[2], 1.0)?,
    ];
    let linear = match space {
        "srgb" => c.map(srgb_to_lin),
        "srgb-linear" => c,
        "display-p3" => mul(&XYZ_TO_LIN_SRGB, mul(&LIN_P3_TO_XYZ, c.map(srgb_to_lin))),
        "a98-rgb" => mul(
            &XYZ_TO_LIN_SRGB,
            mul(
                &LIN_A98_TO_XYZ,
                c.map(|v| v.signum() * v.abs().powf(563.0 / 256.0)),
            ),
        ),
        "rec2020" => mul(
            &XYZ_TO_LIN_SRGB,
            mul(&LIN_REC2020_TO_XYZ, c.map(rec2020_to_lin)),
        ),
        "prophoto-rgb" => mul(
            &XYZ_TO_LIN_SRGB,
            mul(
                &D50_TO_D65,
                mul(&LIN_PROPHOTO_TO_XYZ_D50, c.map(prophoto_to_lin)),
            ),
        ),
        "xyz" | "xyz-d65" => mul(&XYZ_TO_LIN_SRGB, c),
        "xyz-d50" => mul(&XYZ_TO_LIN_SRGB, mul(&D50_TO_D65, c)),
        _ => return None,
    };
    Some(color_from_linear(linear, alpha))
}

/// Rec. 2020 transfer function, encoded to linear.
fn rec2020_to_lin(c: f64) -> f64 {
    const ALPHA: f64 = 1.099_296_826_809_44;
    const BETA: f64 = 0.018_053_968_510_807;
    let a = c.abs();
    if a < BETA * 4.5 {
        c / 4.5
    } else {
        c.signum() * ((a + ALPHA - 1.0) / ALPHA).powf(1.0 / 0.45)
    }
}

/// ProPhoto RGB transfer function, encoded to linear.
fn prophoto_to_lin(c: f64) -> f64 {
    let a = c.abs();
    if a <= 16.0 / 512.0 {
        c / 16.0
    } else {
        c.signum() * a.powf(1.8)
    }
}

/// Parses a lowercase CSS Color 4 function, or `None` when `text` is not one of them.
///
/// `Some(Err(..))` means it is one of the functions but malformed or unsupported (for example a
/// relative color with `from`).
pub(crate) fn parse_wide(text: &str) -> Option<Result<Color, ColorError>> {
    let (name, rest) = text.split_once('(')?;
    let name = name.trim();
    let known = matches!(name, "oklab" | "oklch" | "lab" | "lch" | "hwb" | "color");
    if !known {
        return None;
    }
    let bad = || {
        tracing::debug!(text, "color parse reject: bad CSS Color 4 function");
        ColorError::BadColorFunction(name.to_owned())
    };
    let parsed = rest
        .trim_end()
        .strip_suffix(')')
        .and_then(|inner| match name {
            "color" => parse_color_fn(inner),
            _ => parse_named(name, inner),
        });
    Some(parsed.ok_or_else(bad))
}
