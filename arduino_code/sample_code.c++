#include <ESP8266WiFi.h>
#include <WebSocketsServer.h>

const char* ssid = "Your_SSID";
const char* password = "Your_PASSWORD";

WebSocketsServer webSocket = WebSocketsServer(81);

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");

  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
}

void loop() {
  webSocket.loop();
}

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  if (type == WStype_CONNECTED) {
    Serial.println("Client connected");
  } else if (type == WStype_TEXT) {
    String data = "{\"heart_rate\": 72, \"temperature\": 36.5}";
    webSocket.sendTXT(num, data);
  }
}