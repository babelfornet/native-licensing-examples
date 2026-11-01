#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ ! -f .sdk/lib/libBabelLicensingNative.dylib ]]; then
    echo 'Run python3 scripts/setup-sdk.py first.' >&2
    exit 1
fi
language="${1:-python}"
if [[ $# -gt 0 ]]; then shift; fi
mkdir -p .build
case "$language" in
    python) exec python3 python/main.py "$@" ;;
    cpp)
        c++ -std=c++20 -Isdk/include cpp/main.cpp -L.sdk/lib -lBabelLicensingNative -Wl,-rpath,"$ROOT/.sdk/lib" -o .build/cpp-example
        exec .build/cpp-example "$@" ;;
    go)
        CGO_ENABLED=1 go build -o .build/go-example go/main.go
        exec .build/go-example "$@" ;;
    rust)
        cargo build --quiet --manifest-path rust/Cargo.toml
        exec rust/target/debug/babel-native-licensing-example "$@" ;;
    *) echo 'Choose python, cpp, go or rust.' >&2; exit 1 ;;
esac
