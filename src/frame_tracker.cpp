#include "frame_tracker.h"

#include "app_config.h"
#include "profile_state.h"

namespace {
bool headerPrinted = false;
bool frameSynced = false;
bool seenAnyField = false;
int8_t lastGasIndex = -1;
uint8_t frameStepCount = 0;
uint32_t batchCounter = 0;
uint32_t frameCounter = 0;

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
    if (frameStepCount != profile_state::length()) {
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
  if (frameSynced && frameStepCount == profile_state::length()) {
    Serial.printf("[frame] id=%lu complete step_count=%u\n",
                  static_cast<unsigned long>(frameCounter),
                  frameStepCount);
  }
}

void processField(uint8_t fieldIndex, const bme68x_data &data) {
  if (data.status != app_config::kValidDataMask) {
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
}  // namespace

namespace frame_tracker {
void printCsvHeader() {
  if (headerPrinted) {
    return;
  }

  Serial.println("[csv] frame_id,batch_id,frame_step,host_ms,field_index,gas_index,meas_index,temp_c,humidity_pct,pressure_hpa,gas_kohms,status_hex,gas_valid,heat_stable");
  headerPrinted = true;
}

void processMeasurementBatch(const bme68x_data *data, uint8_t fieldCount) {
  ++batchCounter;
  for (uint8_t i = 0; i < fieldCount; ++i) {
    processField(i, data[i]);
  }
}
}  // namespace frame_tracker
