
#include <Adafruit_NeoPixel.h>

// ==========================================
// HOLO-FAN CONFIGURATION
// ==========================================

// Four independent blade data pins
#define BLADE1_PIN D3
#define BLADE2_PIN D4
#define BLADE3_PIN D5
#define BLADE4_PIN D6

// LED configuration
#define LEDS_PER_BLADE 25
#define BLADE_COUNT 4
#define TOTAL_LEDS 100

// Brightness: 50% (128 out of 255)
#define LED_BRIGHTNESS 45

// ==========================================
// CREATE FOUR INDEPENDENT LED STRIPS
// ==========================================

Adafruit_NeoPixel blade1(
  LEDS_PER_BLADE, BLADE1_PIN, NEO_GRB + NEO_KHZ800
);

Adafruit_NeoPixel blade2(
  LEDS_PER_BLADE, BLADE2_PIN, NEO_GRB + NEO_KHZ800
);

Adafruit_NeoPixel blade3(
  LEDS_PER_BLADE, BLADE3_PIN, NEO_GRB + NEO_KHZ800
);

Adafruit_NeoPixel blade4(
  LEDS_PER_BLADE, BLADE4_PIN, NEO_GRB + NEO_KHZ800
);

// ==========================================
// INITIALIZE ALL BLADES
// ==========================================

void setup() {

  Serial.begin(115200);

  Serial.println();
  Serial.println("==============================");
  Serial.println("       HOLO-FAN TEST");
  Serial.println("==============================");

  // Initialize blade 1
  blade1.begin();
  blade1.setBrightness(LED_BRIGHTNESS);
  blade1.clear();
  blade1.show();

  // Initialize blade 2
  blade2.begin();
  blade2.setBrightness(LED_BRIGHTNESS);
  blade2.clear();
  blade2.show();

  // Initialize blade 3
  blade3.begin();
  blade3.setBrightness(LED_BRIGHTNESS);
  blade3.clear();
  blade3.show();

  // Initialize blade 4
  blade4.begin();
  blade4.setBrightness(LED_BRIGHTNESS);
  blade4.clear();
  blade4.show();

  Serial.println("[SYSTEM] Four blades initialized.");
  Serial.println("[BLADE 1] D3 - 25 LEDs");
  Serial.println("[BLADE 2] D4 - 25 LEDs");
  Serial.println("[BLADE 3] D5 - 25 LEDs");
  Serial.println("[BLADE 4] D6 - 25 LEDs");

  Serial.println("[SYSTEM] Total LEDs: 100");
  Serial.println("[SYSTEM] Brightness: 50%");
  Serial.println("[SYSTEM] Motor: OFF");
  Serial.println("[SYSTEM] Hall sensor: NOT USED");

  Serial.println("==============================");
  Serial.println("[TEST] Starting LED test...");
}

// ==========================================
// UPDATE ALL FOUR BLADES
// ==========================================

void showAll() {
  blade1.show();
  blade2.show();
  blade3.show();
  blade4.show();
}

// ==========================================
// CLEAR ALL FOUR BLADES
// ==========================================

void clearAll() {
  blade1.clear();
  blade2.clear();
  blade3.clear();
  blade4.clear();

  showAll();
}

// ==========================================
// SET SAME COLOR ON ALL BLADES
// ==========================================

void setAllColor(uint32_t color) {

  blade1.fill(color);
  blade2.fill(color);
  blade3.fill(color);
  blade4.fill(color);

  showAll();
}

// ==========================================
// COLOR WIPE TEST
// ==========================================

void colorWipe(uint32_t color, int wait) {

  for (int i = 0; i < LEDS_PER_BLADE; i++) {

    blade1.setPixelColor(i, color);
    blade2.setPixelColor(i, color);
    blade3.setPixelColor(i, color);
    blade4.setPixelColor(i, color);

    showAll();

    delay(wait);
  }
}

// ==========================================
// THEATER CHASE TEST
// ==========================================

void theaterChase(uint32_t color, int wait) {

  for (int a = 0; a < 10; a++) {

    for (int b = 0; b < 3; b++) {

      clearAll();

      for (int c = b; c < LEDS_PER_BLADE; c += 3) {

        blade1.setPixelColor(c, color);
        blade2.setPixelColor(c, color);
        blade3.setPixelColor(c, color);
        blade4.setPixelColor(c, color);
      }

      showAll();

      delay(wait);
    }
  }
}

// ==========================================
// RAINBOW TEST
// ==========================================

void rainbow(int wait) {

  for (long hue = 0; hue < 5L * 65536; hue += 256) {

    for (int i = 0; i < LEDS_PER_BLADE; i++) {

      int pixelHue = hue + (i * 65536L / LEDS_PER_BLADE);

      uint32_t color = Adafruit_NeoPixel::gamma32(
        Adafruit_NeoPixel::ColorHSV(pixelHue)
      );

      blade1.setPixelColor(i, color);
      blade2.setPixelColor(i, color);
      blade3.setPixelColor(i, color);
      blade4.setPixelColor(i, color);
    }

    showAll();

    delay(wait);
  }
}

// ==========================================
// RAINBOW THEATER CHASE
// ==========================================

void theaterChaseRainbow(int wait) {

  int firstPixelHue = 0;

  for (int a = 0; a < 30; a++) {

    for (int b = 0; b < 3; b++) {

      clearAll();

      for (int c = b; c < LEDS_PER_BLADE; c += 3) {

        int hue = firstPixelHue +
                  c * 65536L / LEDS_PER_BLADE;

        uint32_t color = Adafruit_NeoPixel::gamma32(
          Adafruit_NeoPixel::ColorHSV(hue)
        );

        blade1.setPixelColor(c, color);
        blade2.setPixelColor(c, color);
        blade3.setPixelColor(c, color);
        blade4.setPixelColor(c, color);
      }

      showAll();

      delay(wait);

      firstPixelHue += 65536 / 90;
    }
  }
}

// ==========================================
// MAIN LOOP
// ==========================================

void loop() {
  theaterChase(blade1.Color(127, 0, 0), 50);
}
