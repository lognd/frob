## Done report

frob-core PyO3/maturin crate (r3_canonical_hash, winnow, candidate_pairs,
tree_edit_similarity; 5/5 cargo tests) + the smart-dup Python pipeline
(find_clones R1/R2 pure-Python, R3 via frob-core, no silent fallback);
DUP001/DUP002 wired as the opt-in 'clones' gate; make core + CI build
the Rust side. Delivers the buildable core of T-0001.
