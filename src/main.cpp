#include <Arduino.h>
#include <Wire.h>

#include "app_config.h"
#include "bme688_controller.h"
#include "frame_tracker.h"
#include "serial_protocol.h"

namespace {
unsigned long bootCount = 0;
bool sensorReady = false;
}

void setup() {
  Serial.begin(115200);

  const unsigned long serialWaitStartedAtMs = millis();
  while (!Serial && (millis() - serialWaitStartedAtMs) < app_config::kSerialWaitTimeoutMs) {
    delay(10);
  }

  delay(200);

  ++bootCount;
  serial_protocol::printBootBanner();
  Serial.printf("Setup completed. Boot counter: %lu\n", bootCount);
  Serial.println("[setup] starting I2C on the board default pins");

  Wire.begin(SDA, SCL);
  Wire.setClock(100000);
  delay(50);

  bme688_controller::scanI2CBus();
  sensorReady = bme688_controller::initialize();

  if (!sensorReady) {
    Serial.println("[result] BME688 SensorAPI parallel-mode test failed. Check wiring, power and I2C address.");
    Serial.println("[hint] StampS3 default I2C pins are SDA=13 and SCL=15.");
  } else {
    serial_protocol::printProfileSummary();
    serial_protocol::printCurrentProfileDetails();
    frame_tracker::printCsvHeader();
    Serial.println("[result] BME688 SensorAPI parallel-mode test setup complete. CSV rows will follow.");
  }
}

void loop() {
  serial_protocol::pollSerialCommands();

  if (!sensorReady) {
    delay(1000);
    return;
  }

  serial_protocol::waitWithCommandPolling(bme688_controller::pollIntervalUs());

  bme68x_data data[app_config::kMaxFieldsPerRead] = {};
  uint8_t fieldCount = 0;
  if (bme688_controller::readMeasurementBatch(data, fieldCount)) {
    frame_tracker::processMeasurementBatch(data, fieldCount);
  }
}
