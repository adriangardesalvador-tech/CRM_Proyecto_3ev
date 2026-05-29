from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)


# conexion a la base de datos, se llama cada vez que se necesita hacer una consulta
def get_conexion():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="",
        database="crm_preyecto3ev",
    )


# pagina principal, muestra los 10 primeros clientes con el nombre de su comercial
@app.route("/")
def inicio():
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)
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
    cursor.close()
    conn.close()
    return render_template("index.html", clientes=clientes)


# pagina de clientes, muestra todos los clientes con el nombre de su comercial
@app.route("/clientes")
def clientes():
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


# recibe los datos del formulario y los inserta en la tabla clientes
@app.route("/añadir", methods=["POST"])
def añadir_cliente():
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


# pagina de comerciales, muestra todos los comerciales de la tabla
@app.route("/comerciales")
def comerciales():
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)
    # traer cada comercial con el numero de pedidos de sus clientes
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


# elimina el cliente cuyo id viene en la URL y vuelve al inicio
@app.route("/eliminar/<int:id_cliente>", methods=["POST"])
def eliminar_cliente(id_cliente):
    conn = get_conexion()
    cursor = conn.cursor()

    # 1. obtener los ids de los pedidos del cliente
    cursor.execute("SELECT id_pedido FROM pedidos WHERE id_cliente = %s", (id_cliente,))
    pedidos = cursor.fetchall()
    ids_pedidos = [p[0] for p in pedidos]

    # 2. borrar las facturas de esos pedidos
    if ids_pedidos:
        formato = ",".join(["%s"] * len(ids_pedidos))
        cursor.execute(
            f"DELETE FROM facturas WHERE id_pedido IN ({formato})", ids_pedidos
        )

    # 3. borrar los pedidos del cliente
    cursor.execute("DELETE FROM pedidos WHERE id_cliente = %s", (id_cliente,))

    # 4. borrar el cliente
    cursor.execute("DELETE FROM clientes WHERE id_cliente = %s", (id_cliente,))

    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("inicio"))


# muestra el formulario de editar con los datos del cliente ya rellenos
@app.route("/editar/<int:id_cliente>")
def editar_form(id_cliente):
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clientes WHERE id_cliente = %s", (id_cliente,))
    cliente = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("editar.html", cliente=cliente)


# recibe los datos del formulario de editar y actualiza el cliente en la base de datos
@app.route("/editar/<int:id_cliente>", methods=["POST"])
def editar_cliente(id_cliente):
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


# pagina de pedidos, hace tres consultas separadas para separar los pedidos por estado
# solicitados, enviados y recibidos se mandan por separado al HTML para el kanban
@app.route("/pedidos")
def pedidos():
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.id_pedido, p.fregistro, p.estado_pedido, p.precio, p.descuentoporcliente, c.nombre as cliente
        FROM pedidos p
        JOIN clientes c ON p.id_cliente = c.id_cliente
        WHERE p.estado_pedido = 'Solicitado'
    """)
    solicitados = cursor.fetchall()
    cursor.execute("""
        SELECT p.id_pedido, p.fregistro, p.estado_pedido, p.precio, p.descuentoporcliente, c.nombre as cliente
        FROM pedidos p
        JOIN clientes c ON p.id_cliente = c.id_cliente
        WHERE p.estado_pedido = 'Enviado'
    """)
    enviados = cursor.fetchall()
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


# pagina de facturas, muestra todas las facturas unidas con su pedido
@app.route("/facturas")
def facturas():
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT f.id_factura, f.fragistro, f.estadofactura, f.importebruto, f.importe_neto, p.id_pedido
        FROM facturas f
        JOIN pedidos p ON f.id_pedido = p.id_pedido
    """)
    facturas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("facturas.html", facturas=facturas)


# arranca el servidor en modo debug para ver los errores en pantalla
if __name__ == "__main__":
    app.run(debug=True)
