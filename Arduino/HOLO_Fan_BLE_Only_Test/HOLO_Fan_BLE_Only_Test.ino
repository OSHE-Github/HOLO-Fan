/*
  HOLO-FAN - BLE-ONLY TEST FOR ARDUINO NANO ESP32

  Purpose:
    Test BLE advertising and connection independently of the NeoPixel blades
    and Hall sensor. This sketch uses the same BLE library and GATT UUIDs as
    the uploaded Holo-Fan firmware.

  BLE name: Holo-Fan

  Expected onboard RGB LED behavior (active-low channels):
    BLUE  = advertising / waiting for a connection
    GREEN = a BLE client is connected
    RED   = briefly shown after disconnect, then returns to BLUE

  IMPORTANT:
    - This sketch does not control the blades or Hall sensor.
    - It provides the same service and characteristic UUIDs so nRF Connect
      and a desktop client can discover the expected GATT structure.
    - It is a connection test, not the image-transfer firmware. Do not use
      this sketch to send an image to the fan.
    - Serial is optional. The sketch never waits for Serial to be connected.
*/

#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Keep the Holo-Fan BLE identifiers identical to the main firmware.
static const char* DEVICE_NAME = "Holo-Fan";
static const char* SERVICE_UUID = "9a6b1000-5b3f-4c21-9f31-2d4c5b7a0001";
static const char* CONTROL_UUID = "9a6b1001-5b3f-4c21-9f31-2d4c5b7a0001";
static const char* DATA_UUID    = "9a6b1002-5b3f-4c21-9f31-2d4c5b7a0001";
static const char* STATUS_UUID = "9a6b1003-5b3f-4c21-9f31-2d4c5b7a0001";

BLEServer* bleServer = nullptr;
BLECharacteristic* controlCharacteristic = nullptr;
BLECharacteristic* dataCharacteristic = nullptr;
BLECharacteristic* statusCharacteristic = nullptr;

volatile bool deviceConnected = false;

// Nano ESP32 RGB LED channels are active LOW in the main Holo-Fan sketch.
void setBoardColor(bool redOn, bool greenOn, bool blueOn) {
  digitalWrite(LED_RED,   redOn   ? LOW : HIGH);
  digitalWrite(LED_GREEN, greenOn ? LOW : HIGH);
  digitalWrite(LED_BLUE,  blueOn  ? LOW : HIGH);
}

void showAdvertisingColor() { setBoardColor(false, false, true); }
void showConnectedColor()  { setBoardColor(false, true, false); }
void showDisconnectedColor() { setBoardColor(true, false, false); }

class HoloFanTestServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* server) override {
    deviceConnected = true;
    showConnectedColor();

    if (statusCharacteristic != nullptr) {
      statusCharacteristic->setValue("CONNECTED - BLE TEST ONLY");
      statusCharacteristic->notify();
    }
  }

  void onDisconnect(BLEServer* server) override {
    deviceConnected = false;
    showDisconnectedColor();
    delay(250);

    // Resume advertising so the phone/desktop can find the Nano again.
    BLEDevice::startAdvertising();
    showAdvertisingColor();
  }
};

class ControlTestCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* characteristic) override {
    // This test intentionally does not execute Holo-Fan commands.
    // It only verifies that the BLE characteristic can receive a write.
    std::string value = characteristic->getValue();
    if (statusCharacteristic != nullptr) {
      statusCharacteristic->setValue("BLE TEST: CONTROL WRITE RECEIVED");
      if (deviceConnected) statusCharacteristic->notify();
    }
  }
};

void setup() {
  // Serial is optional; never wait for a USB Serial connection.
  //Serial.begin(115200);
  delay(300);

  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);
  setBoardColor(false, false, false);

  // Start the BLE stack and create the same GATT service as Holo-Fan.
  BLEDevice::init(DEVICE_NAME);

  bleServer = BLEDevice::createServer();
  bleServer->setCallbacks(new HoloFanTestServerCallbacks());

  BLEService* service = bleServer->createService(SERVICE_UUID);

  controlCharacteristic = service->createCharacteristic(
    CONTROL_UUID,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE
  );
  controlCharacteristic->setValue("BLE TEST ONLY");
  controlCharacteristic->setCallbacks(new ControlTestCallbacks());

  dataCharacteristic = service->createCharacteristic(
    DATA_UUID,
    BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR
  );
  dataCharacteristic->setValue("BLE TEST ONLY");

  statusCharacteristic = service->createCharacteristic(
    STATUS_UUID,
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
  );
  statusCharacteristic->addDescriptor(new BLE2902());
  statusCharacteristic->setValue("READY - BLE TEST ONLY");

  service->start();

  // Advertise the device name and Holo-Fan service UUID.
  BLEAdvertising* advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->setScanResponse(true);

  BLEDevice::startAdvertising();
  showAdvertisingColor();

 // Serial.println("Holo-Fan BLE-only test started.");
 // Serial.println("Scan for: Holo-Fan");
 // Serial.println("Expected RGB: BLUE while advertising, GREEN when connected.");
}

void loop() {
  // BLE callbacks run in the background. No USB Serial connection is needed.
  delay(20);
}
