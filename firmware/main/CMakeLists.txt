idf_component_register(SRCS "app_main.c" "usb_transport.c"
    INCLUDE_DIRS "." REQUIRES g1 esp_timer esp_hw_support esp_system esp_tinyusb)
