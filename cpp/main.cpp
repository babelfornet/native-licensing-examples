#include <babel/babel_licensing.h>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

static std::string readFile(const char* path, size_t max) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) throw std::runtime_error(std::string("Cannot read ") + path);
    const auto size = stream.tellg();
    if (size < 0 || static_cast<size_t>(size) > max) throw std::runtime_error("Input exceeds its size limit");
    std::string text(static_cast<size_t>(size), '\0');
    stream.seekg(0);
    if (!stream.read(text.data(), static_cast<std::streamsize>(text.size())) || text.find('\0') != text.npos)
        throw std::runtime_error("Invalid input file");
    return text;
}
static void success(babel_status status, const char* operation) {
    if (status != BABEL_OK)
        throw std::runtime_error(std::string(operation) + " failed (status " + std::to_string(status) + ")");
}
int main(int argc, char** argv) {
    try {
        if (argc > 5) throw std::runtime_error("Usage: native-example [license.xml [publisher-key.txt [RSA|ECDSA [feature]]]]");
        if (babel_abi_version() != 2) throw std::runtime_error("This example requires native ABI v2");
        auto text = readFile(argc > 1 ? argv[1] : "demo/perpetual.xml", 1024 * 1024);
        auto key = readFile(argc > 2 ? argv[2] : "demo/publisher-key.txt", 16384);
        babel_license* raw = nullptr;
        success(babel_license_load(text.c_str(), &raw), "License parsing");
        std::unique_ptr<babel_license, decltype(&babel_license_free)> handle(raw, babel_license_free);
        success(babel_license_verify(handle.get(), argc > 3 ? argv[3] : "RSA", key.c_str()), "Publisher signature verification");
        success(babel_license_validate(handle.get()), "Runtime license validation (10=expired, 4=unsupported restriction)");
        const char* feature = argc > 4 ? argv[4] : "Pro";
        if (!babel_license_feature_enabled(handle.get(), feature)) throw std::runtime_error("Requested feature is absent or expired");
        std::cout << "License verified. Feature " << feature << " enabled.\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
