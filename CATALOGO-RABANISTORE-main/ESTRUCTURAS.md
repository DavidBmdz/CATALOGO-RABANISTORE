# Estructuras de datos aplicadas a Rabanistore

## Ejecutar la aplicación

Requiere Python 3.9 o superior y Pillow para generar recibos PNG. Instálalo una vez desde PowerShell con `py -m pip install Pillow`. Después, desde la carpeta del proyecto, ejecuta:

```powershell
py -m backend.server
```

Luego abre <http://127.0.0.1:8000>. Para detener el servidor, usa `Ctrl+C`. La página necesita el servidor para que funcionen el catálogo Python, los filtros y las nuevas funciones.

## Módulos

- `backend/products.json`: fuente única de los 15 productos; el precio es numérico.
- `backend/catalog.py`: carga el catálogo y conecta las estructuras.
- `backend/category_tree.py`: organiza categorías y subcategorías.
- `backend/linked_list.py`: historial de productos vistos.
- `backend/doubly_linked_list.py`: líneas de la bolsa, con enlaces hacia el anterior y el siguiente.
- `backend/recommendation_graph.py`: relaciones de combinación entre productos.
- `backend/stack_queue.py`: pila para deshacer la última visita y cola FIFO para consultas por Instagram.
- `backend/server.py`: API, servidor web y generación de recibos PNG (requiere Pillow). Los recibos se guardan en `receipts/`.
- `script.js`: consume la API y presenta filtros, historial, recomendaciones y bolsa.

## Funcionalidades y notación asintótica

Sea `n` la cantidad de productos, `c` la cantidad de categorías, `h` la profundidad del árbol, `V` los productos del grafo y `E` sus relaciones.

| Estructura | Uso en la aplicación | Operación | Costo |
|---|---|---|---:|
| Lista de Python | Catálogo base y resultados filtrados | Recorrer y filtrar `n` productos | **O(n · L)**, donde `L` es el texto promedio que se compara |
| Diccionario / tabla hash | Índice `id → producto` | Consultar por ID | **O(1)** promedio; **O(n)** en el peor caso teórico |
| Lista enlazada simple | Historial de visitas | Añadir al inicio | **O(1)** |
| Lista enlazada simple | Historial de visitas | Recorrer las últimas `k` visitas | **O(k)**; localizar una visita para quitarla, **O(n)** |
| Lista doblemente enlazada | Bolsa | Añadir al final | **O(1)** |
| Lista doblemente enlazada | Bolsa | Buscar una línea | **O(n)**; quitarla una vez localizada, **O(1)** |
| Árbol de categorías | Navegar categorías y subcategorías | Seguir un camino | **O(h)** con hijos indexados por nombre |
| Árbol de categorías | Filtrar una rama completa | Reunir sus productos | **O(cᵣ + nᵣ)** para nodos y productos de esa rama |
| Grafo con listas de adyacencia | Preparar relaciones producto a producto | Comparar pares al iniciar | **O(n²)** en esta versión |
| Grafo con listas de adyacencia | Recomendar productos relacionados | Búsqueda en anchura (BFS) | **O(V + E)** en el peor caso; memoria **O(V + E)** |
| Pila | Deshacer la visita más reciente | `push` / `pop` | **O(1)** amortizado |
| Cola | Consultas pendientes | Encolar / atender la primera | **O(1)** |

`O(…)` describe cómo crece el trabajo al aumentar los datos. Por ejemplo, la búsqueda revisa el catálogo; la consulta por ID usa un diccionario y normalmente no depende del tamaño del catálogo. La bolsa busca si ya existe la combinación producto/tono antes de añadirla, así que esa búsqueda cuesta **O(m)** para `m` líneas; añadir al final cuesta **O(1)** y quitar una línea localizada cuesta **O(1)** gracias a los enlaces anterior/siguiente.

## API local

- `GET /api/products?category=labios&q=nyx`: lista, filtra y busca.
- `GET /api/products/{id}`: devuelve detalles de un producto.
- `GET /api/categories`: devuelve los filtros y el árbol.
- `GET /api/recommendations/{id}`: devuelve productos conectados en el grafo.
- `GET /api/history?session={id}` y `POST /api/history`: historial por sesión.
- `POST /api/history/undo`: elimina la visita más reciente usando la pila.
- `GET /api/cart?session={id}`, `POST /api/cart` y `DELETE /api/cart`: bolsa de compra.
- `POST /api/receipt`: genera el recibo PNG del contenido de la bolsa y devuelve su ruta de descarga.
- `POST /api/inquiries`: registra una consulta en la cola; `GET /api/inquiries/next` atiende la siguiente.

## Alcance de esta versión

El servidor es una demostración local para el proyecto académico. El catálogo vive en `products.json`; historial, bolsa y cola viven en memoria y se reinician al detener Python; los recibos PNG generados sí permanecen en `receipts/`. Para publicar la tienda con varios usuarios y conservar pedidos habría que guardar las sesiones y transacciones en una base de datos y proteger las rutas administrativas.
