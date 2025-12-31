"""
Middleware pro cachování 404 odpovědí na krátkou dobu
Zabraňuje opakovaným requestům na stejný neexistující soubor
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import status


class NotFoundCacheMiddleware(BaseHTTPMiddleware):
    """Middleware pro cachování 404 odpovědí na /api/audio/* endpointy"""

    def __init__(self, app, cache_ttl: float = 5.0):
        super().__init__(app)
        self.cache_ttl = cache_ttl  # Cache TTL v sekundách
        self._cache = {}  # {path: (timestamp, status_code)}

    async def dispatch(self, request: Request, call_next):
        # Pouze pro /api/audio/* endpointy
        if not request.url.path.startswith("/api/audio/"):
            return await call_next(request)

        # Zkontrolovat cache
        cache_key = request.url.path
        current_time = time.time()

        if cache_key in self._cache:
            cached_time, cached_status = self._cache[cache_key]
            # Pokud je cache stále platná a je to 404, vrátit cached odpověď
            if current_time - cached_time < self.cache_ttl and cached_status == 404:
                # Vyčistit staré záznamy (starší než 1 minutu)
                if len(self._cache) > 1000:
                    cutoff_time = current_time - 60
                    self._cache = {
                        k: v for k, v in self._cache.items()
                        if current_time - v[0] < cutoff_time
                    }

                # Vrátit 404 odpověď bez volání endpointu
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=404,
                    content={"detail": "Soubor nebyl nalezen"},
                    headers={
                        "X-Cached-404": "true",
                        "Cache-Control": f"max-age={int(self.cache_ttl)}",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET,OPTIONS",
                        "Access-Control-Allow-Headers": "*",
                    }
                )

        # Zavolat endpoint
        response = await call_next(request)

        # Pokud je to 404, uložit do cache
        if response.status_code == 404:
            self._cache[cache_key] = (current_time, 404)

        return response

