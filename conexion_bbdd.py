import sqlite3
from datetime import datetime

DB_PATH = "bbdd/facturas.db"  # ruta del fichero de la base de datos


def inicializar_bd():
    """
    crea la tabla 'facturas' si no existe todavía.
    llama una vez al arrancar el programa.
    """
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            comercio    TEXT,
            fecha       TEXT,
            total       TEXT,
            iva         TEXT,
            ruta_pdf    TEXT,
            fecha_carga TEXT
        )
    """)
    conexion.commit()
    conexion.close()


def guardar_factura(datos: dict, ruta_pdf: str):
    """
    inserta una factura en la base de datos.
    'datos' es el return que devuelve extraer_datos_factura()
    en pdf_parser.py
    """
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO facturas (comercio, fecha, total, iva, ruta_pdf, fecha_carga)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datos.get("comercio"),
        datos.get("fecha"),
        datos.get("total"),
        datos.get("iva"),
        ruta_pdf,
        datetime.now().strftime("%d/%m/%Y %H:%M") #formato de la fecha y hora en la que se ha metido el registro
    ))
    conexion.commit()
    conexion.close()


def listar_facturas() -> list:
    """
    devuelverá todas las facturas guardadas como lista en un diccionarios.
    usar el diccionario en lugar de tuplas hace el código más legible para mi.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row  # permite acceder por nombre de columna
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM facturas ORDER BY id DESC")
    filas = cursor.fetchall()
    conexion.close()
    return [dict(fila) for fila in filas]
