class LteCellType:
    SERVING = "serving"
    NEIGHBOR = "neighbor"
    CHOICES = [
        (SERVING, "Serving"),
        (NEIGHBOR, "Neighbor"),
    ]


class SourceDevice:
    UNKNOWN = "unknown"
    MININO = "minino"
    FLIPPER_DEV_BOARD = "flipper dev board"
    FLIPPER_DEV_BOARD_PRO = "flipper dev board pro"
    MARAUDER_V4 = "marauder v4"
    MARAUDER_V6 = "marauder v6"
    FLIPPER_BFFB = "flipper bffb"
    MARAUDER_ESP32 = "marauder esp32"
    RF_CUSTOM_FIRMWARE_WIFI = "rf custom firmware wifi"
    RF_CUSTOM_FIRMWARE_LTE = "rf custom firmware lte"
    KISMET = "kismet"
    WARDRIVER_UK = "wardriver uk"
    KIISU = "kiisu board"
    PWNTERREY_MARAUDER = "pwnterrey marauder"
    WIGGLE_MOBILE_WIFI = "wiggle mobile wifi"
    OTHER = "other"
    WIFI_BLE_ANDROID="wifi_ble_android"
    LTE_ANDROID="lte_android"

    CHOICES = [
        (UNKNOWN, UNKNOWN),
        (MININO, MININO),
        (FLIPPER_DEV_BOARD, FLIPPER_DEV_BOARD),
        (FLIPPER_DEV_BOARD_PRO, FLIPPER_DEV_BOARD_PRO),
        (MARAUDER_V4, MARAUDER_V4),
        (MARAUDER_V6, MARAUDER_V6),
        (FLIPPER_BFFB, FLIPPER_BFFB),
        (MARAUDER_ESP32, MARAUDER_ESP32),
        (RF_CUSTOM_FIRMWARE_WIFI, RF_CUSTOM_FIRMWARE_WIFI),
        (RF_CUSTOM_FIRMWARE_LTE, RF_CUSTOM_FIRMWARE_LTE),
        (KISMET, KISMET),
        (WARDRIVER_UK, WARDRIVER_UK),
        (KIISU, KIISU),
        (PWNTERREY_MARAUDER, PWNTERREY_MARAUDER),
        (WIGGLE_MOBILE_WIFI, WIGGLE_MOBILE_WIFI),
        (WIFI_BLE_ANDROID, WIFI_BLE_ANDROID),
        (LTE_ANDROID, LTE_ANDROID),
        (OTHER, OTHER),
    ]

    AVAILABLE_CHOICES = [
        (FLIPPER_DEV_BOARD, FLIPPER_DEV_BOARD),
        (FLIPPER_DEV_BOARD_PRO, FLIPPER_DEV_BOARD_PRO),
        (PWNTERREY_MARAUDER, PWNTERREY_MARAUDER),
        (WIGGLE_MOBILE_WIFI, WIGGLE_MOBILE_WIFI),
        (WIFI_BLE_ANDROID, WIFI_BLE_ANDROID),
        (LTE_ANDROID, LTE_ANDROID),
        (MININO, MININO),
        (MARAUDER_V4, MARAUDER_V4),
        (MARAUDER_V6, MARAUDER_V6),
        (FLIPPER_BFFB, FLIPPER_BFFB),
        (MARAUDER_ESP32, MARAUDER_ESP32),
        (RF_CUSTOM_FIRMWARE_WIFI, RF_CUSTOM_FIRMWARE_WIFI),
        (RF_CUSTOM_FIRMWARE_LTE, RF_CUSTOM_FIRMWARE_LTE),
        (KISMET, KISMET),
        (WARDRIVER_UK, WARDRIVER_UK),
        (KIISU, KIISU),
    ]
