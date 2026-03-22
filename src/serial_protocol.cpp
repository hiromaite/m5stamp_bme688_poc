#include "serial_protocol.h"

#include "app_config.h"
#include "bme688_controller.h"
#include "profile_state.h"

namespace {
bool commandOverflow = false;
char commandBuffer[app_config::kCommandBufferSize] = {};
size_t commandLength = 0;

void printArrayProfileLine(const char *key, const uint16_t *values) {
  Serial.printf("[profile] %s=", key);
  for (uint8_t i = 0; i < profile_state::length(); ++i) {
    if (i > 0) {
      Serial.print(",");
    }
    Serial.print(values[i]);
  }
  Serial.println();
}

void handleResetProfileCommand() {
  profile_state::resetToDefault();
  const char *errorCode = nullptr;
  if (!bme688_controller::syncActiveProfile(errorCode)) {
    serial_protocol::printStatusKeyValue("command_error", errorCode ? errorCode : "unknown_sync_error");
    return;
  }

  serial_protocol::printEventKeyValue("profile_reset", 1);
  serial_protocol::printCurrentProfileDetails();
}

bool handleSetProfileCommand(const String &command) {
  const int tempPos = command.indexOf("temp=");
  const int durPos = command.indexOf("dur=");
  const int basePos = command.indexOf("base_ms=");
  if (tempPos < 0 || durPos < 0 || basePos < 0) {
    serial_protocol::printStatusKeyValue("command_error", "missing_profile_fields");
    return false;
  }

  String tempValue = command.substring(tempPos + 5, durPos);
  String durValue = command.substring(durPos + 4, basePos);
  String baseValue = command.substring(basePos + 8);
  tempValue.trim();
  durValue.trim();
  baseValue.trim();

  String errorCode;
  bool errorIsValidation = false;
  if (!profile_state::applyFromCommandValues(tempValue, durValue, baseValue, errorCode, errorIsValidation)) {
    if (errorIsValidation) {
      serial_protocol::printStatusKeyValue("profile_validation", errorCode.c_str());
    } else {
      serial_protocol::printStatusKeyValue("command_error", errorCode.c_str());
    }
    return false;
  }

  const char *syncErrorCode = nullptr;
  if (!bme688_controller::syncActiveProfile(syncErrorCode)) {
    serial_protocol::printStatusKeyValue("command_error", syncErrorCode ? syncErrorCode : "unknown_sync_error");
    return false;
  }

  serial_protocol::printEventKeyValue("profile_updated", 1);
  serial_protocol::printCurrentProfileDetails();
  return true;
}

void handleCommand(const String &rawCommand) {
  String command = rawCommand;
  command.trim();
  if (command.isEmpty()) {
    return;
  }

  Serial.printf("[event] command_received=%s\n", command.c_str());

  if (command == "PING") {
    serial_protocol::printStatusKeyValue("pong", "true");
    return;
  }

  if (command == "GET_PROFILE") {
    serial_protocol::printCurrentProfileDetails();
    return;
  }

  if (command == "GET_CAPS") {
    serial_protocol::printCapabilities();
    return;
  }

  if (command == "RESET_PROFILE") {
    handleResetProfileCommand();
    return;
  }

  if (command.startsWith("SET_PROFILE ")) {
    serial_protocol::printStatusKeyValue("set_profile", handleSetProfileCommand(command) ? "ok" : "failed");
    return;
  }

  serial_protocol::printStatusKeyValue("command_error", "unknown_command");
}
}  // namespace

namespace serial_protocol {
void printBootBanner() {
  Serial.println();
  Serial.println("=== M5StampS3 + BME688 SensorAPI parallel-mode PoC boot ===");
  Serial.printf("Chip model: %s\n", ESP.getChipModel());
  Serial.printf("Chip revision: %u\n", ESP.getChipRevision());
  Serial.printf("CPU frequency: %u MHz\n", ESP.getCpuFreqMHz());
  Serial.printf("Flash size: %u bytes\n", ESP.getFlashChipSize());
  Serial.printf("SDK version: %s\n", ESP.getSdkVersion());
  Serial.println("Serial logging is active.");
  Serial.printf("I2C default pins: SDA=%u, SCL=%u\n", SDA, SCL);
}

void printCapabilityKeyValue(const char *key, const char *value) {
  Serial.printf("[caps] %s=%s\n", key, value);
}

void printCapabilityKeyValue(const char *key, int value) {
  Serial.printf("[caps] %s=%d\n", key, value);
}

void printStatusKeyValue(const char *key, const char *value) {
  Serial.printf("[status] %s=%s\n", key, value);
}

void printStatusKeyValue(const char *key, int value) {
  Serial.printf("[status] %s=%d\n", key, value);
}

void printEventKeyValue(const char *key, const char *value) {
  Serial.printf("[event] %s=%s\n", key, value);
}

void printEventKeyValue(const char *key, int value) {
  Serial.printf("[event] %s=%d\n", key, value);
}

void printCapabilities() {
  printCapabilityKeyValue("protocol_version", app_config::kProtocolVersion);
  printCapabilityKeyValue("firmware_version", app_config::kFirmwareVersion);
  printCapabilityKeyValue("supported_commands", app_config::kSupportedCommands);
  printCapabilityKeyValue("board_type", app_config::kBoardType);
  printCapabilityKeyValue("sensor_type", app_config::kSensorType);
  printCapabilityKeyValue("min_profile_len", app_config::kMinProfileLength);
  printCapabilityKeyValue("max_profile_len", app_config::kMaxProfileLength);
  printCapabilityKeyValue("default_profile_len", app_config::kMaxProfileLength);
  printCapabilityKeyValue("supports_runtime_profile", 1);
  printCapabilityKeyValue("supports_parallel_mode", 1);
}

void printCurrentProfileDetails() {
  Serial.printf("[profile] heater_profile_id=%s\n", profile_state::profileId());
  printArrayProfileLine("heater_profile_temp_c", profile_state::heaterTemps());
  printArrayProfileLine("heater_profile_duration_mult", profile_state::heaterDurations());
  Serial.printf("[profile] heater_profile_time_base_ms=%u\n", profile_state::timeBaseMs());
  Serial.printf("[profile] profile_len=%u\n", profile_state::length());
  Serial.printf("[profile] poll_interval_ms=%.2f\n", bme688_controller::pollIntervalUs() / 1000.0f);
}

void printProfileSummary() {
  Serial.printf("[profile] description=%s\n",
                profile_state::isRuntimeProfileActive() ? "runtime custom profile" : "Bosch standard VSC-oriented parallel-mode profile");
  Serial.printf("[profile] time_base_ms=%u\n", profile_state::timeBaseMs());
  Serial.printf("[profile] profile_len=%u\n", profile_state::length());
  Serial.printf("[profile] poll_interval_ms=%.2f\n", bme688_controller::pollIntervalUs() / 1000.0f);
  for (uint8_t i = 0; i < profile_state::length(); ++i) {
    Serial.printf("[profile] step_%u=temp:%u,duration_ms:%u\n",
                  i,
                  profile_state::heaterTemps()[i],
                  static_cast<unsigned>(profile_state::heaterDurations()[i] * profile_state::timeBaseMs()));
  }
}

void pollSerialCommands() {
  while (Serial.available() > 0) {
    const char ch = static_cast<char>(Serial.read());
    if (ch == '\r') {
      continue;
    }

    if (ch == '\n') {
      if (!commandOverflow && commandLength > 0) {
        commandBuffer[commandLength] = '\0';
        handleCommand(String(commandBuffer));
      } else if (commandOverflow) {
        printStatusKeyValue("command_error", "buffer_overflow");
      }
      commandLength = 0;
      commandOverflow = false;
      commandBuffer[0] = '\0';
      continue;
    }

    if (commandOverflow) {
      continue;
    }

    if (commandLength >= (app_config::kCommandBufferSize - 1)) {
      commandOverflow = true;
      continue;
    }

    commandBuffer[commandLength++] = ch;
  }
}

void waitWithCommandPolling(uint32_t totalDelayUs) {
  uint32_t remaining = totalDelayUs;
  while (remaining > 0) {
    const uint32_t chunk = remaining > app_config::kCommandFriendlyDelayChunkUs ? app_config::kCommandFriendlyDelayChunkUs : remaining;
    bme688_controller::shortDelayUs(chunk);
    remaining -= chunk;
    pollSerialCommands();
  }
}
}  // namespace serial_protocol
