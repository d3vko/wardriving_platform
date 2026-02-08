"""
Device-specific file processors. Each module handles one hardware family.
"""
from .marauder import process_file_marauder_esp32
from .minino import process_file_minino
from .rf import process_file_rf

from apps.wardriving import SourceDevice

CHOICES_FUNCTION_PROCESS = {
    SourceDevice.UNKNOWN: None,
    SourceDevice.MININO: process_file_minino,
    SourceDevice.FLIPPER_DEV_BOARD: process_file_marauder_esp32,
    SourceDevice.FLIPPER_DEV_BOARD_PRO: process_file_marauder_esp32,
    SourceDevice.MARAUDER_V4: process_file_marauder_esp32,
    SourceDevice.MARAUDER_V6: process_file_marauder_esp32,
    SourceDevice.FLIPPER_BFFB: process_file_marauder_esp32,
    SourceDevice.MARAUDER_ESP32: process_file_marauder_esp32,
    SourceDevice.RF_CUSTOM_FIRMWARE_WIFI: process_file_rf,
    SourceDevice.RF_CUSTOM_FIRMWARE_LTE: process_file_rf,
    SourceDevice.KISMET: process_file_marauder_esp32,
    SourceDevice.WARDRIVER_UK: process_file_marauder_esp32,
    SourceDevice.KIISU: process_file_marauder_esp32,
    SourceDevice.OTHER: None,
}

__all__ = ["CHOICES_FUNCTION_PROCESS", "process_file_marauder_esp32", "process_file_minino", "process_file_rf"]
