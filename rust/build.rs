fn main() {
    let root = std::path::PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let lib = std::env::var_os("BABEL_NATIVE_SDK_LIB_DIR")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| root.parent().unwrap().join(".sdk/lib"));
    println!("cargo:rerun-if-env-changed=BABEL_NATIVE_SDK_LIB_DIR");
    println!("cargo:rustc-link-search=native={}", lib.display());
    println!("cargo:rustc-link-lib=dylib=BabelLicensingNative");
    if std::env::var("CARGO_CFG_TARGET_OS").unwrap() != "windows" {
        println!("cargo:rustc-link-arg=-Wl,-rpath,{}", lib.display());
    }
    println!("cargo:rerun-if-changed=build.rs");
}
