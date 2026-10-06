// Tiny bridge: types on Karabiner's virtual HID keyboard, which macOS (and
// OpenEmu) treat as real hardware. Must run as root (Karabiner's rule).
//
// stdin protocol, one line per change:
//   k <usage> <usage> ...   hold exactly these HID usages (empty = release all)
//   q                       release all and exit
// Prints READY once the virtual keyboard is available.
#include <atomic>
#include <chrono>
#include <iostream>
#include <sstream>
#include <thread>
#include <pqrs/karabiner/driverkit/virtual_hid_device_driver.hpp>
#include <pqrs/karabiner/driverkit/virtual_hid_device_service.hpp>

namespace vhid = pqrs::karabiner::driverkit;

int main() {
  pqrs::dispatcher::extra::initialize_shared_dispatcher();
  auto client = std::make_unique<vhid::virtual_hid_device_service::client>();
  std::atomic<bool> ready(false);

  client->connected.connect([&client] {
    vhid::virtual_hid_device_service::virtual_hid_keyboard_parameters parameters;
    parameters.set_country_code(pqrs::hid::country_code::us);
    client->async_virtual_hid_keyboard_initialize(parameters);
  });
  client->connect_failed.connect([](auto&& error_code) {
    std::cerr << "connect_failed " << error_code << " (is the Karabiner daemon running?)" << std::endl;
  });
  client->driver_version_mismatched.connect([](auto&& mismatched) {
    if (mismatched) {
      std::cerr << "DRIVER_VERSION_MISMATCH: reinstall the driver with setup_karabiner.command" << std::endl;
    }
  });
  client->virtual_hid_keyboard_ready.connect([&ready](auto&& r) {
    if (r && !ready.exchange(true)) {
      std::cout << "READY" << std::endl;
    }
  });
  client->async_start();

  std::string line;
  while (std::getline(std::cin, line)) {
    if (line == "q") {
      break;
    }
    std::istringstream ss(line);
    std::string cmd;
    ss >> cmd;
    if (cmd != "k") {
      continue;
    }
    vhid::virtual_hid_device_driver::hid_report::keyboard_input report;
    int usage;
    while (ss >> usage) {
      report.keys.insert(static_cast<uint16_t>(usage));
    }
    client->async_post_report(report);
  }

  vhid::virtual_hid_device_driver::hid_report::keyboard_input release;
  client->async_post_report(release);
  std::this_thread::sleep_for(std::chrono::milliseconds(200));
  client = nullptr;
  pqrs::dispatcher::extra::terminate_shared_dispatcher();
  return 0;
}
