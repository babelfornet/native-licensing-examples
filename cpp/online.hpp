#pragma once
#include <chrono>
#include <cstdlib>
#include <thread>

static std::string setting(const char* name, const char* fallback = nullptr) {
    const char* value = std::getenv(name);
    if (!value || !*value) value = fallback;
    if (!value || !*value) throw std::runtime_error(std::string("Set ") + name);
    return value;
}
static int runOnline(const std::string& mode) {
    if (mode != "activation" && mode != "floating") throw std::runtime_error("Choose activation or floating");
    const bool activation = mode == "activation";
    const auto url = setting("BABEL_SERVICE_URL"), user = setting("BABEL_USER_KEY");
    const auto algo = setting("BABEL_ALGORITHM","RSA"), client = setting("BABEL_CLIENT_ID","native-example-cpp");
    const auto keyPath = setting("BABEL_PUBLISHER_KEY_FILE","demo/publisher-key.txt");
    auto key = readFile(keyPath.c_str(),16384);
    char fingerprint[4096];
    success(babel_hardware_key(nullptr,fingerprint,sizeof(fingerprint)),"Machine identity");
    const auto machine = setting("BABEL_MACHINE_ID",fingerprint);
    const auto flags = setting("BABEL_ALLOW_LOOPBACK_HTTP","0");
    if (flags != "0" && flags != "1") throw std::runtime_error("BABEL_ALLOW_LOOPBACK_HTTP must be 0 or 1");
    babel_online_client* raw = nullptr;
    success(babel_online_create(url.c_str(),algo.c_str(),key.c_str(),machine.c_str(),client.c_str(),
        "C++ integration example",15,flags == "1" ? BABEL_ONLINE_ALLOW_LOOPBACK_HTTP : 0,&raw),"Create online client");
    std::unique_ptr<babel_online_client, decltype(&babel_online_free)> handle(raw,babel_online_free);
    auto cleanup = activation ? babel_online_deactivate : babel_online_release;
    try {
        success(activation ? babel_online_activate(raw,user.c_str()) : babel_online_request_floating(raw,user.c_str()),"Acquire grant");
        success(babel_online_check(raw),"Check before protected work");
        if (babel_online_feature_enabled(raw,"Pro") != 1) throw std::runtime_error("Signed license does not enable Pro");
        std::cout << mode << ": signed license valid; Pro enabled\n";
        if (activation) success(babel_online_validate_activation(raw),"Validate activation with service");
        else for (int count=0; count<2; ++count) {
            const auto delay = babel_online_heartbeat_after_ms(raw);
            if (delay < 1) throw std::runtime_error("Floating lease is no longer active");
            std::this_thread::sleep_for(std::chrono::milliseconds(delay));
            success(babel_online_heartbeat(raw),"Renew floating lease");
            success(babel_online_check(raw),"Check renewed lease");
            std::cout << "floating: heartbeat renewed\n";
        }
        success(cleanup(raw),"Release/deactivate");
    } catch (...) {
        const auto status = cleanup(raw);
        if (status != BABEL_OK && status != BABEL_ERR_ARG) std::cerr << "Cleanup failed (status " << status << "); retry with the service\n";
        throw;
    }
    std::cout << mode << ": cleaned up; protected work is now disabled\n";
    return 0;
}
