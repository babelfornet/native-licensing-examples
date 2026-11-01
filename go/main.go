// Verify a publisher-signed XML license through the Babel native C ABI.
package main

/*
#cgo CFLAGS: -I${SRCDIR}/../sdk/include
#cgo darwin LDFLAGS: -L${SRCDIR}/../.sdk/lib -lBabelLicensingNative -Wl,-rpath,${SRCDIR}/../.sdk/lib
#cgo linux LDFLAGS: -L${SRCDIR}/../.sdk/lib -lBabelLicensingNative -Wl,-rpath,${SRCDIR}/../.sdk/lib
#cgo windows LDFLAGS: -L${SRCDIR}/../.sdk/lib -L${SRCDIR}/../.sdk/bin -lBabelLicensingNative
#include <stdlib.h>
#include <babel/babel_licensing.h>
*/
import "C"
import (
	"bytes"
	"fmt"
	"io"
	"os"
	"strings"
	"time"
	"unsafe"
)

func readInput(path string, maximum int64) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	data, err := io.ReadAll(io.LimitReader(f, maximum+1))
	if err != nil {
		return "", err
	}
	if int64(len(data)) > maximum || bytes.IndexByte(data, 0) >= 0 {
		return "", fmt.Errorf("invalid or oversized input: %s", path)
	}
	return string(data), nil
}
func run() error {
	if len(os.Args) == 3 && os.Args[1] == "--online" {
		return runOnline(os.Args[2])
	}
	if len(os.Args) > 5 {
		return fmt.Errorf("usage: native-example [license.xml [publisher-key.txt [RSA|ECDSA [feature]]]]")
	}
	args := []string{"demo/perpetual.xml", "demo/publisher-key.txt", "RSA", "Pro"}
	copy(args, os.Args[1:])
	text, err := readInput(args[0], 1024*1024)
	if err != nil {
		return err
	}
	key, err := readInput(args[1], 16384)
	if err != nil {
		return err
	}
	xml := C.CString(text)
	defer C.free(unsafe.Pointer(xml))
	trusted := C.CString(key)
	defer C.free(unsafe.Pointer(trusted))
	algorithm := C.CString(args[2])
	defer C.free(unsafe.Pointer(algorithm))
	feature := C.CString(args[3])
	defer C.free(unsafe.Pointer(feature))
	if C.babel_abi_version() != 2 {
		return fmt.Errorf("this example requires native ABI v2")
	}
	var handle *C.babel_license
	if status := C.babel_license_load(xml, &handle); status != C.BABEL_OK {
		return fmt.Errorf("license parsing failed (status %d)", status)
	}
	defer C.babel_license_free(handle)
	if status := C.babel_license_verify(handle, algorithm, trusted); status != C.BABEL_OK {
		return fmt.Errorf("publisher signature verification failed (status %d)", status)
	}
	if status := C.babel_license_validate(handle); status != C.BABEL_OK {
		return fmt.Errorf("runtime license validation failed (status %d; 10=expired, 4=unsupported restriction)", status)
	}
	if C.babel_license_feature_enabled(handle, feature) != 1 {
		return fmt.Errorf("feature %s is absent or expired", args[3])
	}
	fmt.Printf("License verified. Feature %s enabled.\n", args[3])
	return nil
}
func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

// runOnline keeps the session inside the native SDK; no token or raw license
// handle can accidentally authorize work after a lease expires or is released.
func runOnline(mode string) (err error) {
	if mode != "activation" && mode != "floating" {
		return fmt.Errorf("choose activation or floating")
	}
	activation := mode == "activation"
	settings := map[string]string{}
	for name, fallback := range map[string]string{
		"BABEL_SERVICE_URL": "", "BABEL_USER_KEY": "", "BABEL_ALGORITHM": "RSA",
		"BABEL_PUBLISHER_KEY_FILE": "demo/publisher-key.txt", "BABEL_CLIENT_ID": "native-example-go",
		"BABEL_ALLOW_LOOPBACK_HTTP": "0",
	} {
		value := os.Getenv(name)
		if value == "" {
			value = fallback
		}
		if value == "" || strings.IndexByte(value, 0) >= 0 {
			return fmt.Errorf("set %s", name)
		}
		settings[name] = value
	}
	key, err := readInput(settings["BABEL_PUBLISHER_KEY_FILE"], 16384)
	if err != nil {
		return err
	}
	machine := os.Getenv("BABEL_MACHINE_ID")
	if machine == "" {
		var fingerprint [4096]C.char
		if status := C.babel_hardware_key(nil, &fingerprint[0], C.size_t(len(fingerprint))); status != C.BABEL_OK {
			return fmt.Errorf("machine identity failed (status %d)", status)
		}
		machine = C.GoString(&fingerprint[0])
	}
	if strings.IndexByte(machine, 0) >= 0 {
		return fmt.Errorf("invalid machine identity")
	}
	var owned []*C.char
	str := func(value string) *C.char { p := C.CString(value); owned = append(owned, p); return p }
	defer func() {
		for _, p := range owned {
			C.free(unsafe.Pointer(p))
		}
	}()
	flags := C.uint32_t(0)
	switch settings["BABEL_ALLOW_LOOPBACK_HTTP"] {
	case "1":
		flags = C.BABEL_ONLINE_ALLOW_LOOPBACK_HTTP
	case "0":
	default:
		return fmt.Errorf("BABEL_ALLOW_LOOPBACK_HTTP must be 0 or 1")
	}
	success := func(status C.babel_status, operation string) error {
		if status != C.BABEL_OK {
			return fmt.Errorf("%s failed (status %d)", operation, status)
		}
		return nil
	}
	var client *C.babel_online_client
	if err = success(C.babel_online_create(str(settings["BABEL_SERVICE_URL"]), str(settings["BABEL_ALGORITHM"]),
		str(key), str(machine), str(settings["BABEL_CLIENT_ID"]), str("Go integration example"), 15, flags, &client), "Create online client"); err != nil {
		return err
	}
	defer C.babel_online_free(client)
	cleanup := func() C.babel_status {
		if activation {
			return C.babel_online_deactivate(client)
		}
		return C.babel_online_release(client)
	}
	cleaned := false
	defer func() {
		if !cleaned {
			status := cleanup()
			if status != C.BABEL_OK && status != C.BABEL_ERR_ARG {
				fmt.Fprintf(os.Stderr, "Cleanup failed (status %d); retry with the service\n", status)
			}
		}
	}()
	user := str(settings["BABEL_USER_KEY"])
	var status C.babel_status
	if activation {
		status = C.babel_online_activate(client, user)
	} else {
		status = C.babel_online_request_floating(client, user)
	}
	if err = success(status, "Acquire "+mode); err != nil {
		return err
	}
	if err = success(C.babel_online_check(client), "Check before protected work"); err != nil {
		return err
	}
	if C.babel_online_feature_enabled(client, str("Pro")) != 1 {
		return fmt.Errorf("signed license does not enable Pro")
	}
	fmt.Printf("%s: signed license valid; Pro enabled\n", mode)
	if activation {
		if err = success(C.babel_online_validate_activation(client), "Validate activation with service"); err != nil {
			return err
		}
	} else {
		for count := 0; count < 2; count++ {
			delay := C.babel_online_heartbeat_after_ms(client)
			if delay < 1 {
				return fmt.Errorf("floating lease is no longer active")
			}
			time.Sleep(time.Duration(delay) * time.Millisecond)
			if err = success(C.babel_online_heartbeat(client), "Renew floating lease"); err != nil {
				return err
			}
			if err = success(C.babel_online_check(client), "Check renewed lease"); err != nil {
				return err
			}
			fmt.Println("floating: heartbeat renewed")
		}
	}
	if err = success(cleanup(), "Release/deactivate"); err != nil {
		return err
	}
	cleaned = true
	fmt.Println(mode + ": cleaned up; protected work is now disabled")
	return nil
}
