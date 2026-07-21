import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..permissions import IsInventoryUser


IBGE_STATES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome"
IBGE_CITIES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome"
CACHE_MAX_AGE = timedelta(days=30)


def _cache_path():
    path = Path(settings.DATA_DIR) / "localidades_ibge.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read_cache():
    path = _cache_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_cache(payload):
    path = _cache_path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _municipality_uf(item):
    microrregion = item.get("microrregiao") or {}
    mesorregion = microrregion.get("mesorregiao") or {}
    state = mesorregion.get("UF") or {}
    if state.get("sigla"):
        return state.get("sigla")

    immediate_region = item.get("regiao-imediata") or {}
    intermediate_region = immediate_region.get("regiao-intermediaria") or {}
    state = intermediate_region.get("UF") or {}
    return state.get("sigla") or ""


def _fetch_ibge_data():
    states_response = requests.get(IBGE_STATES_URL, timeout=25)
    states_response.raise_for_status()
    cities_response = requests.get(IBGE_CITIES_URL, timeout=40)
    cities_response.raise_for_status()

    states = [
        {
            "id": item.get("id"),
            "name": item.get("nome") or "",
            "code": item.get("sigla") or "",
        }
        for item in states_response.json()
        if item.get("sigla")
    ]
    cities = [
        {
            "id": item.get("id"),
            "name": item.get("nome") or "",
            "state": _municipality_uf(item),
        }
        for item in cities_response.json()
        if item.get("nome")
    ]
    states.sort(key=lambda item: item["name"])
    cities.sort(key=lambda item: (item["name"], item["state"]))

    payload = {
        "updated_at": timezone.localtime().isoformat(),
        "source": "IBGE",
        "states": states,
        "cities": cities,
    }
    _write_cache(payload)
    return payload


def _cache_is_fresh(payload):
    updated_at = payload.get("updated_at") if payload else None
    if not updated_at:
        return False
    try:
        updated = datetime.fromisoformat(updated_at)
        if timezone.is_naive(updated):
            updated = timezone.make_aware(updated)
    except (TypeError, ValueError):
        return False
    return timezone.now() - updated <= CACHE_MAX_AGE


def _load_localities(force=False):
    cached = _read_cache()
    if cached and not force and _cache_is_fresh(cached):
        return cached, False

    try:
        return _fetch_ibge_data(), False
    except (requests.RequestException, ValueError, TypeError, OSError):
        if cached:
            return cached, True
        raise


@api_view(["GET"])
@permission_classes([IsInventoryUser])
def brazil_localities(request):
    force = str(request.GET.get("refresh") or "").lower() in {"1", "true", "yes"}
    try:
        payload, stale = _load_localities(force=force)
    except (requests.RequestException, ValueError, TypeError, OSError):
        return Response(
            {
                "detail": "Não foi possível carregar a lista de cidades do IBGE. Verifique a conexão e tente novamente.",
                "states": [],
                "cities": [],
            },
            status=503,
        )

    state = str(request.GET.get("state") or "").upper().strip()
    cities = payload.get("cities") or []
    if state:
        cities = [city for city in cities if city.get("state") == state]

    return Response(
        {
            "source": payload.get("source") or "IBGE",
            "updated_at": payload.get("updated_at"),
            "stale": stale,
            "states": payload.get("states") or [],
            "cities": cities,
        }
    )
