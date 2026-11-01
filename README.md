# Babel Licensing native examples

Use Babel Licensing from **Rust, Go, C++ or Python** to verify a signed license in your own application. Each example loads an XML license, verifies its publisher signature, validates runtime expiry and enables a named feature. A rejected file exits with a nonzero status.

[Read the documentation](https://docs.babelfor.net/licensing/examples/native-sdk) or open an example:

| Language | Example | Client dependency |
|---|---|---|
| Rust | [rust/](rust/) | Rust FFI and the native shared library |
| Go | [go/](go/) | cgo and the native shared library |
| C++ | [cpp/](cpp/) | Public C header and the native shared library |
| Python | [python/](python/) | Standard-library `ctypes` and the native shared library |

## Preview platform

The downloadable SDK preview is for **Apple Silicon Macs, targeting macOS 15 or later**. It has been tested on macOS 27.0.1. Windows, Linux and Intel Mac packages are not available in this preview. The native C ABI can support other language bindings; this repository tests the four examples above.

This preview supports offline XML licenses, RSA-SHA1, ECDSA P-256, absolute license expiry and feature expiry. Compact licenses, online activation and stateful restrictions such as run counts, days from first use, hardware, domain and custom restrictions are not implemented. The validator refuses licenses containing unsupported restriction nodes.

## Run an example

Install Python 3 and the toolchain for your chosen language. C++ and Go/cgo need the Xcode command-line tools; Rust needs Cargo. You do not need .NET or a Licensing Service to run the supplied signed examples.

```sh
git clone https://github.com/babelfornet/native-licensing-examples.git
cd native-licensing-examples
python3 scripts/setup-sdk.py

./run.sh python
./run.sh rust
./run.sh go
./run.sh cpp
```

Run whichever language you use. The setup script downloads a pinned SDK release, checks SHA-256 and installs it in `.sdk`. The archive includes Botan and its native dependencies, so it does not require a separate Homebrew Botan installation. Read `.sdk/EULA.md` and `.sdk/THIRD_PARTY_NOTICES.txt` for the SDK's terms and notices. The MIT license in this repository covers the example sources; the SDK binaries have their own terms.

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

`restricted.xml` illustrates a stateful trial the preview does not support. Refusing it is expected; use absolute `ExpireDate` for the supported trial workflow.

## Use your own publisher key and licenses

```sh
./run.sh python /absolute/path/customer.xml /absolute/path/publisher-key.txt RSA Pro
```

All examples accept the same arguments:

```text
[license.xml [publisher-key.txt [RSA|ECDSA [feature]]]]
```

For RSA, the key file contains Base64 X.509 SubjectPublicKeyInfo DER, as returned by `.NET RSASignature.ExportKeys(true)`. For ECDSA, use an explicit P-256 key and its Babel Base32 public-point encoding. The legacy .NET default 112-bit curve is not supported by this preview.

The examples read the trusted public key from a separate file so you can try your own publisher. In your product, pin that key in the application or in trusted configuration. Never select it from the license document or ship the private signing key. Use a separate publisher key for each product if feature names overlap. Product/version and update-entitlement policy remains the application's responsibility; these examples demonstrate signature, expiry and feature checks.

### Issue files with a trial or purchased Babel Licensing SDK

Use the .NET `Babel.Licensing.dll` and `Crypto.dll` from your SDK. See [Client components](https://docs.babelfor.net/licensing/getting-started/client-components) for the Babel Licensing installation workflow.

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
