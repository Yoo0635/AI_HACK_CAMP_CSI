#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "config.h"
#include "csi_collector.h"

static uint32_t seq_num = 0;

void setup() {
    Serial.begin(115200);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Connecting WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\nConnected. IP: %s\n", WiFi.localIP().toString().c_str());

    csi_collector_init();
}

void loop() {
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

    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(FASTAPI_URL);
        http.addHeader("Content-Type", "application/json");
        int code = http.POST(body);
        if (code != 200) {
            Serial.printf("POST failed: %d\n", code);
        }
        http.end();
    }
}
