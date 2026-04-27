from fastapi import FastAPI
from pydantic import BaseModel #Validacion de datos
import pymysql
from fastapi.middleware.cors import CORSMiddleware  #Permiso para usar la API

app = FastAPI(title="Sistema Los Coyotes")

#Configuracion CORS (permisos)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://frontend-coyotes.onrender.com", "http://localhost:5173"], #Ruta del front
    allow_credentials=True,
    allow_methods=["*"], # Le permite usar GET, POST, PUT, PATCH y DELETE
    allow_headers=["*"], # Le permite enviar cualquier tipo de dato
)


#Configuracion base de datos
DB_CONFIG = {
    "host": "loscoyotes-jhafethyngaamado.g.aivencloud.com",
    "user": "avnadmin",
    "password": "AVNS_En5p-lP6JL2hokonXV1",
    "database": "defaultdb",
    "port": 17199
}

#Funcion para conectarse
def obtener_conexion():
    conexion = pymysql.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        port=DB_CONFIG["port"],
        cursorclass=pymysql.cursors.DictCursor
    )
    return conexion


#Molde para el catalogo general (BaseModel)
class Base_ModeloZapato(BaseModel):
    nombre: str
    categoria: str
    marca: str

#Molde para el zapato fisico en inventario (BaseModel)
class Base_VarianteZapato(BaseModel):
    modelo_id: int
    color: str
    talla: str
    precio: float
    stock: int

class ActualizarDatos(BaseModel):
    #Datos del modelo (Objeto general)
    nombre: str
    categoria: str
    marca: str

    #Datos de la variante (Objeto fisico)
    talla: str
    color: str
    precio: float
    stock: int


@app.get("/")
def root():
    return {
        "estado": "Operativo",
        "mensaje": "El servidor está funcionando correctamente."
    }


#Conexion a la base de datos
@app.get('/conexion')
def probar_conexion():
    try:
        conexion = obtener_conexion()
        conexion.close()
        return {"estado": "Éxito", "mensaje": "¡Conectado a MySQL en la nube correctamente!"}
    except Exception as e:
        return {"estado": "Error", "mensaje": f"Falló la conexión: {str(e)}"}


@app.post('/modelos')
def registrar_modelo(modelo:Base_ModeloZapato):
    try:
        #Abrimos la conexion 
        conexion = obtener_conexion() 
        cursor = conexion.cursor()

        #Buscar si el modelo ya existe exactamente igual
        sql_buscar = "SELECT id FROM zapatos_modelo WHERE nombre = %s AND marca = %s AND categoria = %s"
        cursor.execute(sql_buscar, (modelo.nombre, modelo.marca, modelo.categoria))
        modelo_existente = cursor.fetchone()

        if modelo_existente:
            # Si lo encuentra, NO inserta nada. Solo devuelve el ID que ya existía.
            return {
                "estado": "Éxito", 
                "mensaje": "Modelo existente encontrado", 
                "id_modelo": modelo_existente['id']
            }

        # Si no existe (modelo_existente es None), entonces sí lo creamos
        sql_insertar = "INSERT INTO zapatos_modelo (nombre, categoria, marca) VALUES (%s, %s, %s)"
        valores = (modelo.nombre, modelo.categoria, modelo.marca)

        #Ejecutamos y guardamos
        cursor.execute(sql_insertar, valores)
        conexion.commit()

        new_id = cursor.lastrowid

        return {"estado": "Éxito", "mensaje": "Modelo guardado", "id_modelo": new_id}
    except Exception as e:
        return {"estado": "Error", "mensaje": f"Error al guardar el modelo: {str(e)}"}
    finally:
        if 'conexion' in locals():
            conexion.close() # Siempre cerramos la puerta al salir


@app.post("/zapatos")
def registrar_zapato_fisico(variante: Base_VarianteZapato):
    try:
        #Conectamos
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        #Insertamos
        sql = "INSERT INTO zapatos_variante (modelo_id, talla, color, precio, stock) VALUES (%s, %s, %s, %s, %s)"
        valores = (variante.modelo_id, variante.talla, variante.color, variante.precio, variante.stock)

        #Ejecutamos y guardamos
        cursor.execute(sql, valores)
        conexion.commit()

        new_id = cursor.lastrowid

        return {"estado": "Éxito", "mensaje": "Zapato registrado", "id_variante": new_id}
    except Exception as e:
        return {"estado": "Error", "mensaje": f"Error al guardar el zapato: {str(e)}"}
    finally:
        if 'conexion' in locals():
            conexion.close()
        

@app.get("/zapatos")
def listar_zapatos():
    try:
        #Conectamos
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        #Unimos las tablas y fisltramos los activos y en stock
        sql = "SELECT v.id AS codigo, m.nombre, m.categoria, m.marca, v.talla, v.color, v.precio, v.stock FROM zapatos_variante v JOIN zapatos_modelo m ON v.modelo_id = m.id WHERE v.is_active = TRUE"

        cursor.execute(sql)
        zapatos_encontrados = cursor.fetchall()

        return {
            "estado": "Éxito",
            "cantidad": len(zapatos_encontrados),
            "catalogo": zapatos_encontrados
        }

    except Exception as e:
        return {"estado": "Error", "mensaje": f"Error al listar el catálogo: {str(e)}"}
    finally:
        if 'conexion' in locals():
            conexion.close()


@app.get("/zapatos/archivados")
def listar_zapatos_archivados():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # Aquí buscamos específicamente los que están "ocultos"
        sql = "SELECT v.id AS codigo, m.nombre, m.categoria, m.marca, v.talla, v.color, v.precio, v.stock FROM zapatos_variante v JOIN zapatos_modelo m ON v.modelo_id = m.id WHERE v.is_active = FALSE"

        cursor.execute(sql)
        archivados = cursor.fetchall()

        return {"estado": "Éxito", "cantidad": len(archivados), "archivados": archivados}
        
    except Exception as e:
        return {"estado": "Error", "mensaje": str(e)}
    finally:
        conexion.close()


@app.put("/zapatos/actualizar/{id_variante}")
def actualizar_zapato_inteligente(id_variante: int, datos: ActualizarDatos):
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # Verificamos si los nuevos datos generales ya existen en otro ID
        sql_buscar_modelo = """
            SELECT id FROM zapatos_modelo 
            WHERE nombre = %s AND marca = %s AND categoria = %s
        """
        cursor.execute(sql_buscar_modelo, (datos.nombre, datos.marca, datos.categoria))
        modelo_encontrado = cursor.fetchone()

        if modelo_encontrado:
            # Si ya existe un modelo así, tomamos ese ID
            id_modelo_final = modelo_encontrado['id']
        else:
            # Si es una combinación nueva, creamos un nuevo modelo padre
            sql_nuevo_modelo = "INSERT INTO zapatos_modelo (nombre, marca, categoria) VALUES (%s, %s, %s)"
            cursor.execute(sql_nuevo_modelo, (datos.nombre, datos.marca, datos.categoria))
            id_modelo_final = cursor.lastrowid

        # Reasignamos el modelo_id (por si cambió) y actualizamos los datos físicos
        sql_update_variante = """
            UPDATE zapatos_variante 
            SET modelo_id = %s, talla = %s, color = %s, precio = %s, stock = %s
            WHERE id = %s
        """
        valores_variante = (
            id_modelo_final, 
            datos.talla, 
            datos.color, 
            datos.precio, 
            datos.stock, 
            id_variante
        )
        cursor.execute(sql_update_variante, valores_variante)
        
        conexion.commit()
        return {"estado": "Éxito", "mensaje": "Producto actualizado con inteligencia relacional"}

    except Exception as e:
        return {"estado": "Error", "mensaje": f"Error en la edición inteligente: {str(e)}"}
    finally:
        if 'conexion' in locals():
            conexion.close()


@app.put("/zapatos/descontinuar/{id_variante}")
def descontinuar_zapato(id_variante: int):
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        sql = "UPDATE zapatos_variante SET is_active = FALSE WHERE id = %s"

        cursor.execute(sql, (id_variante,)) 
        conexion.commit()

        if cursor.rowcount == 0:
            return {"estado": "Error", "mensaje": "No se encontro ningun zapato con ese codigo"}
        
        return {"estado": "Exito", "mensaje": "El zapato ha sido descontinuado correctamente"} 
    
    except Exception as e:
        return {"estado": "Error", "mensaje": f"Error al descontinuar el zapato: {str(e)}"}
    finally:
        if 'conexion' in locals():
            conexion.close()


@app.patch("/zapatos/{id_variante}/reactivar")
def reactivar_zapato(id_variante: int):
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # Operación inversa a descontinuar
        sql = "UPDATE zapatos_variante SET is_active = TRUE WHERE id = %s"
        
        cursor.execute(sql, (id_variante,))
        conexion.commit()

        if cursor.rowcount == 0:
            return {"estado": "Error", "mensaje": "No se encontró el zapato"}

        return {"estado": "Éxito", "mensaje": "El zapato ha sido reactivado y volverá a aparecer en el catálogo"}
        
    except Exception as e:
        return {"estado": "Error", "mensaje": f"Error al reactivar: {str(e)}"}
    finally:
        conexion.close()

@app.put("/zapatos/vender/{id_variante}")
def registrar_venta(id_variante: int):
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        sql_venta = "UPDATE zapatos_variante SET stock = stock - 1 WHERE id = %s AND stock > 0"
        cursor.execute(sql_venta, (id_variante,))
        
        if cursor.rowcount == 0:
            return {"estado": "Error", "mensaje": "No hay stock suficiente para realizar la venta."}
        
        #sql_verificar = "SELECT stock FROM zapatos_variante WHERE id = %s"
        #cursor.execute(sql_verificar, (id_variante,))
        #resultado = cursor.fetchone()

        #if resultado and resultado['stock'] == 0:
        #    cursor.execute("UPDATE zapatos_variante SET is_active = FALSE WHERE id = %s", (id_variante,))
        #    mensaje = "¡Venta registrada! El producto se ha descontinuado automáticamente por falta de stock."
        #else:
        #    mensaje = "¡Venta registrada con éxito!"

        conexion.commit()
        return {"estado": "Éxito", "mensaje": "Venta realizada exitosamente"}

    except Exception as e:
        return {"estado": "Error", "mensaje": f"Error al registrar venta: {str(e)}"}
    finally:
        if 'conexion' in locals(): 
            conexion.close()

@app.delete("/zapatos/eliminar/{id_variante}/permanente")
def eliminar_zapato(id_variante: int):
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        sql = "DELETE FROM zapatos_variante WHERE id = %s"
        cursor.execute(sql, (id_variante,))
        conexion.commit()

        if cursor.rowcount == 0:
            return {"estado": "Error", "mensaje": "No se encontro ningun zapato con ese codigo"}
        
        return {"estado": "Exito", "mensaje": "El zapato ha sido eliminado correctamente"} 
    except Exception as e:
        return {"estado": "Error", "mensaje": f"Error al eliminar el zapato: {str(e)}"}
    finally:
        if 'conexion' in locals():
            conexion.close()
