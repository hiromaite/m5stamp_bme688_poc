#pragma once

#include <Arduino.h>

namespace serial_protocol {
void printBootBanner();
void printCapabilityKeyValue(const char *key, const char *value);
void printCapabilityKeyValue(const char *key, int value);
void printStatusKeyValue(const char *key, const char *value);
void printStatusKeyValue(const char *key, int value);
void printEventKeyValue(const char *key, const char *value);
void printEventKeyValue(const char *key, int value);
void printCapabilities();
void printCurrentProfileDetails();
void printProfileSummary();
void pollSerialCommands();
void waitWithCommandPolling(uint32_t totalDelayUs);
}  // namespace serial_protocol
