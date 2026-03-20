# -> !! RECORDAR: handler es "cuando pase esto, haz esto" y hay que añadirlos al crearlos al final si no caca
# el bot esta preguntando siempre en telegram: ¿me estan escribiendo? esto = "polling"
# 17/03/26 -> investigar si es posible que la base de datos se enlace al usuario o al chat, de manera que cada usuario vea su informacion,
# y no sea compartida. Seguramente haya que cambiar gran parte del codigo, sobretodo en el archivo de conexion_bbdd.py, ya que deberia hacer un return del chat_id
# para comprobaciones

from dotenv import load_dotenv
import os
import re
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pdf_parser import extraer_datos_factura
from conexion_bbdd import inicializar_bd, guardar_factura, borrar_factura, buscar_por_comercio, filtrar_facturas_por_fecha
from conexion_bbdd import exportar_facturas_a_csv_v3, obtener_ultimas_facturas, obtener_total_facturas

# log para ver que hace el bot y que muestre errores
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", # formato de cada línea de log
    level=logging.INFO # nivel mínimo para mostrar logs
)
# basicConfig configura el formato y nivel de logging (INFO = muestra INFO, WARNING, ERROR...)

###### COMANDO BIENVENIDA ######
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    # con async se permite que el bot maneje varios usuarios simultáneamente sin bloquearse
    await update.message.reply_text( # envía mensaje de respuesta al chat donde se ejecutó /start
        "👋 ¡Hola! Soy BusinessTripBook.\n\n"
        "Envíame una factura en PDF y extraeré automáticamente:\n"
        "📅 Fecha\n💶 Total\n🏪 Comercio\n📊 IVA\n\n"
        "¡Solo tienes que enviarme el archivo!\n"
        "Si no sabes como hablar conmigo, escribe /ayuda"
    )

################ COMANDOS UTILES ######################

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # obtener_ultimas_facturas(5) devuelve las 5 facturas más recientes
    chat_id = update.effective_chat.id  # cada chat (usuario o grupo) tiene su propio id único en Telegram
    facturas = obtener_ultimas_facturas(chat_id, 5)

    if not facturas:
        await update.message.reply_text("📭 Todavía no hay facturas guardadas.")
        return # sale de la función

    lineas = ["📋 *Últimas facturas guardadas:*", ""]
    for f in facturas:
        # crea una línea con formato legible para cada factura
        linea = f"• [{f['id']}]: {f['fecha'] or 'Sin fecha'} - {f['comercio'] or 'Sin comercio'} - {f['total'] or '?'} €"
        lineas.append(linea)

    # con "\n.join" se unen todas las líneas con un salto de línea
    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # respuesta con todos los comandos disponibles en formato markdown
    await update.message.reply_text( 
        "📖 *Comandos disponibles:*\n\n"
        "📎 /start → Mensaje de bienvenida\n"
        "📋 /listar → Ver tus últimas facturas\n"
        "💶 /total → Suma total de todas tus facturas\n"
        "🔍 /buscar [nombre] → Buscar por comercio\n"
        "🗑️ /borrar [id] → Eliminar una factura\n"
        "⬇️ /exportar para descargar todas las facturas en un CSV\n"
        "🎛️ /filtrar → Usa el formato dd/mm/yyy para filtrar facturas\n"
        "❓ /ayuda → Ver esta ayuda\n\n"
        "📄 También puedes enviar directamente un PDF para procesarlo.",
        parse_mode="Markdown" # permite negritas (*texto*) y monospaced (`texto`) si se usasen
    )


async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # obtiene el total acumulado de todas las facturas
    chat_id = update.effective_chat.id  # se usa el chat_id para sumar solo las facturas de este chat
    suma = obtener_total_facturas(chat_id)
    mensaje = f"💶 El importe total acumulado de tus facturas es: *{suma:.2f} €*"
    await update.message.reply_text(mensaje, parse_mode="Markdown")


async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: # si no hay argumentos después de /buscar...
        await update.message.reply_text("🔍 Uso: /buscar nombre_comercio\nEjemplo: /buscar mercadona") # se le explica al usuario como usarlo
        return

    texto_busqueda = " ".join(context.args) # une todos los argumentos en una sola cadena para leerlos bien
    chat_id = update.effective_chat.id  #y  se filtra la búsqueda solo a las facturas de este chat
    resultados = buscar_por_comercio(texto_busqueda, chat_id)

    if not resultados:
        await update.message.reply_text(f"❌ No se han encontrado facturas para: *{texto_busqueda}*", parse_mode="Markdown")
        return

    lineas = [f"🔍 *Resultados para* `{texto_busqueda}`:", ""]
    for f in resultados[:10]: # máximo 10 resultados para no saturar telegram (tarda mucho/da error si se pone mas de 10)
        linea = f"• [{f['id']}]: {f['fecha'] or 'Sin fecha'} - {f['comercio'] or 'Sin comercio'} - {f['total'] or '?'} €"
        lineas.append(linea)

    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


async def borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: # si no hay argumentos después de /borrar...
        await update.message.reply_text("🗑️ Uso: /borrar id\nEjemplo: /borrar 3") # se le explica al usuario como usarlo
        return

    try:
        id_factura = int(context.args[0]) # convierte el primer argumento a un numero entero
    except ValueError:
        await update.message.reply_text("⚠️ El id debe ser un número. Por ejemplo: /borrar 3")
        return

    chat_id = update.effective_chat.id  # solo se permite borrar facturas que pertenecen a este chat
    if borrar_factura(id_factura, chat_id): # devuelve true si borró algo
        await update.message.reply_text(f"✅ Factura con id {id_factura} borrada correctamente.")
    else:
        await update.message.reply_text(f"❌ No se ha encontrado ninguna factura con id {id_factura}.")


async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📤 Generando fichero CSV con todas tus facturas...")

    # nombre con fecha y hora para evitar los duplicados en la base de datos 
    nombre = datetime.now().strftime("facturas_%Y%m%d_%H%M%S.csv")
    ruta = os.path.join("exportaciones", nombre)
    os.makedirs("exportaciones", exist_ok=True) # crea la carpeta si no existe

    chat_id = update.effective_chat.id  # cada usuario exporta solo sus propias facturas
    ruta_csv = exportar_facturas_a_csv_v3(ruta, chat_id)

    if not os.path.exists(ruta_csv):
        await update.message.reply_text("❌ No se ha podido generar el fichero CSV.")
        return

    # el bot envía el fichero como documento adjunto
    await update.message.reply_document(
        document=open(ruta_csv, "rb"), # abre en modo lectura binaria
        filename=nombre, # nombre que aparecerá en Telegram
        caption="📎 Aquí tienes tus facturas en formato CSV. Puedes abrirlo con Excel."
    )


async def filtrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Filtra facturas entre dos fechas. Uso: /filtrar dd/mm/yyyy dd/mm/yyyy"""

    # validar que el usuario pasó exactamente 2 argumentos
    if len(context.args) != 2:
        await update.message.reply_text(
            "⚠️ Uso correcto: `/filtrar dd/mm/yyyy dd/mm/yyyy`\n"
            "Ejemplo: `/filtrar 01/01/2025 31/03/2025`",
            parse_mode="Markdown"
        )
        return

    fecha_inicio, fecha_fin = context.args[0], context.args[1]
    # validar formato de fecha con regex

    patron = r"^\d{2}/\d{2}/\d{4}$"
    if not re.match(patron, fecha_inicio) or not re.match(patron, fecha_fin):
        await update.message.reply_text(
            "❌ Formato de fecha incorrecto. Usa `dd/mm/yyyy`.",
            parse_mode="Markdown"
        )
        return

    chat_id = update.effective_chat.id  # se filtran las facturas solo del chat actual
    facturas = filtrar_facturas_por_fecha(fecha_inicio, fecha_fin, chat_id)

    if not facturas:
        await update.message.reply_text(
            f"📭 No hay facturas entre el {fecha_inicio} y el {fecha_fin}."
        )
        return

    # se calcula el total del período
    total_periodo = sum(
        float(str(f["total"]).replace("€", "").replace(",", ".").strip())
        for f in facturas
    )
    # y se construye la respuesta con los datos
    lineas = [f"📅 Facturas del {fecha_inicio} al {fecha_fin}:\n"]
    for f in facturas:
        lineas.append(f"• {f['id']}: {f['fecha']} — {f['comercio']} — {f['total']} €")

    lineas.append(f"\n💶 Total del período: {total_periodo:.2f} €")
    lineas.append(f"📄 Facturas encontradas: {len(facturas)}")

    await update.message.reply_text("\n".join(lineas))

############# COSAS QUE EL USUARIO PUEDE HACER Y HAY QUE EVITAR ###########################

# si el usuario enviase una foto al chat:
async def rechazar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # las fotos llegan como 'photo' no como 'document', por eso necesitan su propio handler
    await update.message.reply_text(
        "⚠️ Has enviado una imagen.\n\n"
        "Este bot solo procesa facturas en formato *PDF*.\n"
        "Por favor, envía el fichero PDF directamente.",
        parse_mode="Markdown"
    )

# si el usuario escribe cualquier cosa que no sea un comando conocido
async def mensaje_desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # texto normal, no comandos (que empiecen por /)
    await update.message.reply_text(
        "❓ No entiendo ese mensaje.\n"
        "Usa /ayuda para ver los comandos disponibles."
    )

# cuando se reciba un archivo:
async def recibir_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    documento = update.message.document # objeto con metadatos del documento recibido

    # comprobar que el archivo es un PDF
    if documento.mime_type != "application/pdf":
        await update.message.reply_text("⚠️ Por favor, envíame solo archivos PDF.")
        return

    # cuando el pdf se envíe, automáticamente enviar mensaje de "procesando"
    await update.message.reply_text("⏳ Procesando tu factura...")

    # descargar el PDF a una carpeta local para que el código pueda procesarlo
    archivo = await documento.get_file() # descarga metadatos del fichero
    ruta_local = os.path.join("facturas", documento.file_name)
    await archivo.download_to_drive(ruta_local) # descarga el fichero al disco

    # extraer datos y guardar en bbdd/facturas.db
    chat_id = update.effective_chat.id  # se obtiene el id del chat que ha enviado el PDF
    try:
        datos = extraer_datos_factura(ruta_local) # llama a pdf_parser.py
        guardar_factura(datos, ruta_local, chat_id) # guarda en sqlite ligado a este chat

        # mostrar datos extraídos al usuario
        respuesta = (
            f"✅ Factura guardada correctamente\n\n"
            f"🏪 Comercio: {datos.get('comercio') or 'No encontrado'}\n"
            f"🗓️ Fecha: {datos.get('fecha') or 'No encontrada'}\n"
            f"💶 Total: {datos.get('total') or 'No encontrado'} €\n"
            f"📊 IVA: {datos.get('iva') or 'No encontrado'}"
        )
    except ValueError:
        # si pdf_parser.py lanza error (PDF sin texto), informar al usuario
        respuesta = "❌ No se pudo procesar el PDF. Asegúrate de que no sea un PDF escaneado."

    await update.message.reply_text(respuesta)


def main():
    load_dotenv() # carga el token desde el .env
    TOKEN = os.getenv("TOKEN") # lee el token del .env

    os.makedirs("facturas", exist_ok=True) # crea carpeta para PDFs descargados, si existe la abre

    inicializar_bd() # crea la tabla si no existe

    app = Application.builder().token(TOKEN).build() # crea la aplicación del bot para telegram

    # registrar manejadores (handlers) el orden importa, comandos primero, texto genérico despues, y el usuario haciendo cosas que no tocan al final
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("listar", listar))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler("borrar", borrar))
    app.add_handler(CommandHandler("exportar", exportar))
    app.add_handler(CommandHandler("filtrar", filtrar))

    app.add_handler(MessageHandler(filters.Document.ALL, recibir_pdf)) # PDFs
    app.add_handler(MessageHandler(filters.PHOTO, rechazar_foto)) # fotos
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_desconocido)) # texto normal
    app.add_handler(MessageHandler(filters.COMMAND, mensaje_desconocido)) # comandos desconocidos

    print("🤖 Bot arrancado. Esperando mensajes...")
    app.run_polling() # bucle infinito que escucha mensajes de Telegram

if __name__ == "__main__":
    main() 
    # ejecuta main() solo si se ejecuta directamente este fichero
    # pruebas