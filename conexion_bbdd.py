import sqlite3
from datetime import datetime
import os
import csv


# esto calcula la ruta absoluta sin q importe dónde esté ejecutándose el programa
# __file__ es la ruta del archivo actual, dirname saca la carpeta y abspath la hace absoluta
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # carpeta donde está este archivo Python
DB_PATH = os.path.join(BASE_DIR, "facturas.db")  # ruta completa al fichero de la base de datos


def inicializar_bd():
    # crea la carpeta si no existe (exist_ok=True evita errores si ya existe)
    os.makedirs(BASE_DIR, exist_ok=True)  
    
    # abre la base de datos (si no existe, la crea)
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()  # cursor = herramienta para ejecutar comandos SQL
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,  # ID único que se genera automáticamente
            comercio    TEXT,   # nombre del comercio/establecimiento
            fecha       TEXT,   # fecha de la factura (formato dd/mm/aaaa)
            total       TEXT,   # importe total (texto porque puede tener comas/puntos)
            iva         TEXT,   # IVA (ej: "21%")
            ruta_pdf    TEXT,   # ruta del fichero PDF original
            fecha_carga TEXT    # cuándo se procesó la factura (dd/mm/aaaa HH:MM)
        ) 
    """)
    
    conexion.commit()  # confirma y guarda los cambios
    conexion.close()   # cierra la conexión 


def guardar_factura(datos: dict, ruta_pdf: str):
    """
    Inserta una factura en la base de datos.
    'datos' es el diccionario que devuelve extraer_datos_factura() de pdf_parser.py.
    Los ? son parametrización para evitar ataques SQL injection (buena práctica).
    """
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    
    cursor.execute(""" 
        INSERT INTO facturas (comercio, fecha, total, iva, ruta_pdf, fecha_carga)
        VALUES (?, ?, ?, ?, ?, ?) 
    """, (
        datos.get("comercio"),    # si no existe el campo, devuelve None
        datos.get("fecha"),
        datos.get("total"),
        datos.get("iva"),
        ruta_pdf,                 # ruta del PDF en el disco
        datetime.now().strftime("%d/%m/%Y %H:%M")  # fecha y hora actual
    ))
    
    conexion.commit()
    conexion.close()


def listar_facturas() -> list:
    """
    Devuelve TODAS las facturas guardadas como lista de diccionarios.
    Los diccionarios son más legibles que las tuplas de sqlite3.Row.
    ORDER BY id DESC → las más recientes primero.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row  # permite acceder por nombre de columna
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM facturas ORDER BY id DESC")
    filas = cursor.fetchall()  # fetchall() = todas las filas
    conexion.close()
    return [dict(fila) for fila in filas]  # convierte cada columna en dict


def obtener_ultimas_facturas(limite: int = 5) -> list[dict]:
    """
    Devuelve las últimas N facturas (por defecto 5).
    LIMIT ? es lo que limita el número de filas devueltas.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT id, comercio, fecha, total FROM facturas ORDER BY id DESC LIMIT ?",
        (limite,)  # tupla de un solo elemento necesita coma final
    )
    filas = cursor.fetchall()
    conexion.close()
    return [dict(f) for f in filas]


def obtener_total_facturas() -> float:
    """
    Suma el importe total de TODAS las facturas en la base de datos.
    """
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("SELECT total FROM facturas")  # solo la columna total
    filas = cursor.fetchall()
    conexion.close()

    total = 0.0 
    for (importe_str,) in filas:  # dividde la tupla (importe_str,)
        if not importe_str:  # si está vacío, pasa al siguiente
            continue 
        # cambia el formato ya que en españa se suele usar mucho la coma en los recibos: "77,44" → "77.44"
        importe_str = importe_str.replace(".", "").replace(",", ".") 
        try:
            total += float(importe_str)  # suma si se puede convertir a número
        except ValueError:
            continue  # si no es un número válido, lo ignora
    return total 


def buscar_por_comercio(texto: str) -> list[dict]:
    """
    Busca facturas cuyo 'comercio' contenga el texto introducido.
    %texto% = patrón SQL LIKE (contiene en cualquier parte).
    COLLATE NOCASE = búsqueda sin distinguir mayúsculas/minúsculas.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    patron = f"%{texto}%"  # patrón que introduce el usuario para el LIKE
    cursor.execute(
        "SELECT id, comercio, fecha, total FROM facturas WHERE comercio LIKE ? COLLATE NOCASE ORDER BY id DESC",
        (patron,)
    )
    filas = cursor.fetchall()
    conexion.close()
    return [dict(f) for f in filas]


def borrar_factura(id_factura: int) -> bool:
    """
    Borra la factura con el ID especificado.
    Devuelve True si se borró algo, False si no existía.
    """
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM facturas WHERE id = ?", (id_factura,))
    cambios = cursor.rowcount  # número de filas afectadas (0 o 1)
    conexion.commit()
    conexion.close()
    return cambios > 0  # solo es true si borró algo


def exportar_facturas_a_csv(ruta_csv: str) -> str:
    """
    Exporta todas las facturas a un fichero CSV.
    Devuelve la ruta del fichero generado.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM facturas ORDER BY id ASC")  # ASC = de más antigua a más reciente
    filas = cursor.fetchall()
    conexion.close()

    campos = filas[0].keys() if filas else []  # encabezados de las columnas

    # crear CSV con encabezados y datos
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)  # writer preparado para diccionarios, que es lo que he usado en el codigo para mostrar datos
        writer.writeheader()  # escribe la primera línea con nombres de columnas
        for fila in filas:
            writer.writerow(dict(fila))  # escribe cada fila como diccionario

    return ruta_csv # -> devuelve la ruta del CSV
