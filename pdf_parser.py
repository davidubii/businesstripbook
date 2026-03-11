from pypdf import PdfReader
import re


# ruta_pdf es la ruta del fichero PDF de la factura
def _extraer_texto(ruta_pdf: str) -> str:
    """
    abre el PDF y devuelve todo su texto como un único string.
    si el PDF no tiene texto (es solo imagen), devuelve cadena vacía.
    esta función se marca como privada (empieza por _) porque solo la va a usar extraer_datos_factura.
    """
    reader = PdfReader(ruta_pdf)  # abre el PDF con la librería pypdf
    texto_completo = ""
    for pagina in reader.pages:   # algunas facturas pueden tener varias páginas
        texto_completo += pagina.extract_text() or ""  # or "" evita None al concatenar
    return texto_completo


def _buscar_fecha(texto: str) -> str | None:
    """
    busca fechas en formato dd/mm/aaaa o dd-mm-aaaa en todo el texto.
    re.search() devuelve el primer resultado encontrado (suficiente para facturas).
    """
    # \b = límite de palabra, (\d{1,2}[/\-]\d{1,2}[/\-]\d{4}) = patrón de fecha
    patron = r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b'
    resultado = re.search(patron, texto)  # busca en todo el texto
    return resultado.group(1) if resultado else None  # group(1) = el texto capturado entre paréntesis


def _buscar_importe_total(texto: str) -> str | None:
    """
    busca la línea que contenga 'Total' seguida de un número con decimales.
    re.IGNORECASE = no distingue mayúsculas/minúsculas ('TOTAL', 'Total', 'total').
    """
    # [Tt]otal = 'T' o 't' seguido de 'otal'
    # [^\d]* = cualquier carácter que no sea dígito (espacios, dos puntos...)
    # ([\d.,]+) = captura números con coma o punto decimal
    # \s*€? = espacios opcionales y € opcional
    patron = r'[Tt]otal[^\d]*([\d.,]+)\s*€?'
    resultado = re.search(patron, texto, re.IGNORECASE)
    return resultado.group(1) if resultado else None


def _buscar_iva(texto: str) -> str | None:
    """
    busca el porcentaje de IVA con dos patrones posibles:
    1. IVA (21%) → captura el número entre paréntesis.
    2. IVA 21%   → captura el número seguido de %.
    """
    # IVA seguido de 0-10 caracteres no numéricos, luego el número y %
    patron = r'IVA\D{0,10}(\d{1,2})\s*%'
    resultado = re.search(patron, texto, re.IGNORECASE)
    return resultado.group(1) + "%" if resultado else None  # añade el % al resultado


def _buscar_comercio(texto: str) -> str | None:
    """
    estrategia en dos pasos:
    1. buscar campo explícito ('Razón social:', 'Proveedor:', etc.).
    2. si no, tomar la primera línea no vacía del texto (encabezado típico).
    """
    # intento 1: campo explícito (?:...) = grupo no capturador
    patron_explicito = r'(?:Razón social|Proveedor|Empresa|Emisor)\s*[:\-]?\s*(.+)'
    resultado = re.search(patron_explicito, texto, re.IGNORECASE)
    if resultado:
        return resultado.group(1).strip()  # strip() quita espacios al inicio/final

    # intento 2: primera línea no vacía (normalmente el nombre del comercio)
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea:  # si no está vacía
            return linea

    return None  # si no se encontró nada


def extraer_datos_factura(ruta_pdf: str) -> dict:
    """
    función principal pública que el resto del programa llama directamente.
    1. extrae todo el texto del PDF.
    2. busca cada campo clave con sus funciones específicas.
    3. devuelve un diccionario con los datos encontrados.
    """
    texto = _extraer_texto(ruta_pdf)

    # si no hay texto, el PDF es probablemente una imagen
    if not texto.strip():
        raise ValueError(
            f"No se pudo extraer texto del PDF: {ruta_pdf}. "
            "El archivo puede ser un PDF de imagen (no soportado)."
        )

    # diccionario con todos los datos extraídos (None si no se encontró)
    datos = {
        "fecha":    _buscar_fecha(texto),
        "total":    _buscar_importe_total(texto),
        "iva":      _buscar_iva(texto),
        "comercio": _buscar_comercio(texto),
    }

    return datos
