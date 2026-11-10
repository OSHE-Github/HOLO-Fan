/*
  =============================================================================
  HOLO-FAN - NANO ESP32 FIRMWARE
  =============================================================================

  This sketch combines:
    1. The original Holo-Fan POV display code.
    2. Bluetooth Low Energy (BLE) communication.
    3. The Nano ESP32 onboard RGB LED connection indicator.
    4. Bluetooth commands for uploading image.txt and starting/stopping display.

  BOARD:
    Arduino Nano ESP32

  LIBRARIES:
    - Adafruit NeoPixel
    - Arduino SpiNINA
    - ESP32 BLE library supplied with the ESP32 Arduino board package

  ---------------------------------------------------------------------------
  HARDWARE PIN ASSIGNMENTS
  ---------------------------------------------------------------------------
    D2 = LED data for blade 1
    D3 = LED data for blade 2
    D4 = LED data for blade 3
    D5 = LED data for blade 4
    D6 = rotation/index sensor input

  The onboard RGB LED is controlled using the Nano ESP32 board definitions:
    LED_RED, LED_GREEN, LED_BLUE

    - Confirm the LED strip voltage, common ground, signal level, and power
      wiring before connecting the LED strips.
    - The original POV rendering approach updates four NeoPixel strips in
      sequence. This is a starting integration, not a guarantee of smooth
      high-speed POV performance. Each NeoPixel show() call takes time.

  ---------------------------------------------------------------------------
  RGB STATUS LED
  ---------------------------------------------------------------------------
    BLUE  = BLE advertising; waiting for a computer/phone to connect
    GREEN = a BLE client is connected
    RED   = a client disconnected; shown briefly before returning to BLUE

  Nano ESP32 RGB LED channels are active LOW in this sketch:
    LOW  = channel on
    HIGH = channel off

  If your board displays green and blue reversed, the channel mapping may
  differ on your board revision.

  ---------------------------------------------------------------------------
  BLUETOOTH NAME AND UUIDS
  ---------------------------------------------------------------------------
    Device name: Holo-Fan

    Service UUID:
      9a6b1000-5b3f-4c21-9f31-2d4c5b7a0001

    Control characteristic:
      9a6b1001-5b3f-4c21-9f31-2d4c5b7a0001

    Image data characteristic:
      9a6b1002-5b3f-4c21-9f31-2d4c5b7a0001

    Status characteristic:
      9a6b1003-5b3f-4c21-9f31-2d4c5b7a0001

  ---------------------------------------------------------------------------
  CONTROL COMMANDS
  ---------------------------------------------------------------------------
    BEGIN_FILE  - prepare to receive a new image.txt file
    END_FILE    - finish and validate the received file
    START       - start displaying the loaded image
    STOP        - stop displaying and clear the LED blades
    STATUS      - send current state, RPM, LED count, blade count, dead space

  Send the commands as plain text to the Control characteristic.

  ---------------------------------------------------------------------------
  IMAGE.TXT FORMAT
  ---------------------------------------------------------------------------
    First line: number of vectors
    Following lines: exactly 25 comma-separated six-digit hex colors.

    Example:
      2
      #FF0000,#00FF00,#0000FF,... (25 colors total)
      #FFFFFF,#000000,#FFFFFF,... (25 colors total)

    Each data write can carry up to 20 bytes in this sketch. The desktop
    program must split the text file into chunks and write each chunk to the
    Data characteristic, in order, between BEGIN_FILE and END_FILE.

    The first vector is intended to represent the 3:00 position. The existing
    rendering/index alignment still needs to be calibrated on the real fan.

  ---------------------------------------------------------------------------
  NOTE ABOUT THE EARLIER NEO PIXEL LINKER ERROR
  ---------------------------------------------------------------------------
    If compilation reports an undefined reference to
    digitalPinToGPIONumber from Adafruit_NeoPixel, check the Nano ESP32
    Tools > Pin Numbering setting and the installed board/library versions.
    This combined sketch does not remove the need for a compatible
    Adafruit_NeoPixel build.
  =============================================================================
*/

#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Adafruit_NeoPixel.h>
#include <stdlib.h>
#include <string.h>

// 1. USER SETTINGS / HARDWARE CONFIGURATION

// Number of physical blades on the fan.
static const uint8_t BLADE_COUNT = 4;

// Arduino pin connected to the data input of each blade's LED strip.
//
// These are Arduino pin numbers, matching the labels used in the original
// POV sketch. Check the Nano ESP32 Tools > Pin Numbering setting and your
// physical wiring before changing them.
static const uint8_t BLADE_PINS[BLADE_COUNT] = { D2, D3, D4, D5 };

// Pin connected to the once-per-revolution index sensor.
static const uint8_t INDEX_PIN = D6;

// Number of LEDs on each blade.
static const uint16_t MAX_LEDS = 25;

// Number of LEDs at the inner end of each blade that should remain dark.
static const uint8_t DEAD_SPACE_LEDS = 2;

// Maximum number of angular vectors accepted from image.txt.
static const uint16_t MAX_VECTORS = 360;

// NeoPixel brightness, from 0 (off) to 255 (full brightness).
// Start low while testing to reduce power demand and glare.
static const uint8_t LED_BRIGHTNESS = 30;

// Ignore index sensor pulses that occur less than this many microseconds
// after the previous accepted pulse. This helps reject electrical noise.
static const uint32_t MIN_INDEX_INTERVAL_US = 30000;

// A vector line contains 25 colors, each normally 6 hex digits, optional '#',
// and commas. This buffer is sized to allow the full line.
static const uint16_t MAX_LINE_CHARS = (MAX_LEDS * 8) + 4;

// BLE device name shown in a BLE scanner on a desktop or phone.
static const char* DEVICE_NAME = "Holo-Fan";

// BLE service and characteristic UUIDs.
// Keep these unchanged if your desktop software expects these UUIDs.
static const char* SERVICE_UUID =
  "9a6b1000-5b3f-4c21-9f31-2d4c5b7a0001";

static const char* CONTROL_UUID =
  "9a6b1001-5b3f-4c21-9f31-2d4c5b7a0001";

static const char* DATA_UUID =
  "9a6b1002-5b3f-4c21-9f31-2d4c5b7a0001";

static const char* STATUS_UUID =
  "9a6b1003-5b3f-4c21-9f31-2d4c5b7a0001";

// 2. BLUETOOTH OBJECTS AND STATE

// Pointers to BLE objects are filled in during setup().
BLEServer* bleServer = nullptr;
BLECharacteristic* controlCharacteristic = nullptr;
BLECharacteristic* dataCharacteristic = nullptr;
BLECharacteristic* statusCharacteristic = nullptr;

// True while a BLE computer/phone is connected.
volatile bool deviceConnected = false;

// 3. POV IMAGE STORAGE

// Each pixel is stored as three bytes: red, green, blue.
//
// MAX_FRAME_BYTES = 360 vectors * 25 LEDs * 3 color bytes = 27,000 bytes.
// Two buffers are used:
//   activeFrame    = the image currently available for display
//   receivingFrame = the image currently being uploaded
//
// The two-buffer approach prevents a partially uploaded image from replacing
// the current display image before END_FILE validates the upload.
static const uint32_t MAX_FRAME_BYTES =
  (uint32_t)MAX_VECTORS * MAX_LEDS * 3UL;

uint8_t frameA[MAX_FRAME_BYTES];
uint8_t frameB[MAX_FRAME_BYTES];

uint8_t* activeFrame = frameA;
uint8_t* receivingFrame = frameB;

// One Adafruit NeoPixel object controls each blade's LED strip.
Adafruit_NeoPixel* blades[BLADE_COUNT];

// 4. ROTATION / RPM VARIABLES

// KY-024 digital output (DO) is connected to D6.
// A magnet should pass the sensor ONCE per complete revolution.
//
// The interrupt records the time of each accepted magnet detection.
// The main loop uses that timestamp and revolution period to calculate
// the current angular position of the fan and select the matching image vector.
volatile uint32_t lastIndexMicros = 0;
volatile uint32_t revolutionMicros = 0;
volatile bool indexPulseSeen = false;

// Set this to rotate the displayed image for physical sensor/magnet alignment.
// 0 means image vector 0 is displayed at the instant the magnet is detected.
// Increase/decrease this value after testing if the image is angularly offset.
static const int16_t INDEX_VECTOR_OFFSET = 0;

// 5. FILE UPLOAD AND DISPLAY STATE

uint16_t vectorCount = 0;
uint16_t ledCount = 0;

uint16_t fileExpectedVectors = 0;
uint16_t fileRowsParsed = 0;
uint16_t fileLineNumber = 0;

// Current length of the line being assembled from BLE data chunks.
uint16_t lineLength = 0;

// BLE sends chunks, not necessarily whole text lines. This buffer joins
// chunks together until a newline character is received.
char lineBuffer[MAX_LINE_CHARS + 1];

// File and display state flags.
bool receivingFile = false;
bool fileFailed = false;
bool displayRunning = false;

// Holds a short error message if an upload fails.
char lastError[20] = "";

// Used to send periodic status updates.
uint32_t lastStatusMs = 0;

// Timing used to decide when the next POV vector should be rendered.
uint32_t lastRenderMicros = 0;

// Current vector index.
uint16_t lastVector = 0;

// 6. ONBOARD RGB LED STATUS FUNCTIONS

// Set the three channels of the Nano ESP32's onboard RGB LED.
//
// The channels are treated as active LOW:
//   turn channel on  -> write LOW
//   turn channel off -> write HIGH
//
// If the LED behaves unexpectedly, verify the pin definitions and board
// revision before changing the active-low behavior.
void setBoardColor(bool redOn, bool greenOn, bool blueOn) {
  digitalWrite(LED_RED,   redOn   ? LOW : HIGH);
  digitalWrite(LED_GREEN, greenOn ? LOW : HIGH);
  digitalWrite(LED_BLUE,  blueOn  ? LOW : HIGH);
}

// Blue means the Nano is advertising and waiting for a BLE connection.
void showAdvertisingColor() {
  setBoardColor(false, false, true);
}

// Green means a BLE client is connected.
void showConnectedColor() {
  setBoardColor(false, true, false);
}

// Red is shown briefly after a BLE client disconnects.
void showDisconnectedColor() {
  setBoardColor(true, false, false);
}

// 7. BLUETOOTH STATUS MESSAGE FUNCTION

// Send a text message to the Status characteristic.
//
// The status characteristic supports READ and NOTIFY. A BLE client can read
// the current value, or subscribe to notifications to receive updates.
void sendStatusText(const char* message) {
  if (statusCharacteristic == nullptr) {
    return;
  }

  statusCharacteristic->setValue(message);

  if (deviceConnected) {
    statusCharacteristic->notify();
  }

  Serial.print("[BLE STATUS] ");
  Serial.println(message);
}

// Format a compact status string containing the display state and settings.
// Keep this message short because BLE characteristic values have a finite
// maximum length.
void notifyDisplayStatus(const char* state) {
  char message[80];

  snprintf(
    message,
    sizeof(message),
    "%s,R%lu,L%u,B%u,D%u",
    state,
    (unsigned long)getRPM(),
    ledCount,
    BLADE_COUNT,
    DEAD_SPACE_LEDS
  );

  sendStatusText(message);
}

// 8. BLE SERVER CALLBACKS

// These callbacks are called by the BLE library when a client connects or
// disconnects. They also change the onboard RGB LED.
class HoloFanServerCallbacks : public BLEServerCallbacks {

  void onConnect(BLEServer* server) override {
    deviceConnected = true;

    // Green tells us a computer/phone connected successfully.
    showConnectedColor();

    Serial.println();
    Serial.println("====================================");
    Serial.println("BLUETOOTH CLIENT CONNECTED");
    Serial.println("RGB STATUS LED: GREEN");
    Serial.println("====================================");

    sendStatusText("CONNECTED - Holo-Fan ready");
  }

  void onDisconnect(BLEServer* server) override {
    deviceConnected = false;

    // Brief red indication makes a disconnect visible.
    showDisconnectedColor();

    Serial.println("BLUETOOTH CLIENT DISCONNECTED");
    Serial.println("RGB STATUS LED: RED");

    delay(250);

    // Restart advertising so the desktop/phone can connect again.
    BLEDevice::startAdvertising();

    // Blue means advertising has resumed.
    showAdvertisingColor();

    Serial.println("Advertising again as Holo-Fan");
    Serial.println("RGB STATUS LED: BLUE");
  }
};

// 9. ROTATION SENSOR AND RPM FUNCTIONS

// This interrupt runs on the KY-024 digital output's falling edge.
// Position the KY-024 so the magnet triggers it once per revolution.
//
// IMPORTANT: rejected noise pulses do NOT replace lastIndexMicros.
// Otherwise a noisy sensor could corrupt the RPM and angular position.
void IRAM_ATTR indexISR() {
  const uint32_t now = micros();
  const uint32_t previous = lastIndexMicros;

  // The first detection establishes the angular zero reference.
  if (previous == 0) {
    lastIndexMicros = now;
    indexPulseSeen = true;
    return;
  }

  const uint32_t delta = now - previous;

  // Accept only plausible once-per-revolution pulses.
  if (delta >= MIN_INDEX_INTERVAL_US) {
    revolutionMicros = delta;
    lastIndexMicros = now;
    indexPulseSeen = true;
  }
}

// Calculate RPM from the time between index pulses.
uint32_t getRPM() {
  uint32_t revUs;
  uint32_t lastPulse;

  // Copy multi-byte values safely while the interrupt is paused.
  noInterrupts();
  revUs = revolutionMicros;
  lastPulse = lastIndexMicros;
  interrupts();

  if (revUs == 0 || lastPulse == 0) {
    return 0;
  }

  // If no index pulse has arrived for more than two revolutions,
  // assume the fan has stopped or the sensor is not detecting it.
  if ((uint32_t)(micros() - lastPulse) > revUs * 2UL) {
    return 0;
  }

  return 60000000UL / revUs;
}

// 10. LED STRIP HELPER FUNCTIONS

// Turn off all LEDs on all four blades.
void clearBlades() {
  for (uint8_t blade = 0; blade < BLADE_COUNT; ++blade) {
    blades[blade]->clear();
    blades[blade]->show();
  }
}

// Convert one hexadecimal character into a number from 0 to 15.
// Return -1 if the character is not a valid hexadecimal digit.
int hexNibble(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return 10 + c - 'a';
  if (c >= 'A' && c <= 'F') return 10 + c - 'A';
  return -1;
}

// Convert a color such as "#12ABEF" or "12ABEF" into red, green, blue bytes.
bool parseColor(const char* token, uint8_t& red, uint8_t& green, uint8_t& blue) {
  if (*token == '#') {
    ++token;
  }

  // This firmware expects exactly six hexadecimal digits per color.
  if (strlen(token) != 6) {
    return false;
  }

  int digits[6];

  for (uint8_t i = 0; i < 6; ++i) {
    digits[i] = hexNibble(token[i]);

    if (digits[i] < 0) {
      return false;
    }
  }

  red   = (uint8_t)((digits[0] << 4) | digits[1]);
  green = (uint8_t)((digits[2] << 4) | digits[3]);
  blue  = (uint8_t)((digits[4] << 4) | digits[5]);

  return true;
}

// Remove spaces/tabs at the beginning and spaces/tabs/carriage returns
// at the end of a line.
void trimLine(char* text) {
  size_t start = 0;

  while (text[start] == ' ' || text[start] == '\t') {
    ++start;
  }

  if (start > 0) {
    memmove(text, text + start, strlen(text + start) + 1);
  }

  size_t length = strlen(text);

  while (length > 0 &&
         (text[length - 1] == ' ' ||
          text[length - 1] == '\t' ||
          text[length - 1] == '\r')) {
    text[--length] = '\0';
  }
}

// 11. IMAGE.TXT PARSER

// Parse one vector line.
//
// A vector line must contain exactly 25 comma-separated colors.
// Each color must be six hexadecimal digits, optionally preceded by '#'.
bool parseVectorLine(char* text) {
  if (fileRowsParsed >= fileExpectedVectors) {
    return false;
  }

  uint16_t colorCount = 0;
  char* token = text;

  while (true) {
    // Split at the next comma.
    char* comma = strchr(token, ',');

    if (comma != nullptr) {
      *comma = '\0';
    }

    trimLine(token);

    uint8_t red, green, blue;

    if (!parseColor(token, red, green, blue)) {
      return false;
    }

    if (colorCount >= MAX_LEDS) {
      return false;
    }

    // Calculate where this color belongs in the receiving image buffer.
    const uint32_t offset =
      ((uint32_t)fileRowsParsed * MAX_LEDS + colorCount) * 3UL;

    receivingFrame[offset]     = red;
    receivingFrame[offset + 1] = green;
    receivingFrame[offset + 2] = blue;

    ++colorCount;

    // No comma means this was the final color on the line.
    if (comma == nullptr) {
      break;
    }

    token = comma + 1;

    // A comma followed by nothing is an invalid empty color.
    if (*token == '\0') {
      return false;
    }
  }

  // Every vector must have exactly 25 colors.
  if (colorCount != MAX_LEDS) {
    return false;
  }

  if (fileRowsParsed == 0) {
    ledCount = colorCount;
  } else if (colorCount != ledCount) {
    return false;
  }

  ++fileRowsParsed;
  return true;
}

// Process one complete line from image.txt.
bool processFileLine(char* text) {
  trimLine(text);

  // Ignore empty lines.
  if (text[0] == '\0') {
    return true;
  }

  // The first non-empty line contains the number of vectors.
  if (fileLineNumber == 0) {
    char* endPointer = nullptr;
    long value = strtol(text, &endPointer, 10);

    while (endPointer != nullptr &&
           (*endPointer == ' ' || *endPointer == '\t')) {
      ++endPointer;
    }

    // Reject invalid numbers and counts outside the supported range.
    if (endPointer == text ||
        (endPointer != nullptr && *endPointer != '\0') ||
        value < 1 ||
        value > MAX_VECTORS) {
      return false;
    }

    fileExpectedVectors = (uint16_t)value;
    ++fileLineNumber;
    return true;
  }

  // Every later non-empty line is one vector.
  if (!parseVectorLine(text)) {
    return false;
  }

  ++fileLineNumber;
  return true;
}

// Record an upload error and stop receiving the current file.
void failFile(const char* reason) {
  fileFailed = true;
  receivingFile = false;

  strncpy(lastError, reason, sizeof(lastError) - 1);
  lastError[sizeof(lastError) - 1] = '\0';

  sendStatusText(lastError);

  Serial.print("Image upload failed: ");
  Serial.println(lastError);
}

// Add one received byte to the line buffer.
// A newline means the current line is complete and can be parsed.
void acceptTextByte(uint8_t value) {
  if (!receivingFile || fileFailed) {
    return;
  }

  // Ignore carriage returns; newline is used to end a line.
  if (value == '\r') {
    return;
  }

  if (value == '\n') {
    lineBuffer[lineLength] = '\0';

    bool lineIsValid = processFileLine(lineBuffer);

    lineLength = 0;

    if (!lineIsValid) {
      failFile("ERR_BAD_LINE");
    }

    return;
  }

  // Prevent writing past the end of lineBuffer.
  if (lineLength >= MAX_LINE_CHARS) {
    failFile("ERR_LINE_LONG");
    return;
  }

  lineBuffer[lineLength++] = (char)value;
}

// Prepare the receiving buffer for a new image upload.
void beginFile() {
  // Stop displaying while the new image is being uploaded.
  displayRunning = false;

  receivingFile = true;
  fileFailed = false;

  lastError[0] = '\0';

  fileExpectedVectors = 0;
  fileRowsParsed = 0;
  fileLineNumber = 0;
  lineLength = 0;
  ledCount = 0;

  // Clear only the receiving buffer. The active display buffer is untouched.
  memset(receivingFrame, 0, MAX_FRAME_BYTES);

  sendStatusText("FILE_READY");
  Serial.println("Ready to receive image.txt");
}

// Finish and validate an image upload.
void endFile() {
  if (!receivingFile && fileFailed) {
    sendStatusText(lastError[0] ? lastError : "ERR_FILE");
    return;
  }

  if (!receivingFile) {
    sendStatusText("ERR_NO_FILE");
    return;
  }

  // Process the last line if the file did not end with a newline character.
  if (lineLength > 0) {
    lineBuffer[lineLength] = '\0';

    if (!processFileLine(lineBuffer)) {
      failFile("ERR_BAD_LINE");
      return;
    }

    lineLength = 0;
  }

  receivingFile = false;

  // Check that the received file contains the expected number of vectors.
  if (fileExpectedVectors == 0 ||
      fileRowsParsed != fileExpectedVectors ||
      ledCount != MAX_LEDS) {
    failFile("ERR_ROW_COUNT");
    return;
  }

  // The file is valid. Swap the buffers so the new image becomes active.
  vectorCount = fileExpectedVectors;

  uint8_t* oldActiveFrame = activeFrame;
  activeFrame = receivingFrame;
  receivingFrame = oldActiveFrame;

  lastVector = 0;

  notifyDisplayStatus("FILE_OK");

  Serial.print("Image upload complete. Vectors: ");
  Serial.println(vectorCount);
}

// 12. CONTROL COMMAND HANDLER

// Run a command received through the BLE Control characteristic.
void handleControlCommand(const char* command) {
  Serial.print("[CONTROL COMMAND] ");
  Serial.println(command);

  if (strcmp(command, "STATUS") == 0) {
    if (receivingFile) {
      notifyDisplayStatus("RECEIVING");
    } else if (displayRunning) {
      notifyDisplayStatus("RUNNING");
    } else {
      notifyDisplayStatus("IDLE");
    }
  }

  else if (strcmp(command, "BEGIN_FILE") == 0) {
    beginFile();
  }

  else if (strcmp(command, "END_FILE") == 0) {
    endFile();
  }

  else if (strcmp(command, "STOP") == 0) {
    displayRunning = false;
    clearBlades();
    notifyDisplayStatus("STOPPED");
    Serial.println("POV display stopped.");
  }

  else if (strcmp(command, "START") == 0) {
    // Do not start unless a valid image has been uploaded.
    if (vectorCount > 0 &&
        ledCount == MAX_LEDS &&
        !receivingFile &&
        !fileFailed) {
      displayRunning = true;
      lastRenderMicros = micros();

      // Force the first phase-derived vector to be rendered.
      // The actual angular reference comes from the next KY-024 pulse.
      lastVector = UINT16_MAX;

      notifyDisplayStatus("RUNNING");
      Serial.println("POV display started.");
    } else {
      sendStatusText("ERR_NOT_READY");
      Serial.println("Cannot start: no valid image is loaded.");
    }
  }

  else {
    sendStatusText("ERR_COMMAND");
    Serial.println("Unknown control command.");
  }
}

// 13. BLE CHARACTERISTIC CALLBACKS

// Called when the computer/phone writes to the Control characteristic.
class ControlWriteCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* characteristic) override {
    std::string received = characteristic->getValue();

    if (received.length() == 0 || received.length() >= 32) {
      sendStatusText("ERR_COMMAND_LENGTH");
      return;
    }

    char command[32];

    memcpy(command, received.data(), received.length());
    command[received.length()] = '\0';

    // Remove trailing whitespace from the command.
    size_t length = strlen(command);

    while (length > 0 &&
           (command[length - 1] == '\r' ||
            command[length - 1] == '\n' ||
            command[length - 1] == ' ')) {
      command[--length] = '\0';
    }

    handleControlCommand(command);
  }
};

// Called when the computer/phone writes image file bytes to the Data
// characteristic. One BLE write is one chunk of the text file.
class DataWriteCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic* characteristic) override {
    if (!receivingFile || fileFailed) {
      sendStatusText("ERR_NOT_RECEIVING");
      return;
    }

    std::string received = characteristic->getValue();

    if (received.length() == 0 || received.length() > 20) {
      sendStatusText("ERR_CHUNK_SIZE");
      return;
    }

    // Feed each byte into the text-file parser.
    for (size_t i = 0; i < received.length(); ++i) {
      acceptTextByte((uint8_t)received[i]);

      // Stop processing if a malformed line was detected.
      if (fileFailed) {
        break;
      }
    }
  }
};

// 14. POV RENDERING

// Display one angular vector on all four blades.
//
// The existing design divides the vector count into four sections so each
// blade displays a different quarter of the image at the same instant.
//
// NOTE: vectorCount should ideally be divisible by four for equal sections.
// The existing modulo-based behavior is retained from the supplied sketch.
//
// The two innermost LEDs on every blade are forced off to create dead space.
void renderVector(uint16_t vectorIndex) {
  if (vectorCount == 0 || ledCount == 0) {
    return;
  }

  const uint16_t bladeOffset = vectorCount / BLADE_COUNT;

  for (uint8_t blade = 0; blade < BLADE_COUNT; ++blade) {
    const uint16_t sourceVector =
      (vectorIndex + blade * bladeOffset) % vectorCount;

    for (uint16_t led = 0; led < MAX_LEDS; ++led) {
      uint8_t red = 0;
      uint8_t green = 0;
      uint8_t blue = 0;

      // Keep the first two LEDs dark.
      if (led >= DEAD_SPACE_LEDS) {
        const uint32_t index =
          ((uint32_t)sourceVector * MAX_LEDS + led) * 3UL;

        red   = activeFrame[index];
        green = activeFrame[index + 1];
        blue  = activeFrame[index + 2];
      }

      blades[blade]->setPixelColor(
        led,
        blades[blade]->Color(red, green, blue)
      );
    }

    // Send the prepared color data to this blade's LED strip.
    // This is done one strip at a time in the supplied design.
    blades[blade]->show();
  }
}

// 15. BLUETOOTH INITIALIZATION

// Create the BLE server, service, and characteristics, then begin advertising.
void setupBluetooth() {
  Serial.println("Starting Bluetooth");

  BLEDevice::init(DEVICE_NAME);

  // Create the BLE server and install connection callbacks.
  bleServer = BLEDevice::createServer();
  bleServer->setCallbacks(new HoloFanServerCallbacks());

  // Create the service that groups all Holo-Fan BLE characteristics.
  BLEService* service = bleServer->createService(SERVICE_UUID);

  // Control characteristic:
  // The desktop writes short commands such as START, STOP, and BEGIN_FILE.
  controlCharacteristic = service->createCharacteristic(
    CONTROL_UUID,
    BLECharacteristic::PROPERTY_READ |
    BLECharacteristic::PROPERTY_WRITE
  );

  controlCharacteristic->setValue("Ready");
  controlCharacteristic->setCallbacks(new ControlWriteCallbacks());

  // Data characteristic:
  // The desktop writes image.txt data in chunks of up to 20 bytes.
  dataCharacteristic = service->createCharacteristic(
    DATA_UUID,
    BLECharacteristic::PROPERTY_WRITE |
    BLECharacteristic::PROPERTY_WRITE_NR
  );

  dataCharacteristic->setCallbacks(new DataWriteCallbacks());

  // Status characteristic:
  // The desktop can read this value and subscribe to notifications.
  statusCharacteristic = service->createCharacteristic(
    STATUS_UUID,
    BLECharacteristic::PROPERTY_READ |
    BLECharacteristic::PROPERTY_NOTIFY
  );

  // BLE2902 descriptor enables notification subscription in common BLE apps.
  statusCharacteristic->addDescriptor(new BLE2902());
  statusCharacteristic->setValue("READY - Holo-Fan");

  // Start the service before advertising it.
  service->start();

  // Configure BLE advertising so scanners can find Holo-Fan.
  BLEAdvertising* advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->setScanResponse(true);

  BLEDevice::startAdvertising();

  // Blue indicates that the device is ready and waiting for a client.
  showAdvertisingColor();

  Serial.println("BLE READY");
  Serial.print("Device name: ");
  Serial.println(DEVICE_NAME);
  Serial.println("RGB LED BLUE = waiting for connection");
}

// 16. ARDUINO SETUP

void setup() {
  // Start serial communication for debugging.
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("HOLO-FAN");

  // Initialize the onboard RGB LED

  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);

  // Turn all RGB channels off before BLE starts
  setBoardColor(false, false, false);

  // Initialize the KY-024 Hall-effect sensor.
  // Connect VCC to 3V3, GND to GND, and DO to D6.
  // INPUT_PULLUP is used because many KY-024 comparator outputs are
  // open-collector/open-drain style. If your module's output is active
  // HIGH instead of active LOW, change FALLING to RISING below.
  pinMode(INDEX_PIN, INPUT_PULLUP);

  // One falling edge should occur each time the magnet passes the sensor.
  attachInterrupt(
    digitalPinToInterrupt(INDEX_PIN),
    indexISR,
    FALLING
  );

  // Initialize the four NeoPixel blade strips

  Serial.println("Initializing LED blades...");

  for (uint8_t blade = 0; blade < BLADE_COUNT; ++blade) {
    blades[blade] = new Adafruit_NeoPixel(
      MAX_LEDS,
      BLADE_PINS[blade],
      NEO_GRB + NEO_KHZ800
    );

    blades[blade]->begin();
    blades[blade]->setBrightness(LED_BRIGHTNESS);
    blades[blade]->clear();
    blades[blade]->show();

    Serial.print("Blade ");
    Serial.print(blade + 1);
    Serial.print(" initialized on pin D");
    Serial.println(BLADE_PINS[blade]);
  }

  // Initialize Bluetooth

  setupBluetooth();

  Serial.println("-----------------------------------------------");
  Serial.println("Setup complete.");
  Serial.println("Blue RGB LED: waiting for Bluetooth connection.");
  Serial.println("Send STATUS to check the device.");
  Serial.println("-----------------------------------------------");
}

// 17. ARDUINO MAIN LOOP

void loop() {
  // The ESP32 BLE stack handles BLE callbacks in the background.
  // A short delay allows normal background tasks to run.
  delay(1);

  // POV image rendering synchronized to the KY-024 index pulse.
  //
  // The magnet detection is the angular zero reference for each revolution.
  // Rather than advancing vectors using a free-running timer, calculate the
  // fan's current phase from (current time - last index pulse). This allows
  // the image timing to follow changes in RPM.
  if (displayRunning && vectorCount > 0 && ledCount > 0) {
    uint32_t periodSnapshot;
    uint32_t indexSnapshot;

    // Copy ISR-updated 32-bit values atomically.
    noInterrupts();
    periodSnapshot = revolutionMicros;
    indexSnapshot = lastIndexMicros;
    interrupts();

    const uint32_t now = micros();

    // Wait until the first magnet detection establishes the index position.
    if (indexSnapshot != 0 && periodSnapshot > 0) {
      const uint32_t sinceIndex = now - indexSnapshot;

      // If the expected pulse has been missing for too long, stop updating
      // the image rather than free-running with an unreliable phase.
      if (sinceIndex <= periodSnapshot * 2UL) {
        const uint32_t phaseMicros = sinceIndex % periodSnapshot;

        // Map the current rotational phase to an image vector.
        uint16_t targetVector =
          (uint16_t)(((uint64_t)phaseMicros * vectorCount) /
                     periodSnapshot);

        if (targetVector >= vectorCount) {
          targetVector = vectorCount - 1;
        }

        // Apply a user-adjustable angular alignment correction.
        int32_t adjustedVector =
          (int32_t)targetVector + INDEX_VECTOR_OFFSET;

        while (adjustedVector < 0) {
          adjustedVector += vectorCount;
        }
        adjustedVector %= vectorCount;
        targetVector = (uint16_t)adjustedVector;

        // Render only when the phase enters a different vector.
        if (targetVector != lastVector) {
          renderVector(targetVector);
          lastVector = targetVector;
        }
      }
    }
  } else {
    // When stopped, do not retain a stale vector selection.
    lastRenderMicros = micros();
    lastVector = UINT16_MAX;
  }

  // Periodic BLE status updates

  if (deviceConnected && millis() - lastStatusMs >= 1000) {
    lastStatusMs = millis();

    if (receivingFile) {
      notifyDisplayStatus("RECEIVING");
    } else if (displayRunning) {
      notifyDisplayStatus("RUNNING");
    } else if (vectorCount > 0) {
      notifyDisplayStatus("IDLE");
    } else {
      notifyDisplayStatus("READY");
    }
  }
}
