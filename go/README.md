# Go native licensing example

[Source](main.go) · [Full setup and supported modes](../README.md)

The native ABI library is awaiting release. Automatic SDK downloads are disabled until that release. See the root README for testing a supplied preview archive.

Once the SDK is available, run from the repository root:

```sh
python3 scripts/setup-sdk.py
./run.sh go
./run.sh go demo/trial.xml
./run.sh go /absolute/path/customer.xml /absolute/path/publisher-key.txt RSA Pro
```

The preview runtime requires an Apple Silicon Mac and targets macOS 15 or later. Read the root README before integrating the example into a product. Signature verification and runtime validation must both succeed before a feature is enabled.
