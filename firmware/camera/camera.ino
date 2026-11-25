#include "esp_camera.h"
#include "esp_http_server.h"
#include <WiFi.h>

// XIAO ESP32S3 Sense. Board: "XIAO_ESP32S3", PSRAM: "OPI PSRAM".
// Makes its own network; join it on the phone and open http://192.168.4.1
const char *SSID = "armtank-cam";
const char *PASS = "CHANGE_ME";  // set your own (8+ characters) before flashing

static esp_err_t stream(httpd_req_t *req) {
  httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=f");
  char head[64];
  while (true) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) return ESP_FAIL;
    int n = snprintf(head, sizeof(head), "\r\n--f\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len);
    esp_err_t r = httpd_resp_send_chunk(req, head, n);
    if (r == ESP_OK) r = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    if (r != ESP_OK) return r;
  }
}

static esp_err_t page(httpd_req_t *req) {
  const char *html = "<html><body style='margin:0;background:#000'>"
                     "<img src='/stream' style='width:100vw;height:100vh;object-fit:contain'></body></html>";
  return httpd_resp_send(req, html, HTTPD_RESP_USE_STRLEN);
}

void setup() {
  camera_config_t c = {};
  c.pin_pwdn = -1;
  c.pin_reset = -1;
  c.pin_xclk = 10;
  c.pin_sccb_sda = 40;
  c.pin_sccb_scl = 39;
  c.pin_d7 = 48; c.pin_d6 = 11; c.pin_d5 = 12; c.pin_d4 = 14;
  c.pin_d3 = 16; c.pin_d2 = 18; c.pin_d1 = 17; c.pin_d0 = 15;
  c.pin_vsync = 38;
  c.pin_href = 47;
  c.pin_pclk = 13;
  c.xclk_freq_hz = 20000000;
  c.ledc_timer = LEDC_TIMER_0;
  c.ledc_channel = LEDC_CHANNEL_0;
  c.pixel_format = PIXFORMAT_JPEG;
  // VGA at q12 keeps frames small enough to stay smooth at the edge of range
  c.frame_size = FRAMESIZE_VGA;
  c.jpeg_quality = 12;
  c.fb_count = 2;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  esp_camera_init(&c);

  WiFi.softAP(SSID, PASS);
  WiFi.setTxPower(WIFI_POWER_19_5dBm);

  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  httpd_handle_t srv;
  httpd_start(&srv, &cfg);
  httpd_uri_t a = {"/", HTTP_GET, page, nullptr};
  httpd_uri_t b = {"/stream", HTTP_GET, stream, nullptr};
  httpd_register_uri_handler(srv, &a);
  httpd_register_uri_handler(srv, &b);
}

void loop() {
  delay(1000);
}
