#!/usr/bin/env python3
"""
Test script pro ověření kódování českých znaků v logování
"""
import sys
import logging

# Nastavení loggeru s UTF-8 podporou
logger = logging.getLogger(__name__)

# Vytvoříme custom StreamHandler pro konzoli s error handling
class ConsoleHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        super().__init__(stream)
        # Nastavíme encoding pro Windows konzoli
        if hasattr(self.stream, 'reconfigure'):
            try:
                self.stream.reconfigure(encoding='cp1252', errors='replace')
            except Exception:
                pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        ConsoleHandler(sys.stdout),
        logging.FileHandler('test_encoding.log', encoding='utf-8')
    ]
)

# Test českých znaků
logger.info("Test českých znaků: Automatická detekce GPU dostupné, používá se CUDA")
logger.info("Čeština funguje správně: žluťoučký kůň úpěl ďábelské ódy")
logger.warning("Varování s diakritikou: Příliš mnoho znaků!")
logger.error("Chyba s českými znaky: Špatné kódování!")

print("Hotovo - podívejte se na konzoli a do souboru test_encoding.log")
