
# -> !! RECORDAR: handler es "cuando pase esto, haz esto" y hay que añadirlos al crearlos al final si no caca
# el bot esta preguntando siempre en telegram: ¿me estan escribiendo? esto = "polling"
# 11/03/26 -> investigar sobre si es posible generar un archivo (.csv, a ser posible) 
# con las facturas que esten en la base de datos , añadir un filtro de fechas (/entre 01/01/2025 31/01/2025)
# que muestre (o sume) en ese perieodo

from dotenv import load_dotenv
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pdf_parser import extraer_datos_factura
from conexion_bbdd import inicializar_bd, guardar_factura, borrar_factura, buscar_por_comercio, obtener_ultimas_facturas, obtener_total_facturas

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


###### COMANDO BIENVENIDA ######
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): #async permite que varios usuarios puedan usar el bot a la vez
    await update.message.reply_text( # -> si alguien en tu chat escribe "/start, di esto"
        "👋 ¡Hola! Soy BusinessTripBook.\n\n"
        "Envíame una factura en PDF y extraeré automáticamente:\n"
        "📅 Fecha\n💶 Total\n🏪 Comercio\n📊 IVA\n\n"
        "¡Solo tienes que enviarme el archivo!\n"
        "Si no sabes como hablar conmigo, escribe /ayuda"
    )

################ COMANDOS UTILES ######################

async def listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    facturas = obtener_ultimas_facturas(5)

    if not facturas:
        await update.message.reply_text("📭 Todavía no hay facturas guardadas.")
        return

    lineas = ["📋 *Últimas facturas guardadas:*", ""]
    for f in facturas:
        linea = f"• [{f['id']}] {f['fecha'] or 'Sin fecha'} – {f['comercio'] or 'Sin comercio'} – {f['total'] or '?'} €"
        lineas.append(linea)

    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text( # -> si alguien en tu chat escribe "/ayuda, di esto"
        "📖 *Comandos disponibles:*\n\n"
        "📎 /start → Mensaje de bienvenida\n"
        "📋 /listar → Ver tus últimas facturas\n"
        "💶 /total → Suma total de todas tus facturas\n"
        "🔍 /buscar [nombre] → Buscar por comercio\n"
        "🗑️ /borrar [id] → Eliminar una factura\n"
        "❓ /ayuda → Ver esta ayuda\n\n"
        "📄 También puedes enviarme directamente un PDF para procesarlo.",
        parse_mode="Markdown" #-> para negritas con *
    )


async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    suma = obtener_total_facturas()
    mensaje = f"💶 El importe total acumulado de tus facturas es: *{suma:.2f} €*"
    await update.message.reply_text(mensaje, parse_mode="Markdown")


async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🔍 Uso: /buscar nombre_comercio\nEjemplo: /buscar mercadona")
        return

    texto_busqueda = " ".join(context.args)
    resultados = buscar_por_comercio(texto_busqueda)

    if not resultados:
        await update.message.reply_text(f"❌ No se han encontrado facturas para: *{texto_busqueda}*", parse_mode="Markdown")
        return

    lineas = [f"🔍 *Resultados para* `{texto_busqueda}`:", ""]
    for f in resultados[:10]:
        linea = f"• [{f['id']}]: {f['fecha'] or 'Sin fecha'} – {f['comercio'] or 'Sin comercio'} – {f['total'] or '?'} €"
        lineas.append(linea)

    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


async def borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🗑️ Uso: /borrar id\nEjemplo: /borrar 3")
        return

    try:
        id_factura = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ El id debe ser un número. Ejemplo: /borrar 3")
        return

    if borrar_factura(id_factura):
        await update.message.reply_text(f"✅ Factura con id {id_factura} borrada correctamente.")
    else:
        await update.message.reply_text(f"❌ No se ha encontrado ninguna factura con id {id_factura}.")


############# COSAS QUE EL USUARIO PUEDE HACER Y HAY QUE EVITAR ###########################

# si el usuario enviase una foto al chat:

async def rechazar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ Has enviado una imagen.\n\n"
        "Este bot solo procesa facturas en formato *PDF*.\n"
        "Por favor, envía el fichero PDF directamente.",
        parse_mode="Markdown"
    )


# si el usuario escribe cualquier cosa que no sea un comando conocido

async def mensaje_desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ No entiendo ese mensaje.\n" # -> di esto si te dicen algo escrito en el chat
        "Usa /ayuda para ver los comandos disponibles."
    )


# cuando se reciba un archivo:
async def recibir_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    documento = update.message.document

    # comprobar que el archivo es un PDF
    if documento.mime_type != "application/pdf":
        await update.message.reply_text("⚠️ Por favor, envíame solo archivos PDF.")
        return

    # cuando el pdf se envie, automaticamente enviar esto (este bien o no)
    await update.message.reply_text("⏳ Procesando tu factura...")

    # descargar el PDF a una carpeta local para que el codigo pueda procesarlo
    archivo = await documento.get_file()
    ruta_local = os.path.join("facturas", documento.file_name)
    await archivo.download_to_drive(ruta_local)

    # extraer datos y guardar en bbdd/facturasd.db
    try:
        datos = extraer_datos_factura(ruta_local)
        guardar_factura(datos, ruta_local)

    # mostrar datos
        respuesta = (
            f"✅ Factura guardada correctamente\n\n"
            f"🏪 Comercio: {datos.get('comercio') or 'No encontrado'}\n"
            f"🗓️​ Fecha: {datos.get('fecha') or 'No encontrada'}\n"
            f"💶 Total: {datos.get('total') or 'No encontrado'} €\n"
            f"📊 IVA: {datos.get('iva') or 'No encontrado'}"
        )
    except ValueError:
        respuesta = "❌ No se pudo procesar el PDF. Asegúrate de que no sea un PDF escaneado." # -> si te envian un pdf en foto di esto

    await update.message.reply_text(respuesta)

def main():
    load_dotenv()
    TOKEN = os.getenv("TOKEN") # -> carga el token del bot

    os.makedirs("facturas", exist_ok=True)

    inicializar_bd()  # crea la tabla si no existe

    app = Application.builder().token(TOKEN).build() # -> llama a los handlers "en nombre" del token del bot

    # registrar manejadores (handlers)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("listar", listar))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler("borrar", borrar))

    app.add_handler(MessageHandler(filters.Document.ALL, recibir_pdf))
    app.add_handler(MessageHandler(filters.PHOTO, rechazar_foto))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_desconocido))



    print("🤖 Bot arrancado. Esperando mensajes...")
    app.run_polling()  # empieza el bucle de escucha aplicando todo lo anterior


if __name__ == "__main__":
    main()