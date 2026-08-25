#!/usr/bin/env bash

# Adds two numbers.
add() {
    echo $(( $1 + $2 ))
}

# sum them and print
_hidden() {
    add 1 2
}

export MAX_WIDGETS=10
