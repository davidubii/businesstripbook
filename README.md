# BusinessTripBook – Bot de Telegram para gestionar facturas en PDF

BusinessTripBook es un bot de Telegram que te permite guardar y consultar tus facturas simplemente enviando archivos PDF al chat.  
Extrae automáticamente fecha, total, comercio e IVA de cada factura, las guarda en una base de datos SQLite y ofrece comandos para listarlas, filtrarlas, calcular totales y exportarlas a CSV.

---

## ✨ Características principales

- Recepción de facturas en formato PDF directamente desde Telegram (modo chat con el bot).  
- Extracción automática de:
  - Fecha de la factura (`dd/mm/yyyy` o `dd-mm-yyyy`).
  - Importe total (reconociendo formatos con coma y punto).
  - Porcentaje de IVA.
  - Nombre del comercio (por campo explícito o por heurística de primera línea).
- Almacenamiento de todas las facturas en SQLite, incluyendo:
  - `chat_id` de Telegram (cada chat ve solo sus propias facturas).
  - Ruta local del PDF.
  - Fecha y hora de procesamiento.
- Comandos para:
  - Listar las últimas facturas.
  - Buscar por comercio.
  - Filtrar por rango de fechas.
  - Calcular el total acumulado.
  - Borrar facturas concretas.
  - Exportar todo a un CSV compatible con Excel.
- Soporte multiusuario/multi‑chat gracias al uso de `chat_id` en la base de datos.

---

## 🧱 Arquitectura del proyecto

El proyecto está organizado en tres capas/módulos bien separados:

- `bot.py`  
  Capa de interfaz con Telegram. Define todos los comandos (`/start`, `/ayuda`, `/listar`, `/total`, `/buscar`, `/borrar`, `/exportar`, `/filtrar`), maneja la recepción de PDFs y construye los mensajes de respuesta al usuario.

- `pdf_parser.py`  
  Capa de lógica de negocio encargada de abrir el PDF, extraer todo el texto y localizar los campos clave mediante expresiones regulares (fecha, total, IVA, comercio). Expone la función principal `extraer_datos_factura(ruta_pdf: str) -> dict`.

- `conexion_bbdd.py`  
  Capa de persistencia basada en SQLite. Se ocupa de crear y actualizar la tabla `facturas`, guardar nuevas facturas, listarlas, filtrarlas, sumar totales, buscar por comercio, borrar y exportar a CSV.

Esta separación hace que el bot sea más fácil de mantener y ampliar (por ejemplo, cambiando el parser o la base de datos sin tocar la lógica de Telegram).

---

## 📁 Estructura de ficheros

```text
.
├── bot.py                 # Bot de Telegram y comandos
├── pdf_parser.py          # Lógica de extracción de datos desde el PDF
├── conexion_bbdd.py       # Acceso y operaciones sobre la base de datos SQLite
├── .env                   # TOKEN del bot de Telegram (inaccesible)
├── facturas/              # Carpeta con un PDF de prueba para probar el funcionamiento del bot
└── exportaciones/         # Carpeta con los CSV generados por /exportar
