#pragma once

#include <Arduino.h>

namespace app_config {
constexpr char kFirmwareVersion[] = "0.2.3-dev";
constexpr char kProtocolVersion[] = "1.1";
constexpr char kSupportedCommands[] = "PING,GET_PROFILE,SET_PROFILE,RESET_PROFILE,GET_CAPS";
constexpr char kBoardType[] = "M5StampS3";
constexpr char kSensorType[] = "BME688";
constexpr unsigned long kSerialWaitTimeoutMs = 5000;
constexpr uint8_t kBme68xPrimaryAddress = 0x76;
constexpr uint8_t kBme68xSecondaryAddress = 0x77;
constexpr int8_t kAmbientTemperatureC = 25;
constexpr uint8_t kMaxProfileLength = 10;
constexpr uint8_t kMinProfileLength = 1;
constexpr uint16_t kDefaultProfileTimeBaseMs = 140;
constexpr uint8_t kMaxFieldsPerRead = 3;
constexpr uint8_t kValidDataMask = 0xB0;
constexpr uint32_t kCommandFriendlyDelayChunkUs = 5000;
constexpr size_t kCommandBufferSize = 256;

constexpr uint16_t kDefaultHeaterTempProfile[kMaxProfileLength] = {320, 100, 100, 100, 200, 200, 200, 320, 320, 320};
constexpr uint16_t kDefaultHeaterDurationMultipliers[kMaxProfileLength] = {5, 2, 10, 30, 5, 5, 5, 5, 5, 5};
}  // namespace app_config
