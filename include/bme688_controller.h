#pragma once

#include <Arduino.h>

extern "C" {
#include <bme68x.h>
}

namespace bme688_controller {
void shortDelayUs(uint32_t period);
void scanI2CBus();
bool initialize();
bool syncActiveProfile(const char *&errorCode);
uint32_t pollIntervalUs();
bool readMeasurementBatch(struct bme68x_data *data, uint8_t &fieldCount);
}  // namespace bme688_controller
