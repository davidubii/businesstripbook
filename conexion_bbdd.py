import sqlite3
from datetime import datetime
import os
import csv

# SQLite usa /* */ o -- para comentarios SQL, no """ <-- RECORDAR IMPORTANTE
# __file__ es la ruta del archivo actual, dirname saca la carpeta y abspath la hace absoluta
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # carpeta donde está este archivo python
DB_PATH = os.path.join(BASE_DIR, "bbdd/facturas.db") # ruta completa al fichero de la base de datos
# esto calcula la ruta absoluta sin q importe dónde esté ejecutándose el programa

def inicializar_bd():
    os.makedirs(BASE_DIR, exist_ok=True)

    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS facturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        comercio TEXT,
        fecha TEXT,
        total TEXT,
        iva TEXT,
        ruta_pdf TEXT,
        fecha_carga TEXT
    ) 
    """)

    # aquí se establecen las columnas de la base de datos, y que tipo de dato reciben
    # ("TEXT = string", el id se pone un número que incrementa en cada insert que se hace.).

    # comprobación extra: si la tabla ya existía de antes, puede no tener aún la columna chat_id.
    cursor.execute("PRAGMA table_info(facturas)")
    columnas = [fila[1] for fila in cursor.fetchall()]
    if "chat_id" not in columnas:
        cursor.execute(
            "ALTER TABLE facturas ADD COLUMN chat_id INTEGER"
        )

    # reseteo de emergencia del contador de ids:
    # si la tabla está vacía pero sqlite_sequence aún recuerda un id anterior (por ejemplo, seq=1),
    # el primer insert daría id=2 en vez de id=1. al borrar la entrada, SQLite empieza desde 0+1=1.
    cursor.execute("SELECT COUNT(*) FROM facturas")
    if cursor.fetchone()[0] == 0:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'facturas'")

    conexion.commit()
    conexion.close()


def guardar_factura(datos: dict, ruta_pdf: str, chat_id: int):
    """
    inserta una factura en la base de datos.
    'datos' es el diccionario que devuelve extraer_datos_factura() de pdf_parser.py.
    los ? son parametrización para evitar ataques SQL injection (se supone que es buena práctica).
    """
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()

    # se añade chat_id para ligar cada factura al chat concreto de Telegram (multiusuario).
    cursor.execute(""" 
    INSERT INTO facturas (chat_id, comercio, fecha, total, iva, ruta_pdf, fecha_carga)
    VALUES (?, ?, ?, ?, ?, ?, ?) 
    """, (
        chat_id,  # primer valor: identifica a qué chat pertenece esta factura
        datos.get("comercio"),  # si no existe el campo, devuelve None
        datos.get("fecha"),
        datos.get("total"),
        datos.get("iva"),
        ruta_pdf,  # ruta del PDF en el disco
        datetime.now().strftime("%d/%m/%Y %H:%M")  # fecha y hora actual
    ))

    conexion.commit()
    nuevo_id = cursor.lastrowid
    conexion.close()
    return nuevo_id


def listar_facturas(chat_id: int) -> list:
    """
    devuelve TODAS las facturas guardadas como lista de diccionarios.
    los diccionarios son más legibles que las tuplas de sqlite3.Row.
    ORDER BY id DESC → las más recientes primero.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row  # permite acceder por nombre de columna
    cursor = conexion.cursor()
    # se filtra por chat_id para que cada chat solo vea sus propias facturas
    cursor.execute(
        "SELECT * FROM facturas WHERE chat_id = ? ORDER BY id DESC",
        (chat_id,)
    )
    filas = cursor.fetchall()  # fetchall() = todas las filas
    conexion.close()
    return [dict(fila) for fila in filas]  # convierte cada columna en dict


def obtener_ultimas_facturas(chat_id: int, limite: int = 5) -> list[dict]:
    """
    devuelve las últimas N facturas (por defecto 5).
    LIMIT ? es lo que limita el número de filas devueltas.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    # mismo patrón: se filtra por chat_id y luego se limita el número de filas
    cursor.execute(
        "SELECT id, comercio, fecha, total FROM facturas "
        "WHERE chat_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (chat_id, limite)  # primero el chat_id, luego el límite
    )
    filas = cursor.fetchall()
    conexion.close()
    return [dict(f) for f in filas]


def filtrar_facturas_por_fecha(fecha_inicio: str, fecha_fin: str, chat_id: int) -> list[dict]:
    """
    Devuelve facturas cuya fecha esté entre fecha_inicio y fecha_fin (inclusive).
    Las fechas deben pasarse en formato dd/mm/yyyy.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()

    # sqLite no entiende dd/mm/yyyy para comparar rangos.
    # hay que reorganizar la fecha a yyyy-mm-dd con substr() para que la comparación funcione.
    # además se añade chat_id al WHERE para que solo se tengan en cuenta las facturas de ese chat.
    cursor.execute("""
    SELECT * FROM facturas
    WHERE chat_id = ?
      AND substr(fecha, 7, 4) || '-' || substr(fecha, 4, 2) || '-' || substr(fecha, 1, 2)
          BETWEEN ? AND ?
    ORDER BY substr(fecha, 7, 4) || substr(fecha, 4, 2) || substr(fecha, 1, 2) ASC
    """, (chat_id, convertir_fecha(fecha_inicio), convertir_fecha(fecha_fin)))

    filas = cursor.fetchall()
    conexion.close()
    return [dict(fila) for fila in filas]


def convertir_fecha(fecha_ddmmyyyy: str) -> str:
    """
    convierte 'dd/mm/yyyy' a 'yyyy-mm-dd' para comparaciones en SQLite.
    """
    partes = fecha_ddmmyyyy.strip().split("/")
    return f"{partes[2]}-{partes[1]}-{partes[0]}"


def obtener_total_facturas(chat_id: int) -> float:
    """
    suma el importe total de TODAS las facturas en la base de datos.
    """
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    # solo se seleccionan los totales del chat actual
    cursor.execute(
        "SELECT total FROM facturas WHERE chat_id = ?",  # solo la columna total
        (chat_id,)
    )
    filas = cursor.fetchall()
    conexion.close()

    total = 0.0
    for (importe_str,) in filas:  # dividde la tupla (importe_str,)
        if not importe_str:  # si está vacío, pasa al siguiente
            continue
        importe_str = importe_str.replace(".", "").replace(",", ".")  # se cambia el formato ya que en españa se suele usar mucho la coma en los recibos: "77,44" → "77.44"
        try:
            total += float(importe_str)  # suma si se puede convertir a número
        except ValueError:
            continue  # si no es un número válido, lo ignora
    return total


def buscar_por_comercio(texto: str, chat_id: int) -> list[dict]:
    """
    busca facturas cuyo 'comercio' contenga el texto introducido.
    %texto% = patrón SQL LIKE (contiene en cualquier parte).
    COLLATE NOCASE = búsqueda sin distinguir mayúsculas/minúsculas.
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    patron = f"%{texto}%"  # patrón que introduce el usuario para el LIKE
    # se añade chat_id al WHERE para que cada chat solo busque en sus propias facturas
    cursor.execute(
        "SELECT id, comercio, fecha, total FROM facturas "
        "WHERE comercio LIKE ? COLLATE NOCASE AND chat_id = ? "
        "ORDER BY id DESC",
        (patron, chat_id)
    )
    filas = cursor.fetchall()
    conexion.close()
    return [dict(f) for f in filas]


def borrar_factura(id_factura: int, chat_id: int) -> bool:
    """
    borra la factura con el ID especificado.
    devuelve True si se borró algo, False si no existía.
    tras el borrado, reajusta el contador de IDs para que sean consecutivos.
    """
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    # solo se borra la factura si pertenece al chat indicado
    cursor.execute(
        "DELETE FROM facturas WHERE id = ? AND chat_id = ?",
        (id_factura, chat_id)
    )
    cambios = cursor.rowcount  # número de filas afectadas (0 o 1)

    if cambios > 0:
        # obtener el máximo id actual (0 si la tabla está vacía)
        cursor.execute("SELECT MAX(id) FROM facturas")
        max_id = cursor.fetchone()[0] or 0

        if max_id == 0:
            # si la tabla quedó vacía, se elimina completamente el registro de sqlite_sequence.
            # así SQLite no tiene ningún valor previo y el próximo insert empieza desde 1.
            # hacer UPDATE a 0 no es suficiente: si la entrada ya tenía seq=1, SQLite devuelve id=2.
            cursor.execute(
                "DELETE FROM sqlite_sequence WHERE name = 'facturas'"
            )
        else:
            # si aún quedan facturas, se actualiza el contador al máximo id existente
            cursor.execute(
                "UPDATE sqlite_sequence SET seq = ? WHERE name = 'facturas'",
                (max_id,)
            )

    conexion.commit()
    conexion.close()
    return cambios > 0


def exportar_facturas_a_csv_v3(ruta_csv: str, chat_id: int) -> str:
    """
    exporta todas las facturas a un fichero CSV.
    devuelve la ruta del fichero generado.
    (beta, se puede mejorar)
    """
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    # se exportan solo las facturas del chat actual para que cada usuario tenga su propio CSV
    cursor.execute(
        "SELECT * FROM facturas WHERE chat_id = ? ORDER BY id ASC",  # ASC = ASCendente = de más antigua a más reciente
        (chat_id,)
    )
    filas = cursor.fetchall()
    conexion.close()

    campos = filas[0].keys() if filas else []  # encabezados de las columnas

    # crear CSV con encabezados y datos
    with open(ruta_csv, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig para que Excel reconozca la codificación
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=";")  # ; como separador para Excel en español
        writer.writeheader()  # escribe la primera línea con nombres de columnas
        for fila in filas:
            writer.writerow(dict(fila))  # escribe cada fila como diccionario

    return ruta_csv  # -> devuelve la ruta del CSV
