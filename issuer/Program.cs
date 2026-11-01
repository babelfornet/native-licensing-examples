using Babel.Licensing;

// Run this on the publisher's machine, never inside a distributed client.
var output = Path.GetFullPath(args.Length > 0 ? args[0] : "issued");
Directory.CreateDirectory(output);
var privateDirectory = Path.Combine(output, "private");
Directory.CreateDirectory(privateDirectory);
var privatePath = Path.Combine(privateDirectory, "publisher-private-key.txt");
RSASignature signer;
if (File.Exists(privatePath)) signer = RSASignature.FromKeys(File.ReadAllText(privatePath));
else {
    signer = new RSASignature(2048);
    signer.CreateKeyPair();
    File.WriteAllText(privatePath, signer.ExportKeys(false));
    if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(privatePath, UnixFileMode.UserRead | UnixFileMode.UserWrite);
}
var trialDays = args.Length > 1 ? int.Parse(args[1]) : 30;
var demoFixtures = args.Length > 2 && args[2] == "--repository-fixtures";
File.WriteAllText(Path.Combine(output, "publisher-key.txt"), signer.ExportKeys(true));
foreach (var kind in new[] { "perpetual", "trial", "expired", "no-feature", "restricted" }) {
    var license = new XmlLicense { Id = "native-demo-" + kind, Type = kind == "trial" ? "Trial" : "Demo" };
    license.Licensee = new Licensee { Name = "Example application developer" };
    if (kind == "trial") license.ExpireDate = demoFixtures ?
        new DateTime(2099, 1, 1, 0, 0, 0, DateTimeKind.Utc) : DateTime.UtcNow.AddDays(trialDays);
    if (kind == "expired") license.ExpireDate = new DateTime(2000,1,1,0,0,0,DateTimeKind.Utc);
    if (kind == "restricted") license.Restrictions.Add(new TrialRestriction { ExpireDays = 7 });
    if (kind != "no-feature") license.Features.Add(new Feature("Pro"));
    var builder = new XmlLicenseBuilder { SignatureProvider = signer };
    builder.AddOrUpdate(license); builder.Sign();
    File.WriteAllText(Path.Combine(output, kind + ".xml"), builder.ToXml());
}
Console.WriteLine("Wrote sample licenses and public key to " + output);
Console.WriteLine("Keep " + privatePath + " on your publisher machine. Do not distribute or commit it.");
