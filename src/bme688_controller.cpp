#include "bme688_controller.h"

#include <Wire.h>

#include "app_config.h"
#include "profile_state.h"

namespace {
struct bme68x_dev bme = {};
struct bme68x_conf sensorConf = {};
struct bme68x_heatr_conf heaterConf = {};

uint8_t sensorAddress = 0;
uint32_t profilePollIntervalUs = 0;

void printApiResult(const char *label, int8_t result) {
  if (result == BME68X_OK) {
    return;
  }

  Serial.printf("[%s] SensorAPI returned %d\n", label, result);
}

bool i2cDeviceExists(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
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

void delayUs(uint32_t period, void *intf_ptr) {
  (void)intf_ptr;
  bme688_controller::shortDelayUs(period);
}

bool applyCurrentProfile() {
  heaterConf.enable = BME68X_ENABLE;
  heaterConf.heatr_temp = 0;
  heaterConf.heatr_dur = 0;
  heaterConf.heatr_temp_prof = const_cast<uint16_t *>(profile_state::heaterTemps());
  heaterConf.heatr_dur_prof = const_cast<uint16_t *>(profile_state::heaterDurations());
  heaterConf.profile_len = profile_state::length();

  const uint32_t measurementDurationUs = bme68x_get_meas_dur(BME68X_PARALLEL_MODE, &sensorConf, &bme);
  const uint32_t measurementDurationMs = measurementDurationUs / 1000;
  if (profile_state::timeBaseMs() <= measurementDurationMs) {
    Serial.printf("[status] apply_profile_error=time_base_too_small:%u\n", profile_state::timeBaseMs());
    return false;
  }

  heaterConf.shared_heatr_dur = static_cast<uint16_t>(profile_state::timeBaseMs() - measurementDurationMs);

  const int8_t heaterResult = bme68x_set_heatr_conf(BME68X_PARALLEL_MODE, &heaterConf, &bme);
  printApiResult("bme68x_set_heatr_conf", heaterResult);
  if (heaterResult != BME68X_OK) {
    return false;
  }

  profilePollIntervalUs = measurementDurationUs + (static_cast<uint32_t>(heaterConf.shared_heatr_dur) * 1000);
  return true;
}

bool configureSensor() {
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

bool restartParallelModeInternal() {
  const int8_t modeResult = bme68x_set_op_mode(BME68X_PARALLEL_MODE, &bme);
  printApiResult("bme68x_set_op_mode", modeResult);
  return modeResult == BME68X_OK;
}
}  // namespace

namespace bme688_controller {
void shortDelayUs(uint32_t period) {
  if (period >= 1000) {
    delay(period / 1000);
    period %= 1000;
  }

  if (period > 0) {
    delayMicroseconds(period);
  }
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

bool initialize() {
  if (i2cDeviceExists(app_config::kBme68xPrimaryAddress)) {
    sensorAddress = app_config::kBme68xPrimaryAddress;
  } else if (i2cDeviceExists(app_config::kBme68xSecondaryAddress)) {
    sensorAddress = app_config::kBme68xSecondaryAddress;
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
  bme.amb_temp = app_config::kAmbientTemperatureC;

  const int8_t initResult = bme68x_init(&bme);
  printApiResult("bme68x_init", initResult);
  if (initResult != BME68X_OK) {
    return false;
  }

  profile_state::resetToDefault();
  if (!configureSensor()) {
    return false;
  }

  if (!restartParallelModeInternal()) {
    return false;
  }

  Serial.println("[bme688] initialization successful");
  Serial.println("[bme688] SensorAPI parallel-mode test is active");
  return true;
}

bool syncActiveProfile(const char *&errorCode) {
  if (!applyCurrentProfile()) {
    errorCode = "apply_profile_failed";
    return false;
  }

  if (!restartParallelModeInternal()) {
    errorCode = "restart_parallel_failed";
    return false;
  }

  errorCode = nullptr;
  return true;
}

uint32_t pollIntervalUs() {
  return profilePollIntervalUs;
}

bool readMeasurementBatch(struct bme68x_data *data, uint8_t &fieldCount) {
  fieldCount = 0;
  const int8_t result = bme68x_get_data(BME68X_PARALLEL_MODE, data, &fieldCount, &bme);
  printApiResult("bme68x_get_data", result);
  if (result != BME68X_OK) {
    return false;
  }

  if (fieldCount == 0) {
    Serial.println("[bme688] no new data available");
    return false;
  }

  return true;
}
}  // namespace bme688_controller
