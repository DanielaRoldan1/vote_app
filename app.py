
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from flask import render_template
from flask import session, redirect, url_for, flash
from logica import (
    iniciar_sesion, registrar_usuario, cargar_preguntas_activas,
    registrar_voto, registrar_pregunta, cargar_resultados, cargar_preguntas,
    cargar_pregunta_por_id, guardar_preguntas
)

app = Flask(__name__)
app.secret_key = 'clave_secreta_cambiar'

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        id_usuario = request.form["id_usuario"]
        password = request.form["password"]
        exito, usuario = iniciar_sesion(id_usuario, password)
        if exito:
            session["usuario"] = id_usuario
            session["nombre"] = usuario["nombre"]
            session["tipo"] = usuario["tipo"]
            flash(f"Bienvenido {usuario['nombre']}", "success")
            return redirect(url_for("votar" if usuario["tipo"] != "Administrador" else "admin"))
        else:
            flash("Credenciales inválidas", "danger")
    return render_template("login.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        id_usuario = request.form["id_usuario"]
        nombre = request.form["nombre"]
        password = request.form["password"]
        direccion = request.form["direccion"]
        telefono = request.form["telefono"]
        tipo_usuario = request.form["tipo_usuario"]

        exito, mensaje = registrar_usuario(
            id_usuario, nombre, password, direccion, telefono, tipo_usuario
        )
        if exito:
            flash(mensaje, "success")
            return redirect(url_for("login"))
        else:
            flash(mensaje, "danger")
    return render_template("registro.html")

@app.route("/votar", methods=["GET", "POST"])
def votar():
    if "usuario" not in session:
        flash("Debe iniciar sesión para votar", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        id_pregunta = request.form["id_pregunta"]
        opcion = request.form["opcion"]
        exito, mensaje = registrar_voto(id_pregunta, session["usuario"], opcion)
        flash(mensaje, "success" if exito else "danger")
        return redirect(url_for("votar"))

    preguntas = cargar_preguntas_activas()
    ahora = datetime.now()
    for p in preguntas.values():
        if isinstance(p.get("fecha_caducidad"), datetime):
            restante = int((p["fecha_caducidad"] - ahora).total_seconds())
            p["restante"] = max(restante, 0)
        else:
            p["restante"] = "desconocido"

    return render_template("votar.html", preguntas=preguntas)
@app.route('/extender_tiempo/<pregunta_id>', methods=['POST'])
def extender_tiempo(pregunta_id):
    nuevo_tiempo = int(request.form['nuevo_tiempo'])
    # Aquí debes cargar la pregunta y actualizar su tiempo si es válido
    pregunta = cargar_pregunta_por_id(pregunta_id)  # Implementa esta función según tu lógica
    if pregunta and pregunta['estado'] == 'Activa':
        if pregunta['tiempo_actual'] < nuevo_tiempo <= 300:
            pregunta['tiempo_actual'] = nuevo_tiempo
            guardar_preguntas(pregunta)  # Implementa esta función según tu lógica
            flash("Tiempo extendido correctamente.", "success")
        else:
            flash("El nuevo tiempo debe ser mayor al actual y menor o igual a 300.", "danger")
    else:
        flash("Pregunta no encontrada o no activa.", "danger")
    return redirect(url_for('admin'))
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "usuario" not in session or session.get("tipo") != "Administrador":
        flash("Acceso restringido", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        texto = request.form["texto"]
        try:
            tiempo = int(request.form["tiempo"])
            if tiempo < 60 or tiempo > 300:
                raise ValueError()
        except:
            flash("El tiempo debe estar entre 60 y 300 segundos", "danger")
            return redirect(url_for("admin"))

        exito, mensaje = registrar_pregunta(texto, tiempo)
        flash(mensaje, "success" if exito else "danger")
        return redirect(url_for("admin"))

    resultados = []
    preguntas = cargar_preguntas()
    votos = cargar_resultados()

    for pid, data in preguntas.items():
        r = {
            "texto": data.get("texto", ""),
            "estado": data.get("estado", ""),
            "fecha": data.get("fecha_caducidad").strftime("%Y-%m-%d %H:%M:%S") if isinstance(data.get("fecha_caducidad"), datetime) else "N/A",
            "detalle": {},
            "porcentajes": {},
            "total": 0
        }
        conteo = votos.get(pid, {})
        total = sum(conteo.values()) or 1
        r["detalle"] = conteo
        r["total"] = total
        r["porcentajes"] = {k: (v / total * 100) for k, v in conteo.items()}
        resultados.append(r)

    return render_template("admin.html", resultados=resultados)

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
