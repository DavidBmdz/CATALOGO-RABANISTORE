"""Prueba de carga concurrente para la API de Rabanistore.

Ejemplo desde la raíz del proyecto:
    py -m backend.load_test --users 10000 --concurrency 50

``users`` cuenta sesiones virtuales distintas durante toda la ejecución; no
crea diez millones de conexiones ni procesos simultáneos. ``concurrency``
limita los hilos de solicitudes del generador.
"""

import argparse
import json
import math
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


PRODUCTS_FILE = Path(__file__).with_name("products.json")
PRODUCT_IDS = [item["id"] for item in json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))]
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(math.ceil(fraction * len(ordered)) - 1, len(ordered) - 1)], 2)


class LoadRunner:
    def __init__(self, base_url, timeout, write_state):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.write_state = write_state

    def request(self, path, method="GET", payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path, data=data, method=method,
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        status = None
        error = None
        error_type = None
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status = response.status
                response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            error = f"HTTP {exc.code}"
            error_type = "HTTPError"
            exc.read()
        except Exception as exc:  # captura timeouts, conexión rechazada y errores de red
            error = f"{type(exc).__name__}: {exc}"
            error_type = type(exc).__name__
        return {"latency_ms": (time.perf_counter() - started) * 1000,
                "status": status, "error": error, "error_type": error_type}

    def simulate_user(self, user_number):
        """Un usuario navega catálogo, detalle, historial y bolsa."""
        session = urllib.parse.quote(f"load-{user_number}")
        product_id = PRODUCT_IDS[user_number % len(PRODUCT_IDS)]
        actions = [
            ("GET", "/api/products"),
            # Los IDs pueden contener espacios u otros caracteres que deben
            # codificarse cuando forman parte de una ruta URL.
            ("GET", f"/api/products/{urllib.parse.quote(product_id, safe='')}"),
            ("GET", f"/api/recommendations/{urllib.parse.quote(product_id, safe='')}"),
            ("GET", f"/api/cart?session={session}"),
        ]
        if self.write_state:
            actions.extend([
                ("POST", "/api/history", {"session": session, "product_id": product_id}),
                ("GET", f"/api/history?session={session}"),
            ])
        outcomes = []
        for action in actions:
            method, path, *body = action
            outcomes.append(self.request(path, method, body[0] if body else None))
        return outcomes


def run(args):
    runner = LoadRunner(args.base_url, args.timeout, args.write_state)
    latency_sample = []
    sample_rng = random.Random(42)
    latency_total = 0.0
    latency_max = 0.0
    request_count = 0
    failures = []
    failure_count = 0
    network_error_types = {}
    status_counts = {}
    completed_users = 0
    started_at = datetime.now(timezone.utc)
    started_at_utc = started_at.isoformat()
    started = time.perf_counter()
    # Enviar lotes acotados mantiene bajo el consumo de memoria incluso al
    # recorrer millones de identidades virtuales.
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        next_user = 0
        while next_user < args.users:
            batch_size = min(args.concurrency * 4, args.users - next_user)
            futures = [pool.submit(runner.simulate_user, i)
                       for i in range(next_user, next_user + batch_size)]
            for future in as_completed(futures):
                outcomes = future.result()
                completed_users += 1
                for outcome in outcomes:
                    latency = outcome["latency_ms"]
                    request_count += 1
                    latency_total += latency
                    latency_max = max(latency_max, latency)
                    if len(latency_sample) < 100_000:
                        latency_sample.append(latency)
                    else:
                        index = sample_rng.randrange(request_count)
                        if index < len(latency_sample):
                            latency_sample[index] = latency
                    key = str(outcome["status"] or "network_error")
                    status_counts[key] = status_counts.get(key, 0) + 1
                    if outcome["error"]:
                        failure_count += 1
                        if len(failures) < 20:
                            failures.append(outcome["error"])
                    if outcome["status"] is None and outcome["error_type"]:
                        error_type = outcome["error_type"]
                        network_error_types[error_type] = network_error_types.get(error_type, 0) + 1
            next_user += batch_size
            if args.progress and (next_user % args.progress == 0 or next_user == args.users):
                print(f"Sesiones completadas: {next_user:,}/{args.users:,}")

    elapsed = time.perf_counter() - started
    requests = request_count
    report = {
        "started_at_utc": started_at_utc,
        "target": args.base_url,
        "virtual_users": args.users,
        "concurrency": args.concurrency,
        "requests_per_user": 6 if args.write_state else 4,
        "completed_users": completed_users,
        "requests": requests,
        "elapsed_seconds": round(elapsed, 2),
        "requests_per_second": round(requests / elapsed, 2) if elapsed else 0,
        "latency_ms": {
            "mean": round(latency_total / requests, 2) if requests else None,
            "p50": percentile(latency_sample, 0.50),
            "p95": percentile(latency_sample, 0.95),
            "p99": percentile(latency_sample, 0.99),
            "max": round(latency_max, 2) if requests else None,
            "percentile_sample_size": len(latency_sample),
        },
        "status_counts": status_counts,
        "error_count": failure_count,
        "network_error_types": network_error_types,
        "sample_errors": failures[:20],
        "scope_note": "Usuarios virtuales acumulados con concurrencia limitada; no equivale a usuarios simultáneos.",
        "write_state": args.write_state,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.output:
        requested_path = Path(args.output)
        if requested_path.suffix.lower() == ".json":
            output_dir = requested_path.parent
            prefix = requested_path.stem
        else:
            output_dir = requested_path
            prefix = "reporte-carga"
    else:
        output_dir = PROJECT_ROOT / "reportes_carga"
        prefix = "reporte-carga"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = started_at.strftime("%Y%m%d-%H%M%S-%fZ")
    report_path = output_dir / f"{prefix}-{args.users}usuarios-{timestamp}.json"
    report_path.write_text(output + "\n", encoding="utf-8")
    print(f"Informe guardado en: {report_path}")


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Debe ser un entero positivo.")
    return number


def main():
    parser = argparse.ArgumentParser(description="Generador de carga HTTP para Rabanistore")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="URL del servidor objetivo")
    parser.add_argument("--users", type=positive_int, default=1000,
                        help="sesiones virtuales distintas en total (por defecto: 1000)")
    parser.add_argument("--concurrency", type=positive_int, default=20,
                        help="solicitudes concurrentes del generador (por defecto: 20)")
    parser.add_argument("--timeout", type=float, default=10.0, help="timeout HTTP en segundos")
    parser.add_argument("--write-state", action="store_true",
                        help="incluye escrituras al historial; consume memoria en el servidor")
    parser.add_argument("--progress", type=positive_int, default=1000,
                        help="mostrar avance cada N sesiones; 0 no es válido")
    parser.add_argument("--output", help=(
        "ruta base para el informe: si termina en .json, se usa su carpeta y nombre como prefijo; "
        "si no, se usa como carpeta. Por defecto: reportes_carga en la raíz del proyecto"
    ))
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout debe ser positivo")
    run(args)


if __name__ == "__main__":
    main()
