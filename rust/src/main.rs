// Verify a publisher-signed XML license through the Babel native C ABI.
use std::ffi::{c_char, c_int, c_void, CString};
use std::io::Read;
unsafe extern "C" {
    fn babel_abi_version() -> c_int;
    fn babel_license_load(text: *const c_char, out: *mut *mut c_void) -> c_int;
    fn babel_license_verify(
        lic: *const c_void,
        algorithm: *const c_char,
        key: *const c_char,
    ) -> c_int;
    fn babel_license_validate(lic: *const c_void) -> c_int;
    fn babel_license_feature_enabled(lic: *const c_void, feature: *const c_char) -> c_int;
    fn babel_license_free(lic: *mut c_void);
}
struct Handle(*mut c_void);
impl Drop for Handle {
    fn drop(&mut self) {
        unsafe { babel_license_free(self.0) }
    }
}
fn read_input(path: &str, maximum: u64) -> Result<CString, String> {
    let file = std::fs::File::open(path).map_err(|e| e.to_string())?;
    let mut data = Vec::new();
    file.take(maximum + 1)
        .read_to_end(&mut data)
        .map_err(|e| e.to_string())?;
    if data.len() as u64 > maximum {
        return Err("Input exceeds its size limit".into());
    }
    CString::new(data).map_err(|_| "Input contains NUL".into())
}
fn success(status: c_int, operation: &str) -> Result<(), String> {
    if status == 0 {
        Ok(())
    } else {
        Err(format!("{operation} failed (status {status})"))
    }
}
fn run() -> Result<(), String> {
    let given: Vec<String> = std::env::args().skip(1).collect();
    if given.len() > 4 {
        return Err(
            "Usage: native-example [license.xml [publisher-key.txt [RSA|ECDSA [feature]]]]".into(),
        );
    }
    let mut args = vec![
        "demo/perpetual.xml".to_string(),
        "demo/publisher-key.txt".into(),
        "RSA".into(),
        "Pro".into(),
    ];
    for (i, arg) in given.into_iter().enumerate() {
        args[i] = arg;
    }
    let xml = read_input(&args[0], 1024 * 1024)?;
    let key = read_input(&args[1], 16384)?;
    let algorithm = CString::new(args[2].clone()).map_err(|e| e.to_string())?;
    let feature = CString::new(args[3].clone()).map_err(|e| e.to_string())?;
    unsafe {
        if babel_abi_version() != 2 {
            return Err("This example requires native ABI v2".into());
        }
        let mut raw = std::ptr::null_mut();
        success(
            babel_license_load(xml.as_ptr(), &mut raw),
            "License parsing",
        )?;
        let handle = Handle(raw);
        success(
            babel_license_verify(handle.0, algorithm.as_ptr(), key.as_ptr()),
            "Publisher signature verification",
        )?;
        success(
            babel_license_validate(handle.0),
            "Runtime license validation (10=expired, 4=unsupported restriction)",
        )?;
        if babel_license_feature_enabled(handle.0, feature.as_ptr()) != 1 {
            return Err("Requested feature is absent or expired".into());
        }
    }
    println!("License verified. Feature {} enabled.", args[3]);
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
