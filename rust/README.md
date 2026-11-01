# Rust native licensing example

[Source](src/main.rs) · [Full setup and supported modes](../README.md)

The native ABI library is awaiting release. Automatic SDK downloads are disabled until that release. See the root README for testing a supplied preview archive.

Once the SDK is available, run from the repository root:

```sh
python3 scripts/setup-sdk.py
./run.sh rust
./run.sh rust demo/trial.xml
./run.sh rust /absolute/path/customer.xml /absolute/path/publisher-key.txt RSA Pro
```

The preview runtime requires an Apple Silicon Mac and targets macOS 15 or later. Read the root README before integrating the example into a product. Signature verification and runtime validation must both succeed before a feature is enabled.


### Activation and floating

After installing the matching unreleased SDK archive, follow the root README's
local service setup or configure your own Licensing Service and publisher key.
Run from the repository root:

```sh
./run.sh rust --online activation
./run.sh rust --online floating
```

Activation includes service validation and deactivation; floating includes two
heartbeat renewals and release. Both check the signed license, current grant
and `Pro` entitlement before protected work and attempt cleanup on failure.
The same build configuration and single native runtime library serve all modes.
See the root README for credentials, stable identities, TLS and failure handling.


Rust runner regression: `python3 scripts/test-rust-build.py` (`python` on Windows)
verifies a custom `CARGO_TARGET_DIR` and a moved checkout with the same cache.
The runner uses Cargo's actual executable artifact and tracks the SDK library
directory through `BABEL_NATIVE_SDK_LIB_DIR`.
