from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

#       CONFIGURACIÓN Y CONEXIÓN A BD


def get_conexion():
    """
    Establece y devuelve la conexión a la base de datos MySQL.
    Se invoca dinámicamente en cada ruta para asegurar que no se queden
    conexiones colgadas o inactivas.
    """
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="",
        database="crm_preyecto3ev",
    )


#             BLOQUE: INICIO


@app.route("/")
def inicio():
    """
    Página principal del CRM (Dashboard).
    Muestra los 10 primeros clientes ordenados por su volumen de actividad 
    y calcula las métricas globales para los cuadros informativos superiores.
    """
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Consulta original: Top 10 clientes con más pedidos
    cursor.execute("""
        SELECT c.id_cliente, c.nombre, c.correo, c.telefono, c.direccion, 
               co.nombre as comercial, COUNT(p.id_pedido) as total_pedidos
        FROM clientes c
        JOIN comerciales co ON c.id_comercial = co.id_comercial
        LEFT JOIN pedidos p ON c.id_cliente = p.id_cliente
        GROUP BY c.id_cliente
        ORDER BY total_pedidos DESC
        LIMIT 10
    """)
    clientes = cursor.fetchall()
    
    # 2. Métrica: Total de clientes registrados en el sistema
    cursor.execute("SELECT COUNT(*) as total FROM clientes")
    total_clientes = cursor.fetchone()["total"]
    
    # 3. Métrica: Total de pedidos gestionados en el sistema
    cursor.execute("SELECT COUNT(*) as total FROM pedidos")
    total_pedidos = cursor.fetchone()["total"]
    
    # 4. Métrica: Total de dinero ingresado (Suma del importe_neto de facturas)
    cursor.execute("SELECT SUM(importe_neto) as total FROM facturas")
    resultado_facturacion = cursor.fetchone()["total"]
    # Si no hay facturas todavía, evitamos que devuelva None y ponemos 0
    total_facturado = resultado_facturacion if resultado_facturacion else 0.0
    
    cursor.close()
    conn.close()
    
    # Enviamos los datos del top de clientes y los tres contadores al HTML
    return render_template(
        "index.html", 
        clientes=clientes, 
        total_clientes=total_clientes, 
        total_pedidos=total_pedidos, 
        total_facturado=total_facturado
    )


#            BLOQUE: CLIENTES


@app.route("/clientes")
def clientes():
    """
    Sub-bloque: Listar Clientes
    Muestra la totalidad de los clientes registrados en el CRM junto
    con el nombre del comercial que los gestiona.
    """
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.id_cliente, c.nombre, c.correo, c.telefono, c.direccion, co.nombre as comercial
        FROM clientes c
        JOIN comerciales co ON c.id_comercial = co.id_comercial
    """)
    clientes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("clientes.html", clientes=clientes)


@app.route("/añadir", methods=["POST"])
def añadir_cliente():
    """
    Sub-bloque: Crear Cliente
    Recibe por POST los datos del formulario de registro de clientes
    e inserta una nueva fila en la tabla 'clientes'.
    """
    nombre = request.form["nombre"]
    correo = request.form["correo"]
    telefono = request.form["telefono"]
    direccion = request.form["direccion"]
    id_comercial = request.form["id_comercial"]

    conn = get_conexion()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clientes (nombre, correo, telefono, direccion, id_comercial) VALUES (%s, %s, %s, %s, %s)",
        (nombre, correo, telefono, direccion, id_comercial),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("inicio"))


@app.route("/editar/<int:id_cliente>")
def editar_form(id_cliente):
    """
    Sub-bloque: Formulario de Edición
    Busca los datos actuales de un cliente por su ID y renderiza la vista
    'editar.html' con los campos ya autorrellenados.
    """
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clientes WHERE id_cliente = %s", (id_cliente,))
    cliente = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("editar.html", cliente=cliente)


@app.route("/editar/<int:id_cliente>", methods=["POST"])
def editar_cliente(id_cliente):
    """
    Sub-bloque: Actualizar Cliente
    Procesa el envío del formulario de edición y ejecuta un UPDATE en la
    base de datos para guardar los cambios del cliente.
    """
    nombre = request.form["nombre"]
    correo = request.form["correo"]
    telefono = request.form["telefono"]
    direccion = request.form["direccion"]

    conn = get_conexion()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE clientes SET nombre=%s, correo=%s, telefono=%s, direccion=%s WHERE id_cliente=%s",
        (nombre, correo, telefono, direccion, id_cliente),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("inicio"))


@app.route("/eliminar/<int:id_cliente>", methods=["POST"])
def eliminar_cliente(id_cliente):
    """
    Sub-bloque: Eliminación en Cascada manual
    Para no violar las restricciones de integridad de la BD:
    1. Busca los pedidos del cliente.
    2. Elimina las facturas asociadas a esos pedidos.
    3. Elimina los pedidos propios del cliente.
    4. Elimina finalmente al cliente de la tabla.
    """
    conn = get_conexion()
    cursor = conn.cursor()

    # 1. Obtener los IDs de los pedidos del cliente
    cursor.execute("SELECT id_pedido FROM pedidos WHERE id_cliente = %s", (id_cliente,))
    pedidos = cursor.fetchall()
    ids_pedidos = [p[0] for p in pedidos]

    # 2. Borrar las facturas vinculadas a esos pedidos
    if ids_pedidos:
        formato = ",".join(["%s"] * len(ids_pedidos))
        cursor.execute(
            f"DELETE FROM facturas WHERE id_pedido IN ({formato})", ids_pedidos
        )

    # 3. Borrar los pedidos del cliente
    cursor.execute("DELETE FROM pedidos WHERE id_cliente = %s", (id_cliente,))

    # 4. Borrar el registro del cliente
    cursor.execute("DELETE FROM clientes WHERE id_cliente = %s", (id_cliente,))

    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("inicio"))


#           BLOQUE: COMERCIALES


@app.route("/comerciales")
def comerciales():
    """
    Sub-bloque: Listar Comerciales
    Lista todos los comerciales del equipo junto con el conteo acumulado
    de los pedidos que han conseguido realizar a través de sus clientes.
    """
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT co.id_comercial, co.nombre, co.correo, co.telefono,
               COUNT(p.id_pedido) as total_pedidos
        FROM comerciales co
        LEFT JOIN clientes c ON co.id_comercial = c.id_comercial
        LEFT JOIN pedidos p ON c.id_cliente = p.id_cliente
        GROUP BY co.id_comercial
        ORDER BY total_pedidos DESC
    """)
    comerciales = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("comerciales.html", comerciales=comerciales)


#             BLOQUE: PEDIDOS


@app.route("/pedidos")
def pedidos():
    """
    Sub-bloque: Listar Pedidos (Clasificados)
    Realiza tres consultas paralelas para separar los pedidos según su estado
    ('Solicitado', 'Enviado', 'Recibido'). Esto permite estructurar la información
    en formato visual Kanban en el frontend.
    """
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)

    # Consulta 1: Pedidos Solicitados
    cursor.execute("""
        SELECT p.id_pedido, p.fregistro, p.estado_pedido, p.precio, p.descuentoporcliente, c.nombre as cliente
        FROM pedidos p
        JOIN clientes c ON p.id_cliente = c.id_cliente
        WHERE p.estado_pedido = 'Solicitado'
    """)
    solicitados = cursor.fetchall()

    # Consulta 2: Pedidos Enviados
    cursor.execute("""
        SELECT p.id_pedido, p.fregistro, p.estado_pedido, p.precio, p.descuentoporcliente, c.nombre as cliente
        FROM pedidos p
        JOIN clientes c ON p.id_cliente = c.id_cliente
        WHERE p.estado_pedido = 'Enviado'
    """)
    enviados = cursor.fetchall()

    # Consulta 3: Pedidos Recibidos
    cursor.execute("""
        SELECT p.id_pedido, p.fregistro, p.estado_pedido, p.precio, p.descuentoporcliente, c.nombre as cliente
        FROM pedidos p
        JOIN clientes c ON p.id_cliente = c.id_cliente
        WHERE p.estado_pedido = 'Recibido'
    """)
    recibidos = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template(
        "pedidos.html", solicitados=solicitados, enviados=enviados, recibidos=recibidos
    )


#             BLOQUE: FACTURAS


@app.route("/facturas")
def facturas():
    """
    Sub-bloque: Listar e historial de Facturas
    Trae los datos de las facturas cruzándolas con pedidos y clientes.
    También extrae la lista de pedidos completa para rellenar el
    desplegable dinámico del formulario de inserción.
    """
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)

    # 1. Obtener listado de todas las facturas detalladas
    cursor.execute("""
        SELECT f.id_factura, f.fragistro, f.estadofactura, f.importebruto, f.importe_neto, 
               f.id_pedido, c.nombre as cliente
        FROM facturas f
        JOIN pedidos p ON f.id_pedido = p.id_pedido
        JOIN clientes c ON p.id_cliente = c.id_cliente
        ORDER BY f.id_factura DESC
    """)
    lista_facturas = cursor.fetchall()

    # 2. Obtener los pedidos para asociarlos en el menú desplegable del HTML
    cursor.execute("""
        SELECT p.id_pedido, c.nombre as cliente, p.precio 
        FROM pedidos p
        JOIN clientes c ON p.id_cliente = c.id_cliente
        ORDER BY p.id_pedido DESC
    """)
    lista_pedidos = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template(
        "facturas.html", facturas=lista_facturas, pedidos=lista_pedidos
    )


@app.route("/facturas/añadir", methods=["POST"])
def añadir_factura():
    """
    Sub-bloque: Crear Factura
    Inserta una factura vinculándola al ID de un pedido específico. Los campos
    'fragistro' y 'userinsert' no se envían porque MySQL los autocompleta con
    curdate() y user() respectivamente por defecto según el diseño de tu tabla.
    """
    id_pedido = request.form["id_pedido"]
    estadofactura = request.form["estadofactura"]
    importebruto = request.form["importebruto"]
    importe_neto = request.form["importe_neto"]

    conn = get_conexion()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO facturas (id_pedido, estadofactura, importebruto, importe_neto) 
        VALUES (%s, %s, %s, %s)
    """,
        (id_pedido, estadofactura, importebruto, importe_neto),
    )

    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("facturas"))


@app.route("/facturas/eliminar/<int:id_factura>", methods=["POST"])
def eliminar_factura(id_factura):
    """
    Sub-bloque: Eliminar Factura
    Busca una factura concreta a través de su Clave Primaria (id_factura)
    y la remueve del sistema de forma segura.
    """
    conn = get_conexion()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM facturas WHERE id_factura = %s", (id_factura,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("facturas"))


#           CONTROL DE ARRANQUE

if __name__ == "__main__":
    # Arranca el servidor local de Flask con el modo de depuración activo.
    # Permite ver los errores de sintaxis o de base de datos directamente en el navegador.
    app.run(debug=True)
