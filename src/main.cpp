#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "config.h"
#include "csi_collector.h"

static uint32_t seq_num    = 0;
static uint32_t last_tx_ms = 0;

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
    delay(3000);  // USB CDC 열거 대기
    wifi_connect();
    csi_collector_init();  // WiFi 연결 후 CSI 활성화
}

void loop() {
    // WiFi 끊기면 재연결
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi lost. Reconnecting...");
        wifi_connect();
    }

    // 50ms 간격 전송 (초당 20개)
    uint32_t now = millis();
    if (now - last_tx_ms < 50) return;
    last_tx_ms = now;

    CsiPacket pkt;
    if (!csi_collector_get(&pkt)) return;

    JsonDocument doc;
    doc["node_id"]     = NODE_ID;
    doc["seq_num"]     = seq_num++;
    doc["rssi"]        = pkt.rssi;
    doc["detected_at"] = pkt.timestamp_ms;

    JsonArray matrix = doc["csi_matrix"].to<JsonArray>();
    for (int i = 0; i < pkt.len; i++) {
        matrix.add(pkt.data[i]);
    }

    String body;
    serializeJson(doc, body);

    HTTPClient http;
    http.begin(FASTAPI_URL);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(body);
    if (code != 200) {
        Serial.printf("[WARN] POST %d  seq=%lu\n", code, seq_num - 1);
    }
    http.end();
}
