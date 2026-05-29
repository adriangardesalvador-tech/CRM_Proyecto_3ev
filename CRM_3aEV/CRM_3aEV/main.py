from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

def get_conexion():
    return mysql.connector.connect(
        host="localhost",
        port=3307,
        user="root",
        password="",
        database="CRM_PRUEBA"
    )

@app.route("/")
def inicio():
    conn = get_conexion()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clientes ORDER BY ventas DESC LIMIT 10")
    clientes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("index.html", clientes=clientes)


@app.route("/añadir", methods=["POST"])
def añadir_cliente():
    nombre = request.form["nombre"]
    email = request.form["email"]
    telefono = request.form["telefono"]
    estado = request.form["estado"]
    conn = get_conexion()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clientes (nombre, email, telefono, estado) VALUES (%s, %s, %s, %s)",
        (nombre, email, telefono, estado)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("inicio"))

@app.route("/comerciales")
def comerciales():
    return render_template("comerciales.html")

@app.route("/pedidos")
def pedidos():
    return render_template("pedidos.html")

@app.route("/facturas")
def facturas():
    return render_template("facturas.html")

if __name__ == "__main__":
    app.run(debug=True)