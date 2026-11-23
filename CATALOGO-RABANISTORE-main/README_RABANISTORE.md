# Rabanistore

**Catálogo digital de productos de maquillaje con bolsa de compras y generación de recibos PNG.**

## Integrantes

- David Bermúdez
- Michael Wong
- Javier Suazo
- José Almendarez

## Descripción

Rabanistore es una aplicación web para presentar un catálogo de productos de maquillaje y facilitar que los clientes seleccionen artículos y tonos, organicen su compra en una bolsa y generen un recibo en formato PNG. El recibo se puede descargar y enviar manualmente mediante un mensaje directo al Instagram de la tienda.

Instagram: [@rabanistore](https://www.instagram.com/rabanistore/)

## Funcionalidades principales

- Visualización del catálogo de productos.
- Organización y filtrado por categorías.
- Búsqueda de productos.
- Consulta de detalles y tonos disponibles.
- Registro del historial de productos visitados durante la sesión.
- Recomendaciones de productos relacionados.
- Bolsa de compras con selección de tono y cantidad.
- Eliminación de productos de la bolsa.
- Generación de recibos en formato PNG con número de pedido, fecha, productos, tonos, cantidades e importe total.
- Descarga del recibo para enviarlo manualmente por Instagram.

## Tecnologías utilizadas

- **Python:** servidor local, API y lógica del catálogo.
- **HTML:** estructura de la interfaz.
- **CSS:** presentación visual y estilos.
- **JavaScript:** interacción de la página y comunicación con la API.
- **Pillow:** generación de imágenes PNG.
- **JSON:** almacenamiento de los datos del catálogo.
- **VBScript (VBS):** iniciador opcional para ejecutar el servidor Python sin mostrar una ventana de consola en Windows.

## Requisitos

- Windows (para utilizar los archivos `.vbs` y `.bat` incluidos).
- Python 3.9 o superior.
- `pip` disponible desde el lanzador `py`.
- Navegador web actualizado.

La dependencia Python declarada por el proyecto es Pillow, incluida en `requirements.txt`.

## Instalación

1. Descarga y descomprime el proyecto.
2. Abre PowerShell o la terminal de Visual Studio Code en la carpeta `CATALOGO-RABANISTORE-main`.
3. Instala las dependencias:

   ```powershell
   py -m pip install -r requirements.txt
   ```

## Cómo ejecutar la aplicación

### Opción A: desde PowerShell o Visual Studio Code

Desde la carpeta principal del proyecto, ejecuta:

```powershell
py -m backend.server
```

Mantén esa terminal abierta mientras utilices la tienda. Después, abre en el navegador:

<http://127.0.0.1:8000>

Para detener el servidor, vuelve a la terminal y presiona `Ctrl + C`.

**Importante:** ejecuta el servidor como módulo con `py -m backend.server`. No ejecutes `backend/server.py` directamente, porque los módulos internos utilizan importaciones relativas.

### Opción B: iniciar en segundo plano en Windows

En el Explorador de archivos, abre la carpeta principal del proyecto y haz doble clic en:

`INICIAR_RABANISTORE_SILENCIOSO.vbs`

El iniciador ejecuta `pyw -m backend.server` sin mostrar una ventana de consola, espera a que el servidor responda y luego abre el navegador en `http://127.0.0.1:8000`.

Para detener el servidor, ejecuta:

`DETENER_RABANISTORE.bat`

No cierres el proceso de Python desde el Administrador de tareas mientras utilices la tienda. Si el puerto 8000 ya está ocupado, el servidor no podrá iniciarse normalmente.

## Estructura general del proyecto

```text
CATALOGO-RABANISTORE-main/
├── index.html
├── styles.css
├── script.js
├── requirements.txt
├── ESTRUCTURAS.md
├── INICIAR_RABANISTORE_SILENCIOSO.vbs
├── DETENER_RABANISTORE.bat
├── assets/
│   └── productos/
└── backend/
    ├── __init__.py
    ├── server.py
    ├── catalog.py
    ├── products.json
    ├── category_tree.py
    ├── linked_list.py
    ├── doubly_linked_list.py
    ├── recommendation_graph.py
    └── stack_queue.py
```

### Responsabilidad de los archivos principales

- `index.html`: estructura de la página.
- `styles.css`: estilos de la interfaz.
- `script.js`: interacción del catálogo y solicitudes a la API.
- `backend/server.py`: servidor web, endpoints de la API y creación de recibos PNG.
- `backend/catalog.py`: lógica que conecta los datos del catálogo con las estructuras de datos.
- `backend/products.json`: información de los productos.
- `assets/productos/`: imágenes de los productos.
- `requirements.txt`: dependencias Python.
- `ESTRUCTURAS.md`: documentación de las estructuras de datos y sus costos.
- `INICIAR_RABANISTORE_SILENCIOSO.vbs`: inicio oculto del servidor en Windows.
- `DETENER_RABANISTORE.bat`: detiene el proceso que escucha en el puerto 8000.

## Estructuras de datos utilizadas

El proyecto incluye las siguientes estructuras en el backend:

- **Árbol de categorías:** organiza los productos por categorías y subcategorías.
- **Lista enlazada simple:** mantiene el historial de productos visitados.
- **Lista doblemente enlazada:** administra las líneas de la bolsa de compras.
- **Grafo:** representa relaciones entre productos para obtener recomendaciones.
- **Pila (LIFO):** permite deshacer la visita más reciente.
- **Cola (FIFO):** mantiene consultas pendientes de atención.
- **Diccionario (tabla hash):** permite localizar productos por identificador.

Para una explicación más detallada de las operaciones y su complejidad, consulta `ESTRUCTURAS.md`.

## Recibos PNG

Cuando el cliente solicita generar el recibo, el backend obtiene los artículos de la bolsa de esa sesión y crea una imagen PNG. Los archivos se guardan en la carpeta `receipts/` dentro del proyecto y se entregan mediante una ruta de descarga.

El recibo incluye número de pedido, fecha y hora, nombre del producto, tono, cantidad e importe, además del total del pedido.

El cliente debe descargar la imagen y adjuntarla manualmente en un mensaje directo de Instagram. Esta versión no envía mensajes automáticamente a Instagram.

## Alcance y consideraciones

Esta entrega funciona como una aplicación local de demostración:

- El servidor escucha en `127.0.0.1:8000`; por defecto, solo está disponible desde la computadora donde se ejecuta.
- La bolsa, el historial y las consultas pendientes se mantienen en memoria y se reinician al detener el servidor.
- Los recibos PNG ya generados permanecen guardados en la carpeta `receipts/`.
- El proyecto no incluye una base de datos persistente ni un sistema de autenticación o administración de pedidos.
- Para ofrecer compras públicas por Internet y conservar pedidos entre reinicios, sería necesario desplegar el backend en un servicio de hosting y añadir persistencia y controles de seguridad adecuados.

## Soporte de ejecución

Si la página abre pero los productos muestran `Failed to fetch`, comprueba que el servidor Python siga ejecutándose y que estés entrando mediante `http://127.0.0.1:8000`, no abriendo `index.html` directamente.

---

**Rabanistore — Catálogo digital de maquillaje y gestión de pedidos.**
