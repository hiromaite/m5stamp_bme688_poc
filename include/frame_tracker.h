#pragma once

#include <Arduino.h>

extern "C" {
#include <bme68x.h>
}

namespace frame_tracker {
void printCsvHeader();
void processMeasurementBatch(const struct bme68x_data *data, uint8_t fieldCount);
}  // namespace frame_tracker
