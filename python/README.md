# Python native licensing example

[Source](main.py) · [Full setup and supported modes](../README.md) · [Documentation](https://docs.babelfor.net/licensing/examples/native-sdk)

From the repository root:

```sh
python3 scripts/setup-sdk.py
./run.sh python
./run.sh python demo/trial.xml
./run.sh python /absolute/path/customer.xml /absolute/path/publisher-key.txt RSA Pro
```

The preview runtime requires an Apple Silicon Mac and targets macOS 15 or later. Read the root README before integrating the example into a product. Signature verification and runtime validation must both succeed before a feature is enabled.
