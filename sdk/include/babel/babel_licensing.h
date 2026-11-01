/*
 * Babel Licensing — flat C ABI (extern "C").
 *
 * A stable, language-agnostic surface over the C++ licensing client, intended as
 * the foundation for a Rust `-sys` crate and bindings for C, C++, Go, Python, etc.
 * No C++ types cross this boundary; all strings are UTF-8, NUL-terminated.
 *
 * Phase-1 status: offline file licenses. XML licenses (RSA and ECDSA) parse and
 * verify against a trusted publisher key. Compact string licenses parse; string
 * signature verification and online activation are not yet wired (see the
 * Native-SDK Phase-1 doc).
 *
 * Ownership: babel_license_load() allocates; the caller frees with
 * babel_license_free(). String getters copy into a caller-provided buffer.
 * The caller must not free a handle concurrently with any operation, use it after
 * free, or free it twice. Verification changes its authentication state.
 * Maximum license input: 1 MiB UTF-8; XML depth: 64; XML nodes: 16384.
 */
#ifndef BABEL_LICENSING_H
#define BABEL_LICENSING_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ABI contract version. Bump on any breaking change to this header. */
#define BABEL_LICENSING_ABI_VERSION 2

typedef enum babel_status {
    BABEL_OK            = 0,  /* success */
    BABEL_ERR_ARG       = 1,  /* a NULL/invalid argument */
    BABEL_ERR_PARSE     = 2,  /* the license text could not be parsed */
    BABEL_ERR_SIGNATURE = 3,  /* the signature did not verify */
    BABEL_ERR_UNSUPPORTED = 4,/* operation/algorithm not supported yet */
    BABEL_ERR_NOT_FOUND = 5,  /* requested field is absent */
    BABEL_ERR_BUFFER    = 6,  /* output buffer too small (see required size) */
    BABEL_ERR_INTERNAL  = 7,  /* unexpected internal error */
    BABEL_ERR_MAINTENANCE_EXPIRED   = 8, /* maintenance does not cover the release day */
    BABEL_ERR_ASSEMBLY_NOT_LICENSED = 9, /* no assembly node matches the requested identity */
    BABEL_ERR_EXPIRED = 10 /* license expiration (not maintenance) has passed */
} babel_status;

/* Opaque handle to a parsed license. */
typedef struct babel_license babel_license;

/* Library version string, e.g. "1.0.0". Never NULL. */
const char* babel_version(void);

/* The ABI version this build implements (BABEL_LICENSING_ABI_VERSION). */
int babel_abi_version(void);

/*
 * Parse a license from text. Accepts an XML license or a compact string license;
 * the format is auto-detected. On success *out receives a handle to free later.
 * This does NOT verify the signature — call babel_license_verify for that.
 */
babel_status babel_license_load(const char* text, babel_license** out);

/*
 * Verify the license signature against a trusted publisher public key.
 *
 *   algo == "RSA"  : trusted_key is base64 of the X.509 SubjectPublicKeyInfo DER
 *                    (exactly what .NET RSASignature.ExportKeys(true) returns).
 *   algo == "ECDSA": trusted_key is the Base32 uncompressed EC point
 *                    (exactly what .NET ECDsaSignature.PublicKey returns).
 *   algo == NULL/"" : use the algorithm named in the license.
 * A nonempty trusted_key is mandatory for both algorithms. Embedded keys are
 * never trust anchors. Every failure clears the handle's authentication state.
 *
 * Returns BABEL_OK when the signature is valid, BABEL_ERR_SIGNATURE when not,
 * BABEL_ERR_UNSUPPORTED for a string license (signature verify not yet wired).
 */
babel_status babel_license_verify(const babel_license* lic,
                                  const char* algo,
                                  const char* trusted_key);

/*
 * Validate an authenticated license's runtime restrictions. BABEL_ERR_SIGNATURE
 * before successful verify, BABEL_ERR_EXPIRED for license expiration, and
 * BABEL_ERR_UNSUPPORTED for any restriction not implemented in Phase 1.
 * This checks license expiry against the clock; maintenance NEVER uses the clock.
 * Signature verification alone does not imply runtime validity.
 */
babel_status babel_license_validate(const babel_license* lic);

/* Diagnostic getters expose parsed, potentially unauthenticated data. */
/* Copy the license Id as UTF-8 into buf (NUL-terminated). */
babel_status babel_license_get_id(const babel_license* lic, char* buf, size_t buflen);

/* Copy the license Type (e.g. "Ultimate") as UTF-8 into buf. */
babel_status babel_license_get_type(const babel_license* lic, char* buf, size_t buflen);

/* Expiry as a Unix timestamp (UTC seconds), or -1 if the license has none. */
int64_t babel_license_get_expire_unix(const babel_license* lic);

/* Maintenance/support expiry as a Unix timestamp, or -1 if absent. */
int64_t babel_license_get_support_expire_unix(const babel_license* lic);

/* 1 only for an authenticated, runtime-valid license and unexpired feature. */
int babel_license_feature_enabled(const babel_license* lic, const char* feature);

/*
 * This machine's hardware key (fingerprint). salt may be NULL. Writes the
 * UTF-8 key into buf. Returns BABEL_ERR_BUFFER if buf is too small.
 */
babel_status babel_hardware_key(const char* salt, char* buf, size_t buflen);

/* ---- Maintenance / updates (offline release authentication) ---- */

/*
 * Authenticate a Babel release offline. version is the full four-part assembly
 * version (e.g. "12.1.3.0"), date is the release day as "yyyy-MM-dd", and
 * signature_b64 is the base64 Babel.Licensing.ReleaseSignature. The RSA/SHA-256
 * signature is verified against the pinned Babel publisher public key (a trust
 * anchor compiled into this library — NOT taken from the license or caller).
 * No network and no client-clock check are involved.
 *
 * Returns BABEL_OK if authentic, BABEL_ERR_SIGNATURE otherwise.
 */
babel_status babel_release_authenticate(const char* version,
                                        const char* date,
                                        const char* signature_b64);

/*
 * Decide whether this license licenses the given (already authenticated) release
 * under the maintenance model, without consulting the client clock. Requires
 * successful license verify; otherwise returns BABEL_ERR_SIGNATURE. This is an
 * update-eligibility check, not a replacement for babel_license_validate:
 *
 *   - an Assembly node naming the exact four-part version (name+token match) is a
 *     perpetual grant                                   -> BABEL_OK;
 *   - otherwise a name/public-key-token match whose maintenance window covers the
 *     release day (SupportExpireDate, else IssueDate+1y; inclusive, calendar days)
 *                                                        -> BABEL_OK;
 *   - a name/token match not covered                    -> BABEL_ERR_MAINTENANCE_EXPIRED;
 *   - no matching assembly node                          -> BABEL_ERR_ASSEMBLY_NOT_LICENSED.
 *
 * name/public_key_token identify the running product (public_key_token may be NULL);
 * version is its four-part version; release_date is "yyyy-MM-dd" (typically the day
 * authenticated by babel_release_authenticate).
 */
babel_status babel_license_check_maintenance(const babel_license* lic,
                                             const char* name,
                                             const char* version,
                                             const char* public_key_token,
                                             const char* release_date);

/* Release a handle from babel_license_load. Safe to call with NULL. */
void babel_license_free(babel_license* lic);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* BABEL_LICENSING_H */
