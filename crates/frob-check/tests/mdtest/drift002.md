<!-- mdtest: rule=DRIFT002 -->
# DRIFT002 dangling doc target

A `frob:doc` directive must name a heading that exists.

## A mistyped heading fires

```text expect=fire
=== src/lib.rs
// frob:doc docs/guide.md#greting
pub fn greet() {}
=== docs/guide.md
# Guide

## Greeting

Greets a person by name.

```

## An existing heading is clean

```text expect=clean
=== src/lib.rs
// frob:doc docs/guide.md#greeting
pub fn greet() {}
=== docs/guide.md
# Guide

## Greeting

Greets a person by name.

```
