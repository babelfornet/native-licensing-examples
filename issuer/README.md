# Publisher-side sample issuer

This optional .NET program signs licenses for your own application. It requires the Babel Licensing .NET assemblies from your trial or purchased SDK and .NET 10. The Rust, Go, C++ and Python clients do not require .NET.

From the repository root:

```sh
dotnet run --project issuer/Issuer.csproj \
  -p:BabelLicensingDirectory=/absolute/path/to/your/sdk/assemblies \
  -- issued 30

./run.sh cpp issued/trial.xml issued/publisher-key.txt RSA Pro
```

The assembly directory must contain `Babel.Licensing.dll` and `Crypto.dll`. The issuer stores its private key in `issued/private/publisher-private-key.txt`. Keep that file on the publisher's machine and back it up securely; use the same key when renewing licenses for an existing product. Distribute only the customer's signed XML and the public key pinned by your application.

The second argument is the trial duration in days. Trial files use an absolute `ExpireDate`. Stateful trial restrictions remain unsupported by the native preview. Files named `expired.xml`, `no-feature.xml` and `restricted.xml` exercise refusal paths.

The `--repository-fixtures` switch is only for maintaining this repository's demonstration data. It gives the static trial a 2099 expiry; omit that switch for an actual time-limited trial.
