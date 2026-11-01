// Verify a publisher-signed XML license through the Babel native C ABI.
package main

/*
#cgo CFLAGS: -I${SRCDIR}/../sdk/include
#cgo LDFLAGS: -L${SRCDIR}/../.sdk/lib -lBabelLicensingNative -Wl,-rpath,${SRCDIR}/../.sdk/lib
#include <stdlib.h>
#include <babel/babel_licensing.h>
*/
import "C"
import (
	"bytes"
	"fmt"
	"io"
	"os"
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
