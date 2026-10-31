The Rust adapter now folds each fn returning Result<T, E> into gob-ir error-flow facts, resolving E to a closed enum, a non-exhaustive enum, an erased type or unresolved.
