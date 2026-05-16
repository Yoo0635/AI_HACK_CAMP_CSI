#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "config.h"
#include "csi_collector.h"

#define LED_PIN 48

// Binary packet layout must match backend PACKET_FORMAT = "<4s8sIIi64f"
struct __attribute__((packed)) BinaryPacket {
    char     header[4];      // "CSI!"
    char     node_id[8];     // null-padded node identifier
    uint32_t detected_at;    // millis() timestamp
    uint32_t seq_num;        // monotonic counter
    int32_t  rssi;
    float    csi_data[64];   // exactly 64 amplitude values
};

static_assert(sizeof(BinaryPacket) == 280, "BinaryPacket size must be 280 bytes");

static uint32_t s_seq_num    = 0;
static uint32_t s_last_tx_ms = 0;

static void wifi_connect() {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Connecting WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\nConnected. IP: %s\n", WiFi.localIP().toString().c_str());
}

void setup() {
    Serial.begin(115200);
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    delay(3000);
    wifi_connect();
    csi_collector_init();
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi lost. Reconnecting...");
        wifi_connect();
    }

    uint32_t now = millis();
    if (now - s_last_tx_ms < 50) return;  // 20 Hz
    s_last_tx_ms = now;

    CsiPacket pkt;
    if (!csi_collector_get(&pkt)) return;

    BinaryPacket bin = {};
    memcpy(bin.header, "CSI!", 4);
    strncpy(bin.node_id, NODE_ID, sizeof(bin.node_id));
    bin.detected_at = pkt.timestamp_ms;
    bin.seq_num     = s_seq_num++;
    bin.rssi        = (int32_t)pkt.rssi;

    int copy_len = (pkt.len < 64) ? pkt.len : 64;
    for (int i = 0; i < copy_len; i++) {
        bin.csi_data[i] = pkt.data[i];
    }
    // remaining slots stay 0.0f (zero-initialised above)

    HTTPClient http;
    http.begin(FASTAPI_URL);
    http.addHeader("Content-Type", "application/octet-stream");
    digitalWrite(LED_PIN, HIGH);
    int code = http.POST((uint8_t*)&bin, sizeof(bin));
    digitalWrite(LED_PIN, LOW);

    if (code != 200) {
        Serial.printf("[WARN] POST %d  seq=%lu\n", code, s_seq_num - 1);
    } else {
        Serial.printf("[OK]   seq=%lu  rssi=%d  csi_len=%d\n",
                      s_seq_num - 1, pkt.rssi, pkt.len);
    }
    http.end();
}
