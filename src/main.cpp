#include <Arduino.h>
#include <Wire.h>

extern "C" {
#include <bme68x.h>
}

namespace {
constexpr unsigned long kSerialWaitTimeoutMs = 5000;
constexpr uint8_t kBme68xPrimaryAddress = BME68X_I2C_ADDR_LOW;
constexpr uint8_t kBme68xSecondaryAddress = BME68X_I2C_ADDR_HIGH;
constexpr int8_t kAmbientTemperatureC = 25;
constexpr uint8_t kProfileLength = 10;
constexpr uint16_t kDefaultProfileTimeBaseMs = 140;
constexpr uint8_t kMaxFieldsPerRead = 3;
constexpr uint8_t kValidDataMask = 0xB0;
constexpr uint32_t kCommandFriendlyDelayChunkUs = 5000;
constexpr size_t kCommandBufferSize = 256;

const uint16_t kDefaultHeaterTempProfile[kProfileLength] = {320, 100, 100, 100, 200, 200, 200, 320, 320, 320};
const uint16_t kDefaultHeaterDurationMultipliers[kProfileLength] = {5, 2, 10, 30, 5, 5, 5, 5, 5, 5};

struct bme68x_dev bme = {};
struct bme68x_conf sensorConf = {};
struct bme68x_heatr_conf heaterConf = {};

uint16_t runtimeHeaterTempProfile[kProfileLength] = {};
uint16_t runtimeHeaterDurationMultipliers[kProfileLength] = {};
uint16_t profileTimeBaseMs = kDefaultProfileTimeBaseMs;

unsigned long bootCount = 0;
bool sensorReady = false;
bool headerPrinted = false;
bool frameSynced = false;
bool seenAnyField = false;
bool runtimeProfileActive = false;
bool commandOverflow = false;
uint8_t sensorAddress = 0;
int8_t lastGasIndex = -1;
uint8_t frameStepCount = 0;
uint32_t profilePollIntervalUs = 0;
uint32_t batchCounter = 0;
uint32_t frameCounter = 0;
char commandBuffer[kCommandBufferSize] = {};
size_t commandLength = 0;
}

int8_t i2cRead(uint8_t reg_addr, uint8_t *reg_data, uint32_t length, void *intf_ptr) {
  const uint8_t address = *static_cast<uint8_t *>(intf_ptr);

  Wire.beginTransmission(address);
  Wire.write(reg_addr);
  if (Wire.endTransmission(false) != 0) {
    return BME68X_E_COM_FAIL;
  }

  const uint32_t bytesRead = Wire.requestFrom(static_cast<int>(address), static_cast<int>(length), static_cast<int>(true));
  if (bytesRead != length) {
    return BME68X_E_COM_FAIL;
  }

  for (uint32_t i = 0; i < length; ++i) {
    reg_data[i] = static_cast<uint8_t>(Wire.read());
  }

  return BME68X_OK;
}

int8_t i2cWrite(uint8_t reg_addr, const uint8_t *reg_data, uint32_t length, void *intf_ptr) {
  const uint8_t address = *static_cast<uint8_t *>(intf_ptr);

  Wire.beginTransmission(address);
  Wire.write(reg_addr);
  for (uint32_t i = 0; i < length; ++i) {
    Wire.write(reg_data[i]);
  }

  if (Wire.endTransmission() != 0) {
    return BME68X_E_COM_FAIL;
  }

  return BME68X_OK;
}

void shortDelayUs(uint32_t period) {
  if (period >= 1000) {
    delay(period / 1000);
    period %= 1000;
  }

  if (period > 0) {
    delayMicroseconds(period);
  }
}

void delayUs(uint32_t period, void *intf_ptr) {
  (void)intf_ptr;
  shortDelayUs(period);
}

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

bool i2cDeviceExists(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

void scanI2CBus() {
  Serial.println("[i2c] scanning bus...");

  uint8_t deviceCount = 0;
  for (uint8_t address = 1; address < 127; ++address) {
    Wire.beginTransmission(address);
    const uint8_t error = Wire.endTransmission();
    if (error == 0) {
      ++deviceCount;
      Serial.printf("[i2c] device found at 0x%02X\n", address);
    } else if (error == 4) {
      Serial.printf("[i2c] unknown error at 0x%02X\n", address);
    }
  }

  if (deviceCount == 0) {
    Serial.println("[i2c] no devices found");
  } else {
    Serial.printf("[i2c] scan complete, %u device(s) found\n", deviceCount);
  }
}

void printApiResult(const char *label, int8_t result) {
  if (result == BME68X_OK) {
    return;
  }

  Serial.printf("[%s] SensorAPI returned %d\n", label, result);
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

void printArrayProfileLine(const char *key, const uint16_t *values) {
  Serial.printf("[profile] %s=", key);
  for (uint8_t i = 0; i < kProfileLength; ++i) {
    if (i > 0) {
      Serial.print(",");
    }
    Serial.print(values[i]);
  }
  Serial.println();
}

void copyDefaultProfile() {
  for (uint8_t i = 0; i < kProfileLength; ++i) {
    runtimeHeaterTempProfile[i] = kDefaultHeaterTempProfile[i];
    runtimeHeaterDurationMultipliers[i] = kDefaultHeaterDurationMultipliers[i];
  }
  profileTimeBaseMs = kDefaultProfileTimeBaseMs;
  runtimeProfileActive = false;
}

const char *profileId() {
  return runtimeProfileActive ? "runtime_custom" : "default_vsc_10step";
}

void printCurrentProfileDetails() {
  Serial.printf("[profile] heater_profile_id=%s\n", profileId());
  printArrayProfileLine("heater_profile_temp_c", runtimeHeaterTempProfile);
  printArrayProfileLine("heater_profile_duration_mult", runtimeHeaterDurationMultipliers);
  Serial.printf("[profile] heater_profile_time_base_ms=%u\n", profileTimeBaseMs);
  Serial.printf("[profile] profile_len=%u\n", kProfileLength);
  Serial.printf("[profile] poll_interval_ms=%.2f\n", profilePollIntervalUs / 1000.0f);
}

void printProfileSummary() {
  Serial.printf("[profile] description=%s\n", runtimeProfileActive ? "runtime custom profile" : "Bosch standard VSC-oriented parallel-mode profile");
  Serial.printf("[profile] time_base_ms=%u\n", profileTimeBaseMs);
  Serial.printf("[profile] profile_len=%u\n", kProfileLength);
  Serial.printf("[profile] poll_interval_ms=%.2f\n", profilePollIntervalUs / 1000.0f);
  for (uint8_t i = 0; i < kProfileLength; ++i) {
    Serial.printf("[profile] step_%u=temp:%u,duration_ms:%u\n",
                  i,
                  runtimeHeaterTempProfile[i],
                  static_cast<unsigned>(runtimeHeaterDurationMultipliers[i] * profileTimeBaseMs));
  }
}

void printCsvHeader() {
  if (headerPrinted) {
    return;
  }

  Serial.println("[csv] frame_id,batch_id,frame_step,host_ms,field_index,gas_index,meas_index,temp_c,humidity_pct,pressure_hpa,gas_kohms,status_hex,gas_valid,heat_stable");
  headerPrinted = true;
}

bool applyCurrentProfile() {
  heaterConf.enable = BME68X_ENABLE;
  heaterConf.heatr_temp = 0;
  heaterConf.heatr_dur = 0;
  heaterConf.heatr_temp_prof = runtimeHeaterTempProfile;
  heaterConf.heatr_dur_prof = runtimeHeaterDurationMultipliers;
  heaterConf.profile_len = kProfileLength;

  const uint32_t measurementDurationUs = bme68x_get_meas_dur(BME68X_PARALLEL_MODE, &sensorConf, &bme);
  const uint32_t measurementDurationMs = measurementDurationUs / 1000;
  if (profileTimeBaseMs <= measurementDurationMs) {
    Serial.printf("[status] apply_profile_error=time_base_too_small:%u\n", profileTimeBaseMs);
    return false;
  }

  heaterConf.shared_heatr_dur = static_cast<uint16_t>(profileTimeBaseMs - measurementDurationMs);

  const int8_t heaterResult = bme68x_set_heatr_conf(BME68X_PARALLEL_MODE, &heaterConf, &bme);
  printApiResult("bme68x_set_heatr_conf", heaterResult);
  if (heaterResult != BME68X_OK) {
    return false;
  }

  profilePollIntervalUs = measurementDurationUs + (static_cast<uint32_t>(heaterConf.shared_heatr_dur) * 1000);
  return true;
}

bool configureBme688() {
  sensorConf.filter = BME68X_FILTER_OFF;
  sensorConf.odr = BME68X_ODR_NONE;
  sensorConf.os_hum = BME68X_OS_1X;
  sensorConf.os_pres = BME68X_OS_16X;
  sensorConf.os_temp = BME68X_OS_2X;

  const int8_t confResult = bme68x_set_conf(&sensorConf, &bme);
  printApiResult("bme68x_set_conf", confResult);
  if (confResult != BME68X_OK) {
    return false;
  }

  return applyCurrentProfile();
}

bool restartParallelMode() {
  const int8_t modeResult = bme68x_set_op_mode(BME68X_PARALLEL_MODE, &bme);
  printApiResult("bme68x_set_op_mode", modeResult);
  return modeResult == BME68X_OK;
}

bool initializeBme688() {
  if (i2cDeviceExists(kBme68xPrimaryAddress)) {
    sensorAddress = kBme68xPrimaryAddress;
  } else if (i2cDeviceExists(kBme68xSecondaryAddress)) {
    sensorAddress = kBme68xSecondaryAddress;
  } else {
    Serial.println("[bme688] not detected at 0x76 or 0x77");
    return false;
  }

  Serial.printf("[bme688] attempting SensorAPI initialization at 0x%02X\n", sensorAddress);

  bme.intf = BME68X_I2C_INTF;
  bme.intf_ptr = &sensorAddress;
  bme.read = i2cRead;
  bme.write = i2cWrite;
  bme.delay_us = delayUs;
  bme.amb_temp = kAmbientTemperatureC;

  const int8_t initResult = bme68x_init(&bme);
  printApiResult("bme68x_init", initResult);
  if (initResult != BME68X_OK) {
    return false;
  }

  copyDefaultProfile();
  if (!configureBme688()) {
    return false;
  }

  if (!restartParallelMode()) {
    return false;
  }

  Serial.println("[bme688] initialization successful");
  Serial.println("[bme688] SensorAPI parallel-mode test is active");
  printProfileSummary();
  printCurrentProfileDetails();
  printCsvHeader();
  return true;
}

bool parseUint16List(const String &input, uint16_t *output) {
  int start = 0;
  for (uint8_t index = 0; index < kProfileLength; ++index) {
    const int comma = input.indexOf(',', start);
    String token;
    if (comma == -1) {
      token = input.substring(start);
    } else {
      token = input.substring(start, comma);
    }
    token.trim();
    if (token.isEmpty()) {
      return false;
    }

    const long parsed = token.toInt();
    if (parsed < 0 || parsed > 65535) {
      return false;
    }
    output[index] = static_cast<uint16_t>(parsed);

    if (comma == -1) {
      if (index != kProfileLength - 1) {
        return false;
      }
      start = input.length();
    } else {
      start = comma + 1;
    }
  }

  return input.indexOf(',', start) == -1;
}

bool validateProfileValues(const uint16_t *temps, const uint16_t *durations, uint16_t timeBaseMs) {
  if (timeBaseMs == 0 || timeBaseMs > 1000) {
    printStatusKeyValue("profile_validation", "invalid_time_base");
    return false;
  }

  for (uint8_t i = 0; i < kProfileLength; ++i) {
    if (temps[i] > 400) {
      Serial.printf("[status] profile_validation=temp_out_of_range:%u:%u\n", i, temps[i]);
      return false;
    }
    if (durations[i] == 0 || durations[i] > 255) {
      Serial.printf("[status] profile_validation=duration_out_of_range:%u:%u\n", i, durations[i]);
      return false;
    }
  }

  return true;
}

bool handleSetProfileCommand(const String &command) {
  const int tempPos = command.indexOf("temp=");
  const int durPos = command.indexOf("dur=");
  const int basePos = command.indexOf("base_ms=");
  if (tempPos < 0 || durPos < 0 || basePos < 0) {
    printStatusKeyValue("command_error", "missing_profile_fields");
    return false;
  }

  String tempValue = command.substring(tempPos + 5, durPos);
  String durValue = command.substring(durPos + 4, basePos);
  String baseValue = command.substring(basePos + 8);
  tempValue.trim();
  durValue.trim();
  baseValue.trim();

  uint16_t tempProfile[kProfileLength] = {};
  uint16_t durationProfile[kProfileLength] = {};
  if (!parseUint16List(tempValue, tempProfile) || !parseUint16List(durValue, durationProfile)) {
    printStatusKeyValue("command_error", "invalid_profile_list");
    return false;
  }

  const long parsedTimeBase = baseValue.toInt();
  if (parsedTimeBase <= 0 || parsedTimeBase > 65535) {
    printStatusKeyValue("command_error", "invalid_time_base");
    return false;
  }

  if (!validateProfileValues(tempProfile, durationProfile, static_cast<uint16_t>(parsedTimeBase))) {
    return false;
  }

  for (uint8_t i = 0; i < kProfileLength; ++i) {
    runtimeHeaterTempProfile[i] = tempProfile[i];
    runtimeHeaterDurationMultipliers[i] = durationProfile[i];
  }
  profileTimeBaseMs = static_cast<uint16_t>(parsedTimeBase);
  runtimeProfileActive = true;

  if (!applyCurrentProfile()) {
    printStatusKeyValue("command_error", "apply_profile_failed");
    return false;
  }

  if (!restartParallelMode()) {
    printStatusKeyValue("command_error", "restart_parallel_failed");
    return false;
  }

  printEventKeyValue("profile_updated", 1);
  printCurrentProfileDetails();
  return true;
}

void handleResetProfileCommand() {
  copyDefaultProfile();
  if (!applyCurrentProfile()) {
    printStatusKeyValue("command_error", "apply_default_profile_failed");
    return;
  }
  if (!restartParallelMode()) {
    printStatusKeyValue("command_error", "restart_parallel_failed");
    return;
  }

  printEventKeyValue("profile_reset", 1);
  printCurrentProfileDetails();
}

void handleCommand(const String &rawCommand) {
  String command = rawCommand;
  command.trim();
  if (command.isEmpty()) {
    return;
  }

  Serial.printf("[event] command_received=%s\n", command.c_str());

  if (command == "PING") {
    printStatusKeyValue("pong", "true");
    return;
  }

  if (command == "GET_PROFILE") {
    printCurrentProfileDetails();
    return;
  }

  if (command == "RESET_PROFILE") {
    handleResetProfileCommand();
    return;
  }

  if (command.startsWith("SET_PROFILE ")) {
    if (handleSetProfileCommand(command)) {
      printStatusKeyValue("set_profile", "ok");
    } else {
      printStatusKeyValue("set_profile", "failed");
    }
    return;
  }

  printStatusKeyValue("command_error", "unknown_command");
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

    if (commandLength >= (kCommandBufferSize - 1)) {
      commandOverflow = true;
      continue;
    }

    commandBuffer[commandLength++] = ch;
  }
}

void waitWithCommandPolling(uint32_t totalDelayUs) {
  uint32_t remaining = totalDelayUs;
  while (remaining > 0) {
    const uint32_t chunk = remaining > kCommandFriendlyDelayChunkUs ? kCommandFriendlyDelayChunkUs : remaining;
    shortDelayUs(chunk);
    remaining -= chunk;
    pollSerialCommands();
  }
}

void printDataRow(uint8_t fieldIndex, const bme68x_data &data) {
  const bool gasValid = (data.status & BME68X_GASM_VALID_MSK) != 0;
  const bool heaterStable = (data.status & BME68X_HEAT_STAB_MSK) != 0;

  Serial.printf("[csv] %lu,%lu,%u,%lu,%u,%u,%u,%.2f,%.2f,%.2f,%.2f,0x%02X,%u,%u\n",
                static_cast<unsigned long>(frameCounter),
                static_cast<unsigned long>(batchCounter),
                frameStepCount,
                millis(),
                fieldIndex,
                data.gas_index,
                data.meas_index,
                data.temperature,
                data.humidity,
                data.pressure / 100.0f,
                data.gas_resistance / 1000.0f,
                data.status,
                gasValid ? 1 : 0,
                heaterStable ? 1 : 0);
}

void startNewFrame(uint8_t gasIndex) {
  if (!frameSynced) {
    frameSynced = true;
    frameCounter = 1;
  } else {
    if (frameStepCount != kProfileLength) {
      Serial.printf("[frame] id=%lu incomplete step_count=%u\n",
                    static_cast<unsigned long>(frameCounter),
                    frameStepCount);
    }
    ++frameCounter;
  }

  frameStepCount = 0;
  Serial.printf("[frame] id=%lu started_at_ms=%lu gas_index=%u\n",
                static_cast<unsigned long>(frameCounter),
                millis(),
                gasIndex);
}

void finishFrameIfComplete() {
  if (frameSynced && frameStepCount == kProfileLength) {
    Serial.printf("[frame] id=%lu complete step_count=%u\n",
                  static_cast<unsigned long>(frameCounter),
                  frameStepCount);
  }
}

void processField(uint8_t fieldIndex, const bme68x_data &data) {
  if (data.status != kValidDataMask) {
    return;
  }

  const bool wrapped = (lastGasIndex >= 0) && (data.gas_index <= static_cast<uint8_t>(lastGasIndex));
  if (!frameSynced) {
    if (seenAnyField && wrapped) {
      startNewFrame(data.gas_index);
    } else {
      lastGasIndex = data.gas_index;
      seenAnyField = true;
      return;
    }
  } else if (wrapped) {
    startNewFrame(data.gas_index);
  }

  if (frameSynced) {
    ++frameStepCount;
    printDataRow(fieldIndex, data);
    finishFrameIfComplete();
  }

  lastGasIndex = data.gas_index;
  seenAnyField = true;
}

bool readMeasurementBatch() {
  waitWithCommandPolling(profilePollIntervalUs);

  struct bme68x_data data[kMaxFieldsPerRead] = {};
  uint8_t fieldCount = 0;
  const int8_t result = bme68x_get_data(BME68X_PARALLEL_MODE, data, &fieldCount, &bme);
  printApiResult("bme68x_get_data", result);
  if (result != BME68X_OK) {
    return false;
  }

  if (fieldCount == 0) {
    Serial.println("[bme688] no new data available");
    return false;
  }

  ++batchCounter;
  for (uint8_t i = 0; i < fieldCount; ++i) {
    processField(i, data[i]);
  }

  return true;
}

void setup() {
  Serial.begin(115200);

  const unsigned long serialWaitStartedAtMs = millis();
  while (!Serial && (millis() - serialWaitStartedAtMs) < kSerialWaitTimeoutMs) {
    delay(10);
  }

  delay(200);

  ++bootCount;
  printBootBanner();
  Serial.printf("Setup completed. Boot counter: %lu\n", bootCount);
  Serial.println("[setup] starting I2C on the board default pins");

  Wire.begin(SDA, SCL);
  Wire.setClock(100000);
  delay(50);

  scanI2CBus();
  sensorReady = initializeBme688();

  if (!sensorReady) {
    Serial.println("[result] BME688 SensorAPI parallel-mode test failed. Check wiring, power and I2C address.");
    Serial.println("[hint] StampS3 default I2C pins are SDA=13 and SCL=15.");
  } else {
    Serial.println("[result] BME688 SensorAPI parallel-mode test setup complete. CSV rows will follow.");
    printStatusKeyValue("ready", "true");
  }
}

void loop() {
  pollSerialCommands();

  if (!sensorReady) {
    delay(100);
    return;
  }

  if (!readMeasurementBatch()) {
    Serial.println("[bme688] batch read failed");
  }
}
