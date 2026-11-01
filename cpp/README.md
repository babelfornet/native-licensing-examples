# C++ native licensing example

[Source](main.cpp) · [Full setup and supported modes](../README.md)

The native ABI library is awaiting release. Automatic SDK downloads are disabled until that release. See the root README for testing a supplied preview archive.

Once the SDK is available, run from the repository root:

```sh
python3 scripts/setup-sdk.py
./run.sh cpp
./run.sh cpp demo/trial.xml
./run.sh cpp /absolute/path/customer.xml /absolute/path/publisher-key.txt RSA Pro
```

The preview runtime requires an Apple Silicon Mac and targets macOS 15 or later. Read the root README before integrating the example into a product. Signature verification and runtime validation must both succeed before a feature is enabled.


### Activation and floating

After installing the matching unreleased SDK archive, follow the root README's
local service setup or configure your own Licensing Service and publisher key.
Run from the repository root:

```sh
./run.sh cpp --online activation
./run.sh cpp --online floating
```

Activation includes service validation and deactivation; floating includes two
heartbeat renewals and release. Both check the signed license, current grant
and `Pro` entitlement before protected work and attempt cleanup on failure.
The same build configuration and single native runtime library serve all modes.
See the root README for credentials, stable identities, TLS and failure handling.


## CMake build

The repository-root `CMakeLists.txt` uses the header and runtime from `.sdk` and copies the single Babel runtime beside the executable:

```sh
cmake -S . -B .build/cmake -DCMAKE_BUILD_TYPE=Release
cmake --build .build/cmake --config Release
./.build/cmake/native-example
```

On Windows with the Visual Studio generator, run `.build/cmake/Release/native-example.exe` from the repository root. Ninja places it directly under `.build/cmake`. CMake copies the DLL automatically. Move the executable and its adjacent Babel runtime together when packaging your application.
