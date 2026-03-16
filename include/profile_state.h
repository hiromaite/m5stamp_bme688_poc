#pragma once

#include <Arduino.h>

namespace profile_state {
void resetToDefault();
bool applyFromCommandValues(const String &tempValue,
                            const String &durValue,
                            const String &baseValue,
                            String &errorCode,
                            bool &errorIsValidation);

const uint16_t *heaterTemps();
const uint16_t *heaterDurations();
uint16_t timeBaseMs();
uint8_t length();
bool isRuntimeProfileActive();
const char *profileId();
}  // namespace profile_state
