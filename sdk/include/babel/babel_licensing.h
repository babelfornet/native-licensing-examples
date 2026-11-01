/*
 * Babel Licensing — flat C ABI (extern "C").
 *
 * A stable, language-agnostic surface over the C++ licensing client, intended as
 * the foundation for a Rust `-sys` crate and bindings for C, C++, Go, Python, etc.
 * No C++ types cross this boundary; all strings are UTF-8, NUL-terminated.
 *
 * XML and compact licenses (RSA and ECDSA) parse and verify against a trusted
 * publisher key. Compact
 * signatures use the same pinned-key verification path. Online activation and
 * floating leases are available through the explicit session API below.
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

#ifndef BABEL_LICENSING_C_API
# if defined(_WIN32) && !defined(BABEL_LICENSING_STATIC)
#  if defined(BABEL_LICENSING_EXPORTS)
#   define BABEL_LICENSING_C_API __declspec(dllexport)
#  else
#   define BABEL_LICENSING_C_API __declspec(dllimport)
#  endif
# elif defined(__GNUC__)
#  define BABEL_LICENSING_C_API __attribute__((visibility("default")))
# else
#  define BABEL_LICENSING_C_API
# endif
#endif

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
    BABEL_ERR_EXPIRED = 10, /* license expiration (not maintenance) has passed */
    BABEL_ERR_NETWORK = 11, /* bounded HTTP transport failed */
    BABEL_ERR_AUTH = 12, /* service rejected credentials */
    BABEL_ERR_SERVICE = 13, /* non-success HTTP status */
    BABEL_ERR_DENIED = 14, /* server refused the activation/lease */
    BABEL_ERR_LEASE = 15, /* inactive, released, expired or lost floating lease */
    BABEL_ERR_MACHINE = 16 /* signed hardware restriction does not match */
} babel_status;

/* Opaque handle to a parsed license. */
typedef struct babel_license babel_license;

/* Library version string, e.g. "1.0.0". Never NULL. */
BABEL_LICENSING_C_API const char* babel_version(void);

/* The ABI version this build implements (BABEL_LICENSING_ABI_VERSION). */
BABEL_LICENSING_C_API int babel_abi_version(void);

/*
 * Parse a license from text. Accepts an XML license or a compact string license;
 * the format is auto-detected. On success *out receives a handle to free later.
 * This does NOT verify the signature — call babel_license_verify for that.
 */
BABEL_LICENSING_C_API babel_status babel_license_load(const char* text, babel_license** out);

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
 * Returns BABEL_OK when the signature is valid, BABEL_ERR_SIGNATURE when not.
 * Compact serials without an algorithm record require an explicit algo.
 */
BABEL_LICENSING_C_API babel_status babel_license_verify(const babel_license* lic,
                                  const char* algo,
                                  const char* trusted_key);

/*
 * Validate an authenticated license's runtime restrictions. BABEL_ERR_SIGNATURE
 * before successful verify, BABEL_ERR_EXPIRED for license expiration, and
 * BABEL_ERR_UNSUPPORTED for any restriction not implemented in Phase 1.
 * This checks license expiry against the clock; maintenance NEVER uses the clock.
 * Signature verification alone does not imply runtime validity.
 */
BABEL_LICENSING_C_API babel_status babel_license_validate(const babel_license* lic);

/* Diagnostic getters expose parsed, potentially unauthenticated data. */
/* Copy the license Id as UTF-8 into buf (NUL-terminated). */
BABEL_LICENSING_C_API babel_status babel_license_get_id(const babel_license* lic, char* buf, size_t buflen);

/* Copy the license Type (e.g. "Ultimate") as UTF-8 into buf. */
BABEL_LICENSING_C_API babel_status babel_license_get_type(const babel_license* lic, char* buf, size_t buflen);

/* Expiry as a Unix timestamp (UTC seconds), or -1 if the license has none. */
BABEL_LICENSING_C_API int64_t babel_license_get_expire_unix(const babel_license* lic);

/* Maintenance/support expiry as a Unix timestamp, or -1 if absent. */
BABEL_LICENSING_C_API int64_t babel_license_get_support_expire_unix(const babel_license* lic);

/* 1 only for an authenticated, runtime-valid license and unexpired feature. */
BABEL_LICENSING_C_API int babel_license_feature_enabled(const babel_license* lic, const char* feature);

/*
 * This machine's hardware key (fingerprint). salt may be NULL. Writes the
 * UTF-8 key into buf. Returns BABEL_ERR_BUFFER if buf is too small.
 */
BABEL_LICENSING_C_API babel_status babel_hardware_key(const char* salt, char* buf, size_t buflen);

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
BABEL_LICENSING_C_API babel_status babel_release_authenticate(const char* version,
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
BABEL_LICENSING_C_API babel_status babel_license_check_maintenance(const babel_license* lic,
                                             const char* name,
                                             const char* version,
                                             const char* public_key_token,
                                             const char* release_date);

/* Authenticate and check maintenance against the SAME Babel release metadata.
 * Prefer this combined operation for Babel itself. It pins product/token and
 * fails closed before evaluating even an exact purchased version. The caller
 * must supply the metadata of the actual executing binary, protected from edits.
 * This Babel publisher certificate does not authenticate third-party products. */
BABEL_LICENSING_C_API babel_status babel_license_check_babel_release(const babel_license* lic,
                                             const char* version,
                                             const char* date,
                                             const char* signature_b64);

/* ---- Online activation and floating licenses (synchronous, explicit lifecycle) ---- */
typedef struct babel_online_client babel_online_client;
#define BABEL_ONLINE_ALLOW_LOOPBACK_HTTP 1u /* local testing only, never remote HTTP */
/* service_url is the service root, e.g. https://licensing.example.com/ .
 * HTTPS certificate/hostname validation is mandatory. No redirects are followed.
 * Requests use v1/auth/login and v1/license/{activate,validate,deactivate,request,
 * heartbeat,release}, exactly as the .NET REST client. The publisher public key
 * and algorithm MUST come from the application, never from the service response.
 * machine_id and client_id must be stable nonempty application identities;
 * use babel_hardware_key for a platform fingerprint. client_name may be NULL.
 * All strings are copied. timeout_seconds is 1..300 for EACH HTTP request.
 * flags must be 0 in production. *out is NULL on failure.
 */
BABEL_LICENSING_C_API babel_status babel_online_create(const char* service_url, const char* algo,
    const char* trusted_key, const char* machine_id, const char* client_id,
    const char* client_name, int timeout_seconds, uint32_t flags,
    babel_online_client** out);
/* The user key is obtained from your publisher's licensing service. Responses
 * must contain a signed license, not just success=true. An activation must carry
 * a signed Hardware restriction matching machine_id. Unsupported restrictions
 * and unsupported ECDSA curves fail closed. One active grant per client handle.
 */
BABEL_LICENSING_C_API babel_status babel_online_activate(babel_online_client*, const char* user_key);
BABEL_LICENSING_C_API babel_status babel_online_validate_activation(babel_online_client*);
BABEL_LICENSING_C_API babel_status babel_online_deactivate(babel_online_client*);
BABEL_LICENSING_C_API babel_status babel_online_request_floating(babel_online_client*, const char* user_key);
/* Call heartbeat before the interval expires; no background thread or offline
 * grace period is implied. A failed heartbeat immediately invalidates the grant.
 */
BABEL_LICENSING_C_API babel_status babel_online_heartbeat(babel_online_client*);
/* Invalidates local use before sending release/deactivate, even if HTTP fails.
 * Retry the same cleanup operation on failure; free does not perform network IO.
 */
BABEL_LICENSING_C_API babel_status babel_online_release(babel_online_client*);
/* Check before protected work. Enforces signature, hardware, license expiration
 * and floating token deadline using both wall and monotonic clocks.
 */
BABEL_LICENSING_C_API babel_status babel_online_check(const babel_online_client*);
BABEL_LICENSING_C_API int babel_online_feature_enabled(const babel_online_client*, const char* feature);
/* Recommended heartbeat delay (half the server interval, >=1 ms), or -1 if not
 * currently holding a valid floating lease. Does not renew the lease itself.
 */
BABEL_LICENSING_C_API int64_t babel_online_heartbeat_after_ms(const babel_online_client*);
/* Serializes operations per handle. Caller must NOT free concurrently, use after
 * free or free twice. Safe with NULL; explicitly release/deactivate first.
 */
BABEL_LICENSING_C_API void babel_online_free(babel_online_client*);

/* Release a handle from babel_license_load. Safe to call with NULL. */
BABEL_LICENSING_C_API void babel_license_free(babel_license* lic);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* BABEL_LICENSING_H */
