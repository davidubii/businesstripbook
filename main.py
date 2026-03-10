from pdf_parser import extraer_datos_factura
from conexion_bbdd import inicializar_bd, guardar_factura, listar_facturas

if __name__ == "__main__":
    inicializar_bd()  # crea la tabla si no existe

    ruta = "facturas en pdf/factura_ejemplo.pdf"

    try:
        datos = extraer_datos_factura(ruta)
        print("Datos extraídos:", datos)

        guardar_factura(datos, ruta)
        print("La factura ha sido guardada en la base de datos")

        print("\nFacturas en la base de datos:")
        for f in listar_facturas():
            print(f" - [{f['id']}] {f['comercio']} | {f['fecha']} | {f['total']} €")

    except ValueError as e:
        print(f"Error: {e}")

