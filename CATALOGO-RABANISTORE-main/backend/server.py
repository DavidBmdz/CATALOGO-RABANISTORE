"""Servidor local, sin dependencias, para la web y la API del catálogo."""

import json
import mimetypes
import re
from datetime import datetime
from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import parse_qs, unquote, urlparse

from .catalog import CatalogStore


WEB_ROOT = Path(__file__).resolve().parent.parent
STORE = CatalogStore()
RECEIPTS_DIR = WEB_ROOT / "receipts"
RECEIPTS_DIR.mkdir(exist_ok=True)
mimetypes.add_type("image/avif", ".avif")


def _font(size, bold=False):
    candidates = (["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
                  if bold else ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()

def create_receipt(items):
    """Crea una imagen PNG del pedido actual y devuelve su nombre de archivo."""
    if not items:
        raise ValueError("Tu bolsa está vacía. Agrega productos antes de generar el recibo.")
    now = datetime.now()
    order_number = now.strftime("RB-%y%m%d-%H%M%S")
    width, margin = 900, 64
    row_height = 105
    height = 520 + row_height * len(items)
    image = Image.new("RGB", (width, height), "#fffaf8")
    draw = ImageDraw.Draw(image)
    ink, muted, pink, line = "#35252d", "#806d75", "#bd718d", "#ead9df"
    draw.rounded_rectangle((24, 24, width-24, height-24), radius=28, fill="white", outline=line, width=3)
    draw.text((margin, 58), "RABANISTORE", font=_font(42, True), fill=ink)
    draw.text((margin, 112), "BEAUTY & MORE  ·  RECIBO DE PEDIDO", font=_font(19, True), fill=pink)
    draw.line((margin, 160, width-margin, 160), fill=line, width=3)
    draw.text((margin, 190), f"Pedido: {order_number}", font=_font(20, True), fill=ink)
    draw.text((margin, 225), now.strftime("Fecha: %d/%m/%Y   Hora: %H:%M"), font=_font(18), fill=muted)
    y = 290
    draw.text((margin, y), "PRODUCTO / TONO", font=_font(17, True), fill=muted)
    draw.text((width-margin-210, y), "CANT.     IMPORTE", font=_font(17, True), fill=muted)
    y += 42
    total = 0
    for item in items:
        qty = int(item.get("quantity", 1))
        unit = float(item.get("unit_price", 0))
        subtotal = qty * unit
        total += subtotal
        name = str(item.get("name", "Producto"))
        shade = str(item.get("shade", ""))
        draw.line((margin, y, width-margin, y), fill=line, width=1)
        draw.text((margin, y+13), name[:43], font=_font(19, True), fill=ink)
        draw.text((margin, y+43), f"Tono: {shade[:45]}", font=_font(16), fill=muted)
        draw.text((width-margin-200, y+24), f"{qty:>2}     C${subtotal:,.0f}", font=_font(19, True), fill=ink)
        y += row_height
    y += 8
    draw.line((margin, y, width-margin, y), fill=line, width=3)
    draw.text((margin, y+28), "TOTAL DEL PEDIDO", font=_font(22, True), fill=ink)
    total_text = f"C${total:,.0f}"
    bbox = draw.textbbox((0, 0), total_text, font=_font(30, True))
    draw.text((width-margin-(bbox[2]-bbox[0]), y+22), total_text, font=_font(30, True), fill=pink)
    draw.text((margin, y+92), "¡Gracias por elegir Rabanistore! ♡", font=_font(20, True), fill=ink)
    draw.text((margin, y+130), "Envía esta imagen por mensaje directo en Instagram", font=_font(16), fill=muted)
    draw.text((margin, y+160), "instagram.com/rabanistore", font=_font(17, True), fill=pink)
    filename = f"{order_number}.png"
    image.save(RECEIPTS_DIR / filename, format="PNG", optimize=True)
    return filename, order_number, total


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

        if path.startswith("/receipts/"):
            filename = Path(path).name
            if not re.fullmatch(r"RB-[0-9]{6}-[0-9]{6}\.png", filename):
                self.send_error(404); return
            receipt = RECEIPTS_DIR / filename
            if not receipt.is_file():
                self.send_error(404); return
            data = receipt.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers(); self.wfile.write(data); return
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
                filename, order_number, total = create_receipt(items)
                self._json({"ok": True, "order_number": order_number, "total": total,
                            "receipt_url": f"/receipts/{filename}"}, 201)
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
