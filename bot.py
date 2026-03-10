
# -> !! RECORDAR: handler es "cuando pase esto, haz esto"
# el bot esta preguntando siempre en telegram: ¿me estan escribiendo? esto = "polling"
# 10/03/26 -> agregar manejo de fallos del bot, ortografia, añadir la funcion de ayuda 
# e investigar Railway, tambien mirar sobre como rechazar fotos o archivos que no toquen
# arreglar error de ubicacion del .db

from dotenv import load_dotenv
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pdf_parser import extraer_datos_factura
from conexion_bbdd import inicializar_bd, guardar_factura

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): #async permite que varios usuarios puedan usar el bot a la vez
    await update.message.reply_text( # -> si alguien en tu chat escribe "/start, di esto"
        "👋 ¡Hola! Soy BusinessTripBook.\n\n"
        "Envíame una factura en PDF y extraeré automáticamente:\n"
        "📅 Fecha\n💶 Total\n🏪 Comercio\n📊 IVA\n\n"
        "¡Solo tienes que enviarme el archivo!"
    )

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

async def rechazar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ Has enviado una imagen.\n\n"
        "Este bot solo procesa facturas en formato *PDF*.\n"
        "Por favor, envía el fichero PDF directamente.",
        parse_mode="Markdown"
    )


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
    app.add_handler(MessageHandler(filters.Document.ALL, recibir_pdf))
    app.add_handler(MessageHandler(filters.PHOTO, rechazar_foto))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_desconocido))  # siempre el último



    print("🤖 Bot arrancado. Esperando mensajes...")
    app.run_polling()  # empieza el bucle de escucha aplicando todo lo anterior


if __name__ == "__main__":
    main()
