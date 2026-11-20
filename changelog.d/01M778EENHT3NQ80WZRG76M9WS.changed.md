The rules index generator now emits `#[allow(clippy::too_many_lines)]` with a reason on the generated `bind()`, so a catalog large enough to push it past 100 lines no longer trips clippy.
