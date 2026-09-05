/* T-3895: a zero-width anonymous bit-field (ISO C11 6.7.2.1p12 -- a
 * bit-field declarator with no identifier is legal and forces the next
 * bit-field to start at the next allocation unit boundary). Common in
 * embedded/HAL register-layout structs. tree-sitter's "c" grammar (via
 * tree-sitter-language-pack, the only C parser frob.lang ships) cannot
 * parse the no-identifier form and salvages a partial tree around it --
 * PARSE002 fires on this file regardless of whether frob-core/strata-core
 * are installed (see TestKnownGrammarGaps.
 * test_anonymous_bitfield_partial_parse_is_native_independent). This
 * fixture pins that gap so a future tree-sitter-language-pack upgrade
 * that happens to fix it is a visible test change, not a silent one.
 */
struct gpio_regs {
    unsigned moder : 16;
    unsigned : 0;
    unsigned idr : 16;
};
