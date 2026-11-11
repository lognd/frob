# Text-shaping spike: cosmic-text against parley (ticket ~HKN808M)

Question (docs/design/crunk/crunk.md section 3, D113): which shaping library
measures text for the crunk T1 solver over bundled fonts?

## Method

- Harness: `notes/research/text-shaping-spike/` (standalone cargo project, own
  `[workspace]`, not a member of the repo workspace). `gen_corpus.py` writes
  `corpus.json` (200 strings, seed fixed: kerning pairs, ligature candidates,
  digits, punctuation, mixed-length sentences, one empty string). `src/main.rs`
  measures it with both libraries; `run_chromium.py` measures the same strings
  in headless Chromium (playwright build 1248, arm64) with `white-space: pre`
  and `@font-face` on the same files; `compare.py` diffs them.
- Fonts (the same files are fed to all three engines): DejaVu Sans, Liberation
  Serif, Lato Regular, 16 px, no system fonts loaded in either library.
- Versions: cosmic-text 0.19.0 (default-features off, `std` + `swash`), parley
  0.12.0 (default-features off, `std`; the design named 0.11, 0.12 is current).
- Width is the unwrapped single-line advance sum. 600 measurements per engine.
- Timing: 20 passes over the 200 strings x 3 fonts, release build, per string
  including buffer or layout construction and shaping (warm font contexts).
- Determinism: two independent font contexts, plus two separate process runs;
  widths compared bit for bit.
- Raw results: `notes/research/text-shaping-spike/results.json`.

## Results

Empty string excluded from deltas (parley reports a 5 px phantom width for ""
because it lays out one notdef-sized cluster; the solver must special-case
empty text regardless). Chromium widths are quantised to 1/64 px.

| library | mean abs delta | max delta | strings > 0.05 px | us per string | deterministic |
|---|---|---|---|---|---|
| parley 0.12 | 0.0047 px | 0.0149 px | 0 of 597 | 16.4 | yes |
| cosmic-text 0.19 | 0.1687 px | 2.1698 px | 131 of 597 | 24.8 | yes |

Per font, cosmic-text: DejaVu Sans max 0.008 px; Liberation Serif max 2.05 px;
Lato max 2.17 px. Parley: 0.008, 0.008, 0.015 px.

Cause of the cosmic-text gap: every divergence is a string containing a space
(max 2.17 px over 420 such measurements, 0.015 px over 177 without). cosmic-text
shapes word by word, so kerning across the space (for example "R W" in
"AVATAR WAVE", 107.63 against Chromium 107.34) is lost; DejaVu Sans has little
space kerning, which is why it looks fine there. Parley shapes the whole run
like Chromium does.

Build note: cosmic-text and parley with default features pull `fontconfig-sys`
and need system libfontconfig headers. Both work with defaults off and fonts
loaded explicitly, which is what the solver wants anyway (bundled fonts only).

## Decision

Use parley for solver text measurement. It agrees with Chromium within 0.015 px
on every sample (the solver can treat 0.05 px as parity tolerance), is about
1.5x faster per string, and is deterministic across contexts and processes.
cosmic-text is rejected because per-word shaping drifts by up to 2.2 px on
multi-word strings, which would produce false overflow and wrap findings.
Follow-up work: ~6XH9D6C wires parley behind the measure hook; handle the
empty-string case there.
