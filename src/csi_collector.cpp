#include "csi_collector.h"
#include <Arduino.h>
#include <math.h>
#include "esp_wifi.h"
#include "freertos/queue.h"

static QueueHandle_t s_csi_queue = nullptr;

static void csi_callback(void* ctx, wifi_csi_info_t* info) {
    if (!info || !info->buf || !s_csi_queue) return;

    CsiPacket pkt;
    pkt.rssi         = info->rx_ctrl.rssi;
    pkt.timestamp_ms = millis();

    // I/Q 쌍 → 진폭(amplitude) 변환
    int pairs = info->len / 2;
    if (pairs > CSI_MAX_LEN) pairs = CSI_MAX_LEN;
    pkt.len = pairs;

    int8_t* buf = info->buf;
    for (int i = 0; i < pairs; i++) {
        float I = buf[i * 2];
        float Q = buf[i * 2 + 1];
        pkt.data[i] = sqrtf(I * I + Q * Q);
    }

    // 큐가 가득 차 있으면 오래된 것 버리고 새것 삽입
    if (xQueueIsQueueFullFromISR(s_csi_queue)) {
        CsiPacket dummy;
        xQueueReceiveFromISR(s_csi_queue, &dummy, nullptr);
    }
    xQueueSendFromISR(s_csi_queue, &pkt, nullptr);
}

void csi_collector_init() {
    s_csi_queue = xQueueCreate(10, sizeof(CsiPacket));

    wifi_csi_config_t cfg = {};
    cfg.lltf_en           = true;
    cfg.htltf_en          = true;
    cfg.stbc_htltf2_en    = true;
    cfg.ltf_merge_en      = true;
    cfg.channel_filter_en = false;
    cfg.manu_scale        = false;
    esp_wifi_set_csi_config(&cfg);

    esp_wifi_set_csi_rx_cb(csi_callback, nullptr);
    esp_wifi_set_csi(true);
}

bool csi_collector_get(CsiPacket* out) {
    return xQueueReceive(s_csi_queue, out, 0) == pdTRUE;
}
