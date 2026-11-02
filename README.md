# Babel Licensing native examples

**Babel Licensing Native SDK 12.2.0 · C ABI 2.** Platform ZIPs are available in the [12.2.0 release](https://github.com/babelfornet/native-licensing-examples/releases/tag/v12.2.0). The setup script downloads the pinned package for your platform and verifies SHA-256.

Use Babel Licensing from **Rust, Go, C++ or Python** to verify a signed license in your own application. Each example verifies offline XML/compact licenses and demonstrates online activation and floating acquire/heartbeat/release through the same native C ABI. A rejected file exits with a nonzero status.

Open an example:

| Language | Example | Client dependency |
|---|---|---|
| Rust | [rust/](rust/) | Rust FFI and the native shared library |
| Go | [go/](go/) | cgo and the native shared library |
| C++ | [cpp/](cpp/) | Public C header and the native shared library |
| Python | [python/](python/) | Standard-library `ctypes` and the native shared library |

## Platform packages

The release includes separate packages for these targets:

| Platform | Single SDK runtime | Link-time input |
| --- | --- | --- |
| macOS arm64, target macOS 15+ | `lib/libBabelLicensingNative.dylib` | public C header |
| Linux x64, glibc (Ubuntu 22.04 baseline) | `lib/libBabelLicensingNative.so` | public C header |
| Windows x64 | `bin/BabelLicensingNative.dll` | public C header; `lib/BabelLicensingNative.lib` for MSVC/Rust |

Botan is embedded statically in each library. Windows uses the OS Schannel TLS
stack through embedded static curl; Linux embeds curl and OpenSSL and uses the
OS CA trust store. The runtime does not require a Botan, curl or OpenSSL DLL/so
beside the SDK. Normal OS facilities/runtime remain required. Linux musl/Alpine,
Linux arm64, Windows arm64 and Intel Mac packages are not prepared here.

The build supports XML and compact ASCII/Base32 licenses with RSA-SHA1 or
ECDSA P-256, absolute license/feature expiry, activation with a signed machine
binding, and floating acquisition/heartbeat/release. Stateful trial, domain,
usage and custom restrictions are refused. Raw offline validation refuses
hardware restrictions; the online session validates the signed machine binding.

## Run an example

Install Python 3.9+ and the toolchain for your chosen language. On macOS, C++ and Go/cgo need the Xcode command-line tools; Linux needs a C/C++ compiler. Windows toolchain requirements are listed below. Rust needs Cargo and the platform linker. Offline examples need neither .NET nor a Licensing Service. Online examples use your service or the loopback fixture below.

```sh
git clone https://github.com/babelfornet/native-licensing-examples.git
cd native-licensing-examples
python3 scripts/setup-sdk.py

./run.sh python
./run.sh rust
./run.sh go
./run.sh cpp
```

Run whichever language you use. The setup script downloads the pinned SDK package, checks SHA-256 and installs it in `.sdk`. To use a ZIP you already downloaded, run `python3 scripts/setup-sdk.py --archive /absolute/path/sdk.zip`. The runtime is **one file**: `.sdk/lib/libBabelLicensingNative.dylib` on macOS, `.sdk/lib/libBabelLicensingNative.so` on Linux, or `.sdk/bin/BabelLicensingNative.dll` on Windows. Required Botan modules are linked statically into it: do not install or distribute a separate Botan or SQLite dylib. macOS system libraries are used normally. Read `.sdk/EULA.md` and `.sdk/licenses/` for SDK terms and third-party notices. The MIT license in this repository covers the example sources; the SDK binaries have their own terms.

Successful output:

```text
License verified. Feature Pro enabled.
```

## Try trial, purchased and rejected licenses

```sh
./run.sh python demo/trial.xml       # accepted, absolute expiry
./run.sh python demo/perpetual.xml   # accepted, no license expiry
./run.sh python demo/expired.xml     # refused, status 10
./run.sh python demo/no-feature.xml  # refused, Pro is absent
./run.sh python demo/restricted.xml  # refused, status 4
```

Replace `python` with `rust`, `go` or `cpp`. These files are signed demo licenses for this example application, not Babel Obfuscator product licenses. The checked-in trial expires on 2099-01-01 to keep the demo reusable. The optional issuer creates an actual 30-day trial when you issue your own files. A perpetual license can still contain expiring features.

`restricted.xml` illustrates a stateful trial the SDK does not support. Refusing it is expected; use absolute `ExpireDate` for the supported trial workflow.

## Use your own publisher key and licenses

```sh
./run.sh python /absolute/path/customer.xml /absolute/path/publisher-key.txt RSA Pro
```

All examples accept the same arguments:

```text
[license.xml [publisher-key.txt [RSA|ECDSA [feature]]]]
```

For RSA, the key file contains Base64 X.509 SubjectPublicKeyInfo DER, as returned by `.NET RSASignature.ExportKeys(true)`. For ECDSA, use an explicit P-256 key and its Babel Base32 public-point encoding. The legacy .NET default 112-bit curve is not supported by the native SDK.

The examples read the trusted public key from a separate file so you can try your own publisher. In your product, pin that key in the application or in trusted configuration. Never select it from the license document or ship the private signing key. Use a separate publisher key for each product if feature names overlap. Product/version and update-entitlement policy remains the application's responsibility; these examples demonstrate signature, expiry and feature checks.

### Issue files with a trial or purchased Babel Licensing SDK

Use the protected .NET `Babel.Licensing.dll` from your SDK or the Babel.Licensing NuGet package. The distributed assembly includes its cryptography implementation; no separate `Crypto.dll` is required. See [Client components](https://docs.babelfor.net/licensing/getting-started/client-components) for the Babel Licensing installation workflow.

```sh
# .NET 10 SDK; point to the directory containing your Babel Licensing assemblies.
dotnet run --project issuer/Issuer.csproj \
  -p:BabelLicensingDirectory=/absolute/path/to/your/sdk/assemblies \
  -- issued 30

./run.sh rust issued/trial.xml issued/publisher-key.txt RSA Pro
./run.sh go issued/perpetual.xml issued/publisher-key.txt RSA Pro
```

The issuer creates a 2048-bit RSA key pair on first use. It saves the private key under `issued/private/`, writes the public key separately and signs trial, perpetual and negative-test files. Keep the private directory on the publisher's machine. Subsequent runs reuse that key so existing applications retain the same trust anchor. `issued/` and private-key files are excluded from Git.

Issuing new files is a publisher operation. End-user applications only need the public key, their license file and the native runtime.

## Validation order and errors

The C entry points use UTF-8, opaque handles, caller-owned buffers and integer statuses. They expose no C++ object across the language boundary. Every example checks ABI version 2 and owns exactly one handle until it calls `babel_license_free`.

1. `babel_license_load` parses untrusted data. Parsing success does not authorize a feature.
2. `babel_license_verify` authenticates with a mandatory pinned public key. A failed attempt clears prior authentication.
3. `babel_license_validate` checks license expiry and refuses unsupported restrictions.
4. `babel_license_feature_enabled` grants only an authenticated, runtime-valid, unexpired feature.

Common statuses are `1` (invalid argument), `2` (parse failure), `3` (invalid signature), `4` (unsupported format/restriction) and `10` (license expired). The [public header](sdk/include/babel/babel_licensing.h) defines the full API. The SDK's maintenance helper checks release eligibility without the current clock; it is separate from absolute license expiry and is not a replacement for authenticated release metadata.

## Test all four examples

```sh
python3 scripts/test-examples.py
```

The test runs 28 scenarios: valid perpetual, absolute-expiry trial, expired, missing feature, unsupported restriction, edited content and wrong publisher key in each language. All four programs must refuse the negative cases.

## Activation and floating licenses

Local online changes are prepared for the coordinated release; this repository
has no published native ABI package yet. Install the matching supplied archive
as described above before running these modes.

For a loopback protocol demonstration, open a separate terminal:

```sh
python3 scripts/demo-service.py
```

In the application terminal, from this repository root:

```sh
export BABEL_SERVICE_URL=http://127.0.0.1:8765/
export BABEL_ALLOW_LOOPBACK_HTTP=1
export BABEL_MACHINE_ID=native-example-machine
export BABEL_CLIENT_ID=native-example-python
export BABEL_PUBLISHER_KEY_FILE="$PWD/demo/publisher-key.txt"
export BABEL_ALGORITHM=RSA
export BABEL_USER_KEY=demo-activation
./run.sh python --online activation
export BABEL_USER_KEY=demo-floating
./run.sh python --online floating
```

Replace `python` with `rust`, `go` or `cpp`. Activation verifies the signed
machine-bound compact license, checks `Pro`, validates with the service and
deactivates. Floating verifies the signed license, acquires a seat, checks
validity, renews twice and releases. Both paths attempt cleanup on error and
free the native handle. The fixture is not a license issuer or production
service: it only serves signed demo payloads and disposable credentials.
No signing private key is included or needed. Demo payloads expire in 2099;
the publisher-side issuer's ordinary mode creates a real 30-day expiry.

For your actual application, configure an activation/floating license and a
supported publisher key in your Babel Licensing Service, then use:

```sh
unset BABEL_ALLOW_LOOPBACK_HTTP BABEL_MACHINE_ID
export BABEL_SERVICE_URL=https://your-licensing-service.example/
export BABEL_PUBLISHER_KEY_FILE=/absolute/path/your-publisher-public-key.txt
# Set BABEL_USER_KEY through secure application configuration.
./run.sh python --online activation
# Or use a floating user key and --online floating.
```

The service URL is the root; the native SDK uses `v1/auth/login` and
`v1/license/*`, matching the .NET REST client. HTTPS certificate and hostname
validation stay enabled; redirects are not followed. The HTTP test flag permits
only literal loopback addresses. Timeout is 15 seconds per HTTP request.

Without `BABEL_MACHINE_ID`, each example calls `babel_hardware_key`. Keep machine
and client identities stable for activation and distinct for concurrent floating
clients. Pin the public key in your product; the key-file option is for evaluation.
Do not enter real customer credentials in the local demo service.

Call `babel_online_check` before protected work and use the online feature query.
Renew a floating lease for the entire protected session; the two-heartbeat demo
is only a demonstration. Any heartbeat/check failure stops use immediately.
The console examples wait for the interval reported by the service before each heartbeat; with long production intervals, the two-heartbeat demonstration can take several minutes.
No background thread, offline grace, or persistent activation cache is provided.
An expired/lost lease must be acquired again. `free` performs no network cleanup;
release/deactivate explicitly. Cleanup failure disables local use but may leave a
server seat until cleanup succeeds or a floating token expires.

Run all language examples and refusal paths:

```sh
python3 scripts/test-examples.py
python3 scripts/test-online-examples.py
```

The latter covers activation, validation/deactivation, floating acquire/renew/
release, denied grants, wrong hardware and unsupported restrictions in all four
languages. Native HTTP/security tests additionally cover malformed/tampered
responses, limits, invalid TLS, redirects, timeout and lost/expired leases.
These fixture tests do not claim acceptance against a deployed service.

## Test against your installed Licensing Service

Use a dedicated test customer and two licenses signed with the same publisher
key: one activation license and one floating license, both enabling `Pro`.
Allow at least one activation/concurrent session and ensure that no other test
is using those licenses. Install the matching SDK archive and all four language
toolchains before running the suite.

Configure the HTTPS service root and publisher public key as above. Supply the
two test user keys through your local environment or secret manager, using
`BABEL_ACTIVATION_USER_KEY` and `BABEL_FLOATING_USER_KEY`; do not commit them.
Select `BABEL_ALGORITHM=RSA` or `ECDSA` to match the issuing key, then run:

```sh
python3 scripts/test-service-examples.py
```

On Windows, use `python scripts/test-service-examples.py` in a developer terminal.
The suite runs eight lifecycles: activation and floating in Rust, Go, C++ and
Python. It requires a verified `Pro` entitlement, two successful floating
heartbeats and explicit cleanup. It does not issue licenses or require an
administrator API key. It consumes real test activations and floating sessions;
use dedicated evaluation licenses, not customer production credentials.

Keep client and server clocks synchronized and configure a heartbeat interval
that accommodates network latency, clock skew and pauses. The SDK rejects an
already expired lease. A two-second interval is useful for isolated expiry tests
but unsuitable for machines whose clocks differ by several seconds. For a local
HTTP test deployment only, use the explicit loopback flag described above.
After the run, inspect the service’s activation/token list to confirm cleanup;
a lost HTTP response can still require server-side reconciliation.

## Windows and portable commands

Python 3.9+ selects the current platform package and runs the same client code:

```powershell
python scripts/setup-sdk.py --archive C:\Downloads\matching-windows-x64-sdk.zip
python scripts/run-example.py cpp
python scripts/run-example.py rust
python scripts/run-example.py go
python scripts/run-example.py python
python scripts/run-example.py rust --online activation
python scripts/run-example.py rust --online floating
```

Configure the online environment variables as above using PowerShell's
`$env:BABEL_SERVICE_URL = "..."` syntax. Use an x64 Visual Studio developer terminal
for C++/Rust MSVC. Go/cgo needs a MinGW-compatible GCC or Clang with its runtime
headers (MSYS2 UCRT64 or LLVM-MinGW); point `CC` at that compiler, not `cl.exe`.
The runner adds `.sdk/bin` to the child process PATH on Windows. For a deployed
executable, put the single DLL next to it or on its controlled DLL search path.

Linux/macOS use `python3 scripts/run-example.py` or `./run.sh`. Platform-specific
cgo directives and Cargo `build.rs` omit Unix rpath flags on Windows. Python's
`runtime_path()` chooses the correct `.dll`, `.so` or `.dylib`.


Rust runner regression: `python3 scripts/test-rust-build.py` (`python` on Windows)
verifies a custom `CARGO_TARGET_DIR` and a moved checkout with the same cache.
The runner uses Cargo's actual executable artifact and tracks the SDK library
directory through `BABEL_NATIVE_SDK_LIB_DIR`.

### License identity

Use the pinned publisher identity and authenticated license ID for license
identity, deduplication or revocation records. Legacy ECDSA high-S and low-S
signatures remain valid and are normalized internally by the SDK; raw signature
or file hashes are not stable license identities. The examples validate the
signed entitlement and expiry before enabling protected application work.
