from pypdf import PdfReader
import re

#ruta_pdf es la factura


def _extraer_texto(ruta_pdf: str) -> str:
    """
    abre el PDF y devuelve todo su texto como un único string.
    si el PDF no tiene texto (es solo imagen), devuelve cadena vacía. (será no valido)
    """ # -> indicar en la funcion de prueba que sería no valido
    reader = PdfReader(ruta_pdf)
    texto_completo = ""
    for pagina in reader.pages:
        texto_completo += pagina.extract_text() or ""
    return texto_completo


def _buscar_fecha(texto: str) -> str | None:
    """
    bbuscaremos fechas en formato dd/mm/aaaa o dd-mm-aaaa.
    re.search() devuelve el primer resultado encontrado en todo el texto.
    """
    patron = r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b'
    resultado = re.search(patron, texto)
    return resultado.group(1) if resultado else None


def _buscar_importe_total(texto: str) -> str | None:
    """
    busca la línea que contenga 'Total' seguida de un número con decimales.
    re.IGNORECASE hace que no importe si está escrito 'TOTAL', 'total', etc.
    El patrón captura números con coma o punto (ej: 121,00 o 121.00).
    """
    patron = r'[Tt]otal[^\d]*([\d.,]+)\s*€?'
    resultado = re.search(patron, texto, re.IGNORECASE)
    return resultado.group(1) if resultado else None


def _buscar_iva(texto: str) -> str | None:
    """
    busca el porcentaje de IVA. hay dos posibilidades:
    1. IVA (21%) → captura el porcentaje entre paréntesis.
    2. IVA 21%   → captura el número seguido de %.
    """
    patron = r'IVA\D{0,10}(\d{1,2})\s*%'
    resultado = re.search(patron, texto, re.IGNORECASE)
    return resultado.group(1) + "%" if resultado else None


def _buscar_comercio(texto: str) -> str | None:
    """
    la primera línea del texto suele ser el nombre
    del negocio (razón social o nombre comercial en el encabezado),
    entonces si el PDF tiene el campo 'razón social:' o 'proveedor:', lo buscamos primero.
    """
    # intento 1: buscar campo explícito
    patron_explicito = r'(?:Razón social|Proveedor|Empresa|Emisor)\s*[:\-]?\s*(.+)'
    resultado = re.search(patron_explicito, texto, re.IGNORECASE)
    if resultado:
        return resultado.group(1).strip()

    # intento 2: primera línea no vacía del texto
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea:
            return linea

    return None


def extraer_datos_factura(ruta_pdf: str) -> dict:
    texto = _extraer_texto(ruta_pdf)

    if not texto.strip():
        raise ValueError(
            f"No se pudo extraer texto del PDF: {ruta_pdf}. "
            "El archivo puede ser un PDF de imagen (no soportado aún)."
        )

    datos = {
        "fecha":    _buscar_fecha(texto),
        "total":    _buscar_importe_total(texto),
        "iva":      _buscar_iva(texto),
        "comercio": _buscar_comercio(texto),
    }

    return datos
