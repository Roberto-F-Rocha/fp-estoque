import json
import os
import re
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


def _bundle_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def _application_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _load_environment_file():
    from dotenv import load_dotenv

    load_dotenv(_application_dir() / ".env", override=False)


def _data_dir():
    configured = os.getenv("FP_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "FP Estoque"

    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "fp-estoque"

    return Path.home() / ".fp-estoque"


def _configure_environment(root: Path, data_dir: Path):
    backend_dir = root / "backend" if not getattr(sys, "frozen", False) else root
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    frontend_dir = (
        root / "desktop_frontend"
        if getattr(sys, "frozen", False)
        else root / "backend" / "desktop_frontend"
    )

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ["FP_DESKTOP_MODE"] = "true"
    os.environ["FP_DATA_DIR"] = str(data_dir)
    os.environ["FP_FRONTEND_DIR"] = str(frontend_dir)
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("ALLOW_LAN_DEV", "false")
    os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1")


def _backup_database(data_dir: Path):
    database = data_dir / "fp-estoque.sqlite3"
    if not database.is_file() or database.stat().st_size == 0:
        return

    backup_dir = data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination = backup_dir / f"fp-estoque-{stamp}.sqlite3"

    source_connection = sqlite3.connect(str(database), timeout=30)
    destination_connection = sqlite3.connect(str(destination), timeout=30)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()

    backups = sorted(
        backup_dir.glob("fp-estoque-*.sqlite3"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for old_backup in backups[30:]:
        old_backup.unlink(missing_ok=True)


def _prepare_django(data_dir: Path):
    import django
    from django.core.management import call_command

    django.setup()
    _backup_database(data_dir)
    call_command("migrate", interactive=False, verbosity=0)


def _health_ready(url: str):
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("status") == "ok" and payload.get("mode") == "desktop-local"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return False


def _wait_for_server(url: str, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _health_ready(url):
            return True
        time.sleep(0.25)
    return False


def _start_server(host: str, port: int):
    from config.wsgi import application
    from waitress import serve

    serve(
        application,
        host=host,
        port=port,
        threads=6,
        channel_timeout=120,
        clear_untrusted_proxy_headers=True,
    )


def _show_error(title: str, message: str):
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"{title}: {message}", file=sys.stderr)


def _error_detail(error):
    try:
        payload = json.loads(error.read().decode("utf-8"))
        if isinstance(payload, dict):
            detail = payload.get("detail")
            if detail:
                return str(detail)
            return " • ".join(f"{key}: {value}" for key, value in payload.items())
    except Exception:
        pass
    return f"Falha HTTP {getattr(error, 'code', 'desconhecida')}."


class DesktopApi:
    ALLOWED_REPORT_PATHS = {
        "/api/reports/export.pdf": ".pdf",
        "/api/reports/export.xlsx": ".xlsx",
        "/api/reports/daily.pdf": ".pdf",
        "/api/reports/daily.xlsx": ".xlsx",
    }

    def __init__(self, app_url: str):
        self.app_url = app_url
        parsed = urllib.parse.urlparse(app_url)
        self.allowed_origin = (parsed.scheme, parsed.hostname, parsed.port)

    def _validated_report_url(self, url: str):
        absolute_url = urllib.parse.urljoin(self.app_url, str(url or ""))
        parsed = urllib.parse.urlparse(absolute_url)
        origin = (parsed.scheme, parsed.hostname, parsed.port)
        if origin != self.allowed_origin:
            raise ValueError("Endereço de relatório não permitido.")
        extension = self.ALLOWED_REPORT_PATHS.get(parsed.path)
        if not extension:
            raise ValueError("Tipo de relatório não permitido.")
        return absolute_url, extension

    @staticmethod
    def _safe_filename(filename: str, extension: str):
        name = Path(str(filename or "relatorio")).name
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
        if not name:
            name = "relatorio"
        name = name[:180]
        if not name.lower().endswith(extension):
            name += extension
        return name

    @staticmethod
    def _downloads_directory():
        downloads = Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        return downloads

    @classmethod
    def _available_destination(cls, filename: str):
        directory = cls._downloads_directory()
        candidate = directory / filename
        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        counter = 1
        while True:
            alternative = directory / f"{stem} ({counter}){suffix}"
            if not alternative.exists():
                return alternative
            counter += 1

    def _request_report(self, url: str, access_token: str):
        headers = {"Accept": "application/octet-stream"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()

    def _refresh_access_token(self, refresh_token: str):
        if not refresh_token:
            return None
        refresh_url = urllib.parse.urljoin(self.app_url, "api/auth/refresh/")
        request = urllib.request.Request(
            refresh_url,
            data=json.dumps({"refresh": refresh_token}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {
            "access": payload.get("access"),
            "refresh": payload.get("refresh") or refresh_token,
        }

    def save_report(self, url, filename, access_token="", refresh_token=""):
        try:
            report_url, extension = self._validated_report_url(url)
            safe_filename = self._safe_filename(filename, extension)
            destination = self._available_destination(safe_filename)

            refreshed = None
            try:
                content = self._request_report(report_url, str(access_token or ""))
            except urllib.error.HTTPError as error:
                if error.code != 401:
                    raise RuntimeError(_error_detail(error)) from error
                refreshed = self._refresh_access_token(str(refresh_token or ""))
                if not refreshed or not refreshed.get("access"):
                    raise RuntimeError("Sua sessão expirou. Entre novamente no sistema.") from error
                content = self._request_report(report_url, refreshed["access"])

            temporary = destination.with_name(f".{destination.name}.tmp")
            temporary.write_bytes(content)
            os.replace(temporary, destination)

            result = {
                "status": "saved",
                "path": str(destination),
                "filename": destination.name,
            }
            if refreshed:
                result.update(refreshed)
            return result
        except urllib.error.HTTPError as error:
            return {"status": "error", "error": _error_detail(error)}
        except Exception as error:
            return {"status": "error", "error": str(error)}


def main():
    _load_environment_file()
    root = _bundle_root()
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "media").mkdir(parents=True, exist_ok=True)
    (data_dir / "backups").mkdir(parents=True, exist_ok=True)
    webview_data_dir = data_dir / "webview"
    webview_data_dir.mkdir(parents=True, exist_ok=True)

    _configure_environment(root, data_dir)

    try:
        _prepare_django(data_dir)
    except Exception as exc:
        _show_error(
            "FP Estoque",
            f"Não foi possível preparar os arquivos locais do sistema.\n\n{exc}",
        )
        return 1

    host = "127.0.0.1"
    port = int(os.getenv("FP_DESKTOP_PORT", "8765"))
    app_url = f"http://{host}:{port}/"
    health_url = f"http://{host}:{port}/api/health/"

    if not _health_ready(health_url):
        server_thread = threading.Thread(
            target=_start_server,
            args=(host, port),
            name="fp-estoque-local-server",
            daemon=True,
        )
        server_thread.start()

    if not _wait_for_server(health_url):
        _show_error(
            "FP Estoque",
            "O serviço local não iniciou corretamente. Feche outras instâncias do programa e tente novamente.",
        )
        return 1

    try:
        import webview

        desktop_api = DesktopApi(app_url)
        webview.create_window(
            "FP Estoque — Depósito de Bebidas",
            app_url,
            js_api=desktop_api,
            width=1440,
            height=900,
            min_size=(1024, 680),
            resizable=True,
            text_select=True,
            confirm_close=False,
        )
        webview.start(
            gui="edgechromium",
            debug=os.getenv("DEBUG", "false").lower() == "true",
            private_mode=False,
            storage_path=str(webview_data_dir),
        )
    except Exception as exc:
        _show_error(
            "FP Estoque",
            f"Não foi possível abrir a janela do aplicativo.\n\n{exc}",
        )
        return 1

    try:
        from django.db import connections

        connections.close_all()
        _backup_database(data_dir)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
