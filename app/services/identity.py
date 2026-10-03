"""Consulta de identidad (DNI) via apisperu.

El token se mantiene en el backend; el frontend nunca lo ve.
"""

import httpx

from app.core.config import settings


class DniLookupError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class DniNotFoundError(DniLookupError):
    pass


def lookup_dni(dni: str) -> dict:
    """Devuelve {'dni', 'full_name'} consultando apisperu."""
    if not settings.apisperu_token:
        raise DniLookupError(
            "No se configuro el token de consulta de DNI (APISPERU_TOKEN).", status_code=503
        )

    url = f"{settings.apisperu_base_url.rstrip('/')}/dni/{dni}"
    params = {"token": settings.apisperu_token}
    try:
        response = httpx.get(url, params=params, timeout=10)
    except httpx.HTTPError as exc:
        raise DniLookupError(f"No se pudo consultar el DNI: {exc}") from exc

    if response.status_code == 404:
        raise DniNotFoundError("DNI no encontrado.", status_code=404)
    if response.status_code >= 400:
        raise DniLookupError(
            "El servicio de consulta de DNI no respondio correctamente.",
            status_code=response.status_code,
        )

    data = response.json()
    nombres = (data.get("nombres") or "").strip()
    apellido_paterno = (data.get("apellidoPaterno") or "").strip()
    apellido_materno = (data.get("apellidoMaterno") or "").strip()
    full_name = " ".join(
        part for part in [nombres, apellido_paterno, apellido_materno] if part
    ).upper()

    if not full_name:
        raise DniNotFoundError("El DNI no devolvio un nombre valido.", status_code=404)

    return {
        "dni": data.get("dni", dni),
        "full_name": full_name,
        "nombres": nombres.upper(),
        "apellido_paterno": apellido_paterno.upper(),
        "apellido_materno": apellido_materno.upper(),
    }
