#include "profile_state.h"

#include "app_config.h"

namespace {
uint16_t runtimeHeaterTempProfile[app_config::kMaxProfileLength] = {};
uint16_t runtimeHeaterDurationMultipliers[app_config::kMaxProfileLength] = {};
uint16_t profileTimeBaseMs = app_config::kDefaultProfileTimeBaseMs;
uint8_t currentProfileLength = app_config::kMaxProfileLength;
bool runtimeProfileActive = false;

bool parseStrictUint16(const String &input, uint16_t &parsedValue) {
  String token = input;
  token.trim();
  if (token.isEmpty()) {
    return false;
  }

  uint32_t value = 0;
  for (unsigned int i = 0; i < token.length(); ++i) {
    const char ch = token.charAt(i);
    if (ch < '0' || ch > '9') {
      return false;
    }

    value = (value * 10U) + static_cast<uint32_t>(ch - '0');
    if (value > 65535U) {
      return false;
    }
  }

  parsedValue = static_cast<uint16_t>(value);
  return true;
}

bool parseUint16List(const String &input, uint16_t *output, uint8_t &parsedLength) {
  int start = 0;
  parsedLength = 0;
  while (start <= input.length()) {
    const int comma = input.indexOf(',', start);
    String token = (comma == -1) ? input.substring(start) : input.substring(start, comma);
    token.trim();
    if (token.isEmpty()) {
      return false;
    }

    uint16_t parsed = 0;
    if (!parseStrictUint16(token, parsed)) {
      return false;
    }
    if (parsedLength >= app_config::kMaxProfileLength) {
      return false;
    }

    output[parsedLength++] = parsed;
    if (comma == -1) {
      break;
    }
    start = comma + 1;
  }

  return parsedLength >= app_config::kMinProfileLength;
}

bool validateProfileValues(const uint16_t *temps,
                           const uint16_t *durations,
                           uint16_t timeBaseMs,
                           uint8_t profileLength,
                           String &errorCode) {
  if (timeBaseMs == 0 || timeBaseMs > 1000) {
    errorCode = "invalid_time_base";
    return false;
  }

  if (profileLength < app_config::kMinProfileLength || profileLength > app_config::kMaxProfileLength) {
    errorCode = "invalid_profile_length";
    return false;
  }

  for (uint8_t i = 0; i < profileLength; ++i) {
    if (temps[i] > 400) {
      errorCode = "temp_out_of_range:" + String(i) + ":" + String(temps[i]);
      return false;
    }
    if (durations[i] == 0 || durations[i] > 255) {
      errorCode = "duration_out_of_range:" + String(i) + ":" + String(durations[i]);
      return false;
    }
  }

  return true;
}
}  // namespace

namespace profile_state {
void resetToDefault() {
  for (uint8_t i = 0; i < app_config::kMaxProfileLength; ++i) {
    runtimeHeaterTempProfile[i] = app_config::kDefaultHeaterTempProfile[i];
    runtimeHeaterDurationMultipliers[i] = app_config::kDefaultHeaterDurationMultipliers[i];
  }
  profileTimeBaseMs = app_config::kDefaultProfileTimeBaseMs;
  currentProfileLength = app_config::kMaxProfileLength;
  runtimeProfileActive = false;
}

bool applyFromCommandValues(const String &tempValue,
                            const String &durValue,
                            const String &baseValue,
                            String &errorCode,
                            bool &errorIsValidation) {
  uint16_t tempProfile[app_config::kMaxProfileLength] = {};
  uint16_t durationProfile[app_config::kMaxProfileLength] = {};
  uint8_t parsedTempLength = 0;
  uint8_t parsedDurationLength = 0;
  errorIsValidation = false;

  if (!parseUint16List(tempValue, tempProfile, parsedTempLength) ||
      !parseUint16List(durValue, durationProfile, parsedDurationLength)) {
    errorCode = "invalid_profile_list";
    return false;
  }

  if (parsedTempLength != parsedDurationLength) {
    errorCode = "profile_length_mismatch";
    return false;
  }

  uint16_t parsedTimeBase = 0;
  if (!parseStrictUint16(baseValue, parsedTimeBase) || parsedTimeBase == 0) {
    errorCode = "invalid_time_base";
    return false;
  }

  errorIsValidation = true;
  if (!validateProfileValues(tempProfile, durationProfile, parsedTimeBase, parsedTempLength, errorCode)) {
    return false;
  }
  errorIsValidation = false;

  for (uint8_t i = 0; i < app_config::kMaxProfileLength; ++i) {
    if (i < parsedTempLength) {
      runtimeHeaterTempProfile[i] = tempProfile[i];
      runtimeHeaterDurationMultipliers[i] = durationProfile[i];
    } else {
      runtimeHeaterTempProfile[i] = 0;
      runtimeHeaterDurationMultipliers[i] = 0;
    }
  }

  profileTimeBaseMs = parsedTimeBase;
  currentProfileLength = parsedTempLength;
  runtimeProfileActive = true;
  return true;
}

const uint16_t *heaterTemps() {
  return runtimeHeaterTempProfile;
}

const uint16_t *heaterDurations() {
  return runtimeHeaterDurationMultipliers;
}

uint16_t timeBaseMs() {
  return profileTimeBaseMs;
}

uint8_t length() {
  return currentProfileLength;
}

bool isRuntimeProfileActive() {
  return runtimeProfileActive;
}

const char *profileId() {
  return runtimeProfileActive ? "runtime_custom" : "default_vsc_10step";
}
}  // namespace profile_state
