#!/usr/bin/env bash

set -euo pipefail
shopt -s nullglob

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_root="${IODX_SOURCE_ROOT:-"$repo_root/../iodx"}"
source_grammar="$source_root/src/main/congocc/common"
source_fixtures="$source_root/src/test/resources"
target_grammar="$repo_root/grammar/common"
target_fixtures="$repo_root/tests/resources/upstream"
grammar_files=(IodxTokens.inc.ccc IodxProductions.inc.ccc)

usage() {
    echo "Usage: $0 [--check]" >&2
    echo "Set IODX_SOURCE_ROOT to override the default sibling ../iodx repository." >&2
}

if [[ $# -gt 1 || (${1:-} != "" && ${1:-} != "--check") ]]; then
    usage
    exit 2
fi

for name in "${grammar_files[@]}"; do
    if [[ ! -f "$source_grammar/$name" ]]; then
        echo "Missing upstream grammar: $source_grammar/$name" >&2
        exit 1
    fi
done

fixture_files=("$source_fixtures"/*.iodx)
if [[ ${#fixture_files[@]} -eq 0 ]]; then
    echo "No upstream .iodx fixtures found in $source_fixtures" >&2
    exit 1
fi

if [[ ${1:-} == "--check" ]]; then
    stale=0

    for name in "${grammar_files[@]}"; do
        if ! cmp -s "$source_grammar/$name" "$target_grammar/$name"; then
            echo "Out of sync: grammar/common/$name" >&2
            stale=1
        fi
    done

    for source in "${fixture_files[@]}"; do
        name="$(basename "$source")"
        if ! cmp -s "$source" "$target_fixtures/$name"; then
            echo "Out of sync: tests/resources/upstream/$name" >&2
            stale=1
        fi
    done

    for target in "$target_fixtures"/*.iodx; do
        name="$(basename "$target")"
        if [[ ! -f "$source_fixtures/$name" ]]; then
            echo "Stale mirrored fixture: tests/resources/upstream/$name" >&2
            stale=1
        fi
    done

    if [[ $stale -ne 0 ]]; then
        exit 1
    fi

    echo "Shared grammar and fixtures are in sync."
    exit 0
fi

mkdir -p "$target_grammar" "$target_fixtures"

for name in "${grammar_files[@]}"; do
    cp "$source_grammar/$name" "$target_grammar/$name"
done

for target in "$target_fixtures"/*.iodx; do
    name="$(basename "$target")"
    if [[ ! -f "$source_fixtures/$name" ]]; then
        rm -f "$target"
    fi
done

for source in "${fixture_files[@]}"; do
    cp "$source" "$target_fixtures/"
done

echo "Synced shared grammar and ${#fixture_files[@]} fixtures from $source_root."
