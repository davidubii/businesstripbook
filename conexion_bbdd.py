import sqlite3
from datetime import datetime
import os

# esto calcula la ruta absoluta sin q importe dónde esté ejecutándose el programa
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "facturas.db")

def inicializar_bd():
    os.makedirs(BASE_DIR, exist_ok=True)  # asegura que el directorio existe. si existe, no crea nada y lo abre:
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
    # los ???? son parametrizacion, para evtar ataques de inyeccion SQL. 
    # aunque no haya riesgo real mola decirlo y tal
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
        datos.get("iva"), # datos, es el return que da pdf_parser
        ruta_pdf,
        datetime.now().strftime("%d/%m/%Y %H:%M") # formato de la fecha y hora en la que se ha metido el registro
    ))
    conexion.commit()
    conexion.close()


def listar_facturas() -> list:
    """
    devuelverá todas las facturas guardadas como lista en un diccionarios.
    usar el diccionario hace el código más legible para mi.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row  # permite acceder por nombre de columna
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM facturas ORDER BY id DESC")
    filas = cursor.fetchall()
    conexion.close()
    return [dict(fila) for fila in filas]

def obtener_ultimas_facturas(limite: int = 5) -> list[dict]:
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT id, comercio, fecha, total FROM facturas ORDER BY id DESC LIMIT ?",
        (limite,)
    )
    filas = cursor.fetchall()
    conexion.close()
    return [dict(f) for f in filas]

def obtener_total_facturas() -> float:
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("SELECT total FROM facturas")
    filas = cursor.fetchall()
    conexion.close()

    total = 0.0
    for (importe_str,) in filas:
        if not importe_str:
            continue
        importe_str = importe_str.replace(".", "").replace(",", ".")
        try:
            total += float(importe_str)
        except ValueError:
            continue
    return total

def buscar_por_comercio(texto: str) -> list[dict]:
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    patron = f"%{texto}%"
    cursor.execute(
        "SELECT id, comercio, fecha, total FROM facturas WHERE comercio LIKE ? COLLATE NOCASE ORDER BY id DESC",
        (patron,)
    )
    filas = cursor.fetchall()
    conexion.close()
    return [dict(f) for f in filas]



