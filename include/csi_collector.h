#pragma once
#include <stdint.h>

#define CSI_MAX_LEN 128

struct CsiPacket {
    float    data[CSI_MAX_LEN];
    int      len;
    int      rssi;
    uint32_t timestamp_ms;
};

void csi_collector_init();
bool csi_collector_get(CsiPacket* out);
