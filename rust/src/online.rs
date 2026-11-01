use super::{read_input, success};
use std::ffi::{CString, c_char, c_int, c_void};
use std::time::Duration;
unsafe extern "C" {
    fn babel_online_create(
        url: *const c_char,
        algo: *const c_char,
        key: *const c_char,
        machine: *const c_char,
        client: *const c_char,
        name: *const c_char,
        timeout: c_int,
        flags: u32,
        out: *mut *mut c_void,
    ) -> c_int;
    fn babel_online_activate(client: *mut c_void, user: *const c_char) -> c_int;
    fn babel_online_request_floating(client: *mut c_void, user: *const c_char) -> c_int;
    fn babel_online_validate_activation(client: *mut c_void) -> c_int;
    fn babel_online_heartbeat(client: *mut c_void) -> c_int;
    fn babel_online_check(client: *const c_void) -> c_int;
    fn babel_online_feature_enabled(client: *const c_void, feature: *const c_char) -> c_int;
    fn babel_online_heartbeat_after_ms(client: *const c_void) -> i64;
    fn babel_online_deactivate(client: *mut c_void) -> c_int;
    fn babel_online_release(client: *mut c_void) -> c_int;
    fn babel_online_free(client: *mut c_void);
    fn babel_hardware_key(salt: *const c_char, buf: *mut c_char, length: usize) -> c_int;
}
struct Session {
    raw: *mut c_void,
    activation: bool,
    cleaned: bool,
}
impl Session {
    fn cleanup(&self) -> c_int {
        unsafe {
            if self.activation {
                babel_online_deactivate(self.raw)
            } else {
                babel_online_release(self.raw)
            }
        }
    }
}
impl Drop for Session {
    fn drop(&mut self) {
        if !self.cleaned {
            let status = self.cleanup();
            if status != 0 && status != 1 {
                eprintln!("Cleanup failed (status {status}); retry with the service");
            }
        }
        unsafe { babel_online_free(self.raw) }
    }
}
fn setting(name: &str, default: &str) -> Result<CString, String> {
    let value = std::env::var(name).unwrap_or_else(|_| default.into());
    if value.is_empty() {
        return Err(format!("Set {name}"));
    }
    CString::new(value).map_err(|_| format!("{name} contains NUL"))
}
pub fn run(mode: &str) -> Result<(), String> {
    if mode != "activation" && mode != "floating" {
        return Err("Choose activation or floating".into());
    }
    let url = setting("BABEL_SERVICE_URL", "")?;
    let user = setting("BABEL_USER_KEY", "")?;
    let algo = setting("BABEL_ALGORITHM", "RSA")?;
    let client = setting("BABEL_CLIENT_ID", "native-example-rust")?;
    let key_path = std::env::var("BABEL_PUBLISHER_KEY_FILE")
        .unwrap_or_else(|_| "demo/publisher-key.txt".into());
    let key = read_input(&key_path, 16384)?;
    let machine = match std::env::var("BABEL_MACHINE_ID") {
        Ok(value) => CString::new(value).map_err(|e| e.to_string())?,
        Err(_) => {
            let mut buffer = [0 as c_char; 4096];
            unsafe {
                success(
                    babel_hardware_key(std::ptr::null(), buffer.as_mut_ptr(), buffer.len()),
                    "Machine identity",
                )?;
                std::ffi::CStr::from_ptr(buffer.as_ptr()).to_owned()
            }
        }
    };
    let flags = match std::env::var("BABEL_ALLOW_LOOPBACK_HTTP")
        .as_deref()
        .unwrap_or("0")
    {
        "0" => 0,
        "1" => 1,
        _ => return Err("BABEL_ALLOW_LOOPBACK_HTTP must be 0 or 1".into()),
    };
    unsafe {
        let mut raw = std::ptr::null_mut();
        success(
            babel_online_create(
                url.as_ptr(),
                algo.as_ptr(),
                key.as_ptr(),
                machine.as_ptr(),
                client.as_ptr(),
                c"Rust integration example".as_ptr(),
                15,
                flags,
                &mut raw,
            ),
            "Create online client",
        )?;
        let mut session = Session {
            raw,
            activation: mode == "activation",
            cleaned: false,
        };
        success(
            if session.activation {
                babel_online_activate(raw, user.as_ptr())
            } else {
                babel_online_request_floating(raw, user.as_ptr())
            },
            "Acquire grant",
        )?;
        success(babel_online_check(raw), "Check before protected work")?;
        if babel_online_feature_enabled(raw, c"Pro".as_ptr()) != 1 {
            return Err("Signed license does not enable Pro".into());
        }
        println!("{mode}: signed license valid; Pro enabled");
        if session.activation {
            success(
                babel_online_validate_activation(raw),
                "Validate activation with service",
            )?;
        } else {
            for _ in 0..2 {
                let delay = babel_online_heartbeat_after_ms(raw);
                if delay < 1 {
                    return Err("Floating lease is no longer active".into());
                }
                std::thread::sleep(Duration::from_millis(delay as u64));
                success(babel_online_heartbeat(raw), "Renew floating lease")?;
                success(babel_online_check(raw), "Check renewed lease")?;
                println!("floating: heartbeat renewed");
            }
        }
        success(session.cleanup(), "Release/deactivate")?;
        session.cleaned = true;
    }
    println!("{mode}: cleaned up; protected work is now disabled");
    Ok(())
}
