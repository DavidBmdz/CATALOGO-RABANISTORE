"""Servidor local, sin dependencias, para la web y la API del catálogo."""

import json
import mimetypes
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from catalog import CatalogStore
from receipt_png import create_receipt


WEB_ROOT = Path(__file__).resolve().parent.parent
STORE = CatalogStore()
RECEIPTS_DIR = WEB_ROOT / "receipts"
RECEIPTS_DIR.mkdir(exist_ok=True)
mimetypes.add_type("image/avif", ".avif")


class RequestHandler(BaseHTTPRequestHandler):
    def _json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 16_384:
                raise ValueError("La solicitud excede el tamaño permitido.")
            raw = self.rfile.read(size) if size else b"{}"
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("El cuerpo debe ser JSON válido.") from error

    @staticmethod
    def _session(query, body=None):
        session_id = query.get("session", [None])[0]
        if not session_id and body:
            session_id = body.get("session")
        return str(session_id or "anon")[:100]

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)

        if path == "/api/products":
            self._json(STORE.search(
                category=query.get("category", [None])[0],
                query=query.get("q", [""])[0],
            ))
            return
        if path == "/api/categories":
            self._json({"filters": STORE.categories.filters(),
                        "tree": STORE.categories.as_dict()})
            return
        if path == "/api/history":
            self._json(STORE.history(self._session(query)))
            return
        if path == "/api/cart":
            self._json(STORE.cart_items(self._session(query)))
            return
        if path == "/api/inquiries/next":
            self._json(STORE.next_inquiry())
            return
        if path.startswith("/api/recommendations/"):
            product_id = path.removeprefix("/api/recommendations/")
            if not STORE.get_product(product_id):
                self._json({"error": "Producto no encontrado."}, 404)
                return
            self._json(STORE.recommendations_for(product_id))
            return
        if path.startswith("/api/products/"):
            product_id = path.removeprefix("/api/products/")
            product = STORE.get_product(product_id)
            if not product:
                self._json({"error": "Producto no encontrado."}, 404)
                return
            self._json(product)
            return
        if path.startswith("/api/"):
            self._json({"error": "Ruta de API no encontrada."}, 404)
            return
        self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        try:
            body = self._read_json()
            session_id = self._session(query, body)
            if path == "/api/receipt":
                items = STORE.cart_items(session_id)
                if not items:
                    raise ValueError("La bolsa está vacía.")
                order = datetime.now().strftime("RB-%y%m%d-%H%M%S")
                filename = f"{order}.png"
                total = create_receipt(items, RECEIPTS_DIR / filename, order, datetime.now().strftime("%d/%m/%Y %H:%M"))
                self._json({"order_number": order, "total": total, "receipt_url": f"/receipts/{filename}"}, 201)
                return
            if path == "/api/history":
                product_id = str(body.get("product_id", ""))
                if not STORE.get_product(product_id):
                    self._json({"error": "Producto no encontrado."}, 404)
                    return
                self._json(STORE.visit(session_id, product_id))
                return
            if path == "/api/history/undo":
                self._json(STORE.undo_visit(session_id))
                return
            if path == "/api/cart":
                items = STORE.add_to_cart(
                    session_id,
                    str(body.get("product_id", "")),
                    str(body.get("shade", "")),
                    body.get("quantity", 1),
                )
                self._json(items, 201)
                return
            if path == "/api/inquiries":
                inquiry = STORE.record_inquiry(
                    session_id,
                    str(body.get("product_id", "")),
                    str(body.get("shade", "")),
                )
                self._json(inquiry, 202)
                return
            self._json({"error": "Ruta de API no encontrada."}, 404)
        except ValueError as error:
            self._json({"error": str(error)}, 400)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        try:
            body = self._read_json()
            if path == "/api/cart":
                self._json(STORE.remove_from_cart(
                    self._session(query, body), str(body.get("key", ""))))
                return
            self._json({"error": "Ruta de API no encontrada."}, 404)
        except ValueError as error:
            self._json({"error": str(error)}, 400)

    def _serve_static(self, url_path):
        relative = "index.html" if url_path in ("", "/") else url_path.lstrip("/")
        requested = (WEB_ROOT / relative).resolve()
        try:
            requested.relative_to(WEB_ROOT)
        except ValueError:
            self.send_error(403)
            return
        if not requested.is_file():
            self.send_error(404)
            return
        content = requested.read_bytes()
        content_type = mimetypes.guess_type(str(requested))[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format_string, *args):
        print("[Rabanistore] " + format_string % args)


def main():
    address = ("127.0.0.1", 8000)
    print(f"Rabanistore está disponible en http://{address[0]}:{address[1]}")
    HTTPServer(address, RequestHandler).serve_forever()


if __name__ == "__main__":
    main()
