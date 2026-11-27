# Análisis a posteriori de Rabanistore

## Resumen

Rabanistore cumple el propósito de una demostración académica: presenta un catálogo de 15 productos, permite buscar y consultar detalles, registra historial y bolsa por sesión, recomienda productos y genera recibos PNG. La interfaz está servida junto a una API Python sin framework y los datos del catálogo se leen de un archivo JSON.

La implementación es clara y adecuada para demostrar estructuras de datos con pocos usuarios. No está diseñada para producción ni para millones de usuarios simultáneos. Este análisis es una revisión estática del código y su documentación; no se ejecutaron mediciones de rendimiento.

## Qué funciona bien

- Responsabilidades separadas entre interfaz, servidor, catálogo y estructuras de datos.
- Identificadores de producto indexados en un diccionario y relaciones de recomendación precalculadas al iniciar.
- Validación de productos y tonos antes de agregarlos a la bolsa.
- El servidor limita los cuerpos JSON a 16 KiB y restringe el servicio de archivos al directorio del proyecto.
- La documentación explica la ejecución local y reconoce que sesiones y consultas no son persistentes.

## Hallazgos y efectos

| Hallazgo | Efecto práctico | Prioridad |
|---|---|---|
| `HTTPServer` atiende una solicitud a la vez | Solicitudes simultáneas esperan en una cola; la latencia crece cuando aumenta la concurrencia. | Alta para carga |
| El servidor enlaza a `127.0.0.1` | Solo acepta conexiones de la misma computadora, así que no puede recibir tráfico de una granja de generadores remotos. | Alta para pruebas remotas |
| Historiales, bolsas y consultas viven en diccionarios/cola en memoria | Se pierden al reiniciar. Cada sesión activa consume memoria y no hay limpieza de sesiones antiguas. | Alta para millones de sesiones |
| No hay base de datos, límite de tasa, autenticación administrativa ni protección contra abuso | No es apropiado exponer el servidor directamente a Internet. | Alta antes de publicar |
| El identificador de recibo tiene resolución de un segundo | Dos solicitudes de recibo dentro del mismo segundo pueden escribir el mismo nombre de archivo. | Media |
| La búsqueda recompone los textos y recorre el catálogo en cada petición | El costo crece linealmente con los productos; con solo 15 productos el impacto actual es pequeño. | Baja ahora |
| La cola de consultas solo existe en memoria y no tiene interfaz administrativa documentada | Las consultas se pierden al reiniciar y no se ofrece un flujo de atención persistente. | Media |

## Conclusión

El límite inmediato no es el catálogo, sino el modelo del servidor y el almacenamiento de estado. Para un despliegue real habría que separar el servicio web de la lógica de negocio, usar un servidor concurrente detrás de un proxy, guardar carritos e historial en almacenamiento persistente con expiración, almacenar recibos con nombres únicos y añadir controles de seguridad y observabilidad. Después conviene medir cada cambio en un entorno de staging parecido al destino.

## Módulo de carga

Se agregó `backend/load_test.py`, que simula sesiones virtuales con solicitudes HTTP a la API. Por defecto hace navegación de solo lectura y no crea estado de sesión en el servidor. Admite cantidades grandes de usuarios virtuales acumulados y mantiene una concurrencia de hilos configurable. El informe incluye solicitudes por segundo, códigos HTTP, errores y latencias media, p50, p95 y p99; los percentiles se calculan sobre una muestra uniforme de hasta 100 000 solicitudes para limitar el uso de memoria. Si no se indica una ruta, crea automáticamente el JSON en `reportes_carga/` con el número de usuarios y la fecha/hora en el nombre.

Para revisar y comparar JSON en tablas y gráficas, inicia el servidor y abre <http://127.0.0.1:8000/reportes.html>. Se pueden cargar varios archivos a la vez o añadir más después. El visor compara solicitudes por segundo, latencias p95/p99 y porcentaje de errores según el número de usuarios virtuales; procesa los archivos localmente en el navegador.

Ejemplo local con carga moderada:

```powershell
py -m backend.server
py -m backend.load_test --users 10000 --concurrency 50
```

Para recorrer diez millones de identidades virtuales acumuladas:

```powershell
py -m backend.load_test --users 10000000 --concurrency 50
```

`--users 10000000` no significa diez millones conectados al mismo tiempo. La concurrencia real del generador está limitada por `--concurrency`; los usuarios se procesan en lotes acotados. El modo opcional `--write-state` ejercita historial y crea entradas de sesión en memoria, por lo que no se debe usar con diez millones de identidades contra el servidor actual: podría agotar la memoria. El modo de solo lectura evita ese crecimiento, pero sigue haciendo decenas de millones de solicitudes, así que la prueba puede durar bastante.

El servidor actual es de un solo hilo y solo escucha en loopback. La carga permitirá observar su comportamiento local, pero no demostrar capacidad de diez millones simultáneos. Para un ensayo de concurrencia real se necesita primero un entorno de staging, un servidor capaz de atender solicitudes en paralelo, almacenamiento diseñado para el volumen esperado y generadores distribuidos. Conviene incrementar la carga por etapas y detenerse ante errores crecientes, saturación o degradación severa.

## Cómo leer los resultados

- Comparar p95/p99 y errores entre ejecuciones con el mismo entorno y perfil.
- Registrar también CPU, memoria, conexiones, disco y métricas del almacenamiento durante la ejecución.
- Distinguir usuarios virtuales acumulados, usuarios activos simultáneos y solicitudes por segundo; son medidas diferentes.
- No interpretar una prueba en localhost como capacidad de Internet: red, TLS, proxy, caché y base de datos cambian el resultado.
