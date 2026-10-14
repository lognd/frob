Rust lowering in gob-symbols is stack-safe: files nested thousands of levels deep lower on a depth-sized stack, and the depth-limit cap rose from 160 to 20000 as the honest fallback.
