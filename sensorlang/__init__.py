"""
SensorLang: Compilador para ESP32 con soporte de WiFi, OTA y Telemetría.
"""

from .lexer import lexer, Token, LexerError
from .parser import parsear, Parser, ParserError
from .generador import generar_cpp
from .esp32_tools import (
    FQBN_ESP32,
    detectar_info_puertos_usb,
    detectar_puerto_esp32_automatico,
    listar_puertos_usb,
    compilar_sensorlang_a_cpp,
    compilar_con_arduino_cli,
    subir_firmware_wifi,
    subir_firmware_usb,
)

__version__ = "2.0.0"
__all__ = [
    "lexer",
    "Token",
    "LexerError",
    "parsear",
    "Parser",
    "ParserError",
    "generar_cpp",
    "FQBN_ESP32",
    "detectar_info_puertos_usb",
    "detectar_puerto_esp32_automatico",
    "listar_puertos_usb",
    "compilar_sensorlang_a_cpp",
    "compilar_con_arduino_cli",
    "subir_firmware_wifi",
    "subir_firmware_usb",
]
