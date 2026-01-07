"""
Applio Subprocess Manager
Spravuje Applio jako subprocess pro voice conversion a TTS
"""

import asyncio
import subprocess
import signal
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

try:
    from colorama import Fore, Style

    COLOR_OK = Fore.GREEN
    COLOR_WARN = Fore.YELLOW
    COLOR_ERROR = Fore.RED
    COLOR_INFO = Fore.CYAN
    COLOR_RESET = Style.RESET_ALL
except ImportError:
    COLOR_OK = COLOR_WARN = COLOR_ERROR = COLOR_INFO = COLOR_RESET = ""

try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    logger.warning("aiohttp not installed, health checks will be limited")


class ApplioSubprocessManager:
    """Správce Applio subprocess pro voice conversion a TTS"""

    def __init__(self, applio_dir: Path, config: Dict[str, Any]):
        self.applio_dir = applio_dir
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.start_time: Optional[float] = None

    def _get_run_script(self) -> Optional[Path]:
        """Najde run skript pro Applio"""
        scripts = [
            self.applio_dir / "run-applio.bat",
            self.applio_dir / "run-applio.sh",
            self.applio_dir / "applio.bat",
            self.applio_dir / "applio.exe",
        ]
        for script in scripts:
            if script.exists():
                logger.info(f"Nalezen Applio skript: {script}")
                return script
        return None

    async def start(self, timeout: int = 120) -> bool:
        """
        Spustí Applio subprocess

        Args:
            timeout: Maximální doba čekání na start v sekundách

        Returns:
            True pokud se Applio úspěšně spustilo
        """
        if self.is_running:
            logger.warning("Applio již běží")
            return True

        run_script = self._get_run_script()

        if run_script is None:
            logger.error(
                f"{COLOR_ERROR}Applio skript nebyl nalezen!{COLOR_RESET}\n"
                f"Stáhněte Applio z https://applio.org a rozbalte do: {self.applio_dir}"
            )
            return False

        try:
            logger.info(f"{COLOR_INFO}Spouštím Applio...{COLOR_RESET}")

            # Spustíme jako subprocess
            if sys.platform == "win32":
                self.process = subprocess.Popen(
                    [str(run_script)],
                    cwd=str(self.applio_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                self.process = subprocess.Popen(
                    ["bash", str(run_script)],
                    cwd=str(self.applio_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

            self.start_time = time.time()

            # Čekáme na start
            logger.info(
                f"{COLOR_INFO}Čekám na start Applio (max {timeout}s)...{COLOR_RESET}"
            )

            for i in range(timeout):
                if await self.check_health():
                    self.is_running = True
                    logger.info(
                        f"{COLOR_OK}✅ Applio běží na {self.config.get('base_url', 'http://localhost:9874')}{COLOR_RESET}"
                    )
                    return True

                await asyncio.sleep(1)

                if i % 10 == 0 and i > 0:
                    logger.info(f"{COLOR_INFO}Čekám na Applio... {i}s{COLOR_RESET}")

            logger.error(
                f"{COLOR_ERROR}Applio se nepodařilo spustit v čase {timeout}s{COLOR_RESET}"
            )
            self.stop()
            return False

        except Exception as e:
            logger.error(f"{COLOR_ERROR}Chyba při spouštění Applio: {e}{COLOR_RESET}")
            return False

    async def stop(self):
        """Zastaví Applio subprocess"""
        if self.process:
            logger.info(f"{COLOR_INFO}Zastavuji Applio...{COLOR_RESET}")

            try:
                self.process.terminate()

                # Čekáme na ukončení
                for _ in range(10):
                    if self.process.poll() is not None:
                        break
                    await asyncio.sleep(0.5)

                # Force kill pokud stále běží
                if self.process.poll() is None:
                    self.process.kill()

                self.process = None
                self.is_running = False
                logger.info(f"{COLOR_OK}✅ Applio zastaveno{COLOR_RESET}")

            except Exception as e:
                logger.error(
                    f"{COLOR_ERROR}Chyba při zastavování Applio: {e}{COLOR_RESET}"
                )

    async def check_health(self) -> bool:
        """
        Kontrola, zda Applio API běží

        Returns:
            True pokud API odpovídá
        """
        if not HAS_AIOHTTP:
            # Fallback: kontrola procesu
            if self.process and self.process.poll() is None:
                return True
            return False

        try:
            async with aiohttp.ClientSession() as session:
                # Zkusíme health endpoint nebo root
                urls_to_try = [
                    f"{self.config.get('base_url', 'http://localhost:9874')}/docs",
                    f"{self.config.get('base_url', 'http://localhost:9874')}/",
                    f"{self.config.get('base_url', 'http://localhost:9874')}/api/models",
                ]

                for url in urls_to_try:
                    try:
                        async with session.get(
                            url, timeout=aiohttp.ClientTimeout(total=5)
                        ) as resp:
                            if resp.status == 200:
                                return True
                    except:
                        continue

                return False

        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    @property
    def uptime(self) -> Optional[float]:
        """Vrátí uptime Applio v sekundách"""
        if self.start_time is None:
            return None
        return time.time() - self.start_time

    def get_status(self) -> Dict[str, Any]:
        """Vrátí status Applio"""
        return {
            "running": self.is_running,
            "uptime_seconds": self.uptime,
            "process_alive": self.process is not None and self.process.poll() is None,
            "config": {
                "base_url": self.config.get("base_url"),
                "host": self.config.get("host"),
                "port": self.config.get("port"),
            },
        }
