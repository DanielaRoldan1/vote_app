import json
import os
from datetime import datetime, timedelta
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data")
USUARIOS_FILE = os.path.join(DATA_PATH, "usuarios.json")
RESULTADOS_FILE = os.path.join(DATA_PATH, "resultados.json")

# Cargar usuarios desde archivo JSON
def cargar_usuarios():
    if os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Guardar usuarios en archivo JSON
def guardar_usuarios(usuarios):
    with open(USUARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)

# Registrar un nuevo usuario
def registrar_usuario(id_usuario, nombre, password, direccion, telefono, tipo_usuario):
    usuarios = cargar_usuarios()
    if id_usuario in usuarios:
        return False, "El ID de usuario ya existe."

    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."

    usuarios[id_usuario] = {
        "nombre": nombre,
        "password": password,
        "direccion": direccion,
        "telefono": telefono,
        "tipo": tipo_usuario
    }
    guardar_usuarios(usuarios)
    return True, "Usuario registrado exitosamente."

# Iniciar sesión
def iniciar_sesion(id_usuario, password):
    usuarios = cargar_usuarios()
    user = usuarios.get(id_usuario)
    if user and user.get("password") == password:
        return True, user
    return False, None

# Cargar resultados
def cargar_resultados():
    if os.path.exists(RESULTADOS_FILE):
        with open(RESULTADOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Guardar resultados
def guardar_resultados(resultados):
    with open(RESULTADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

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
        total = sum(conteo.values()) or 1  # evitar división por cero
        r["detalle"] = conteo
        r["total"] = total
        r["porcentajes"] = {k: (v / total * 100) for k, v in conteo.items()}
        resultados.append(r)

    return render_template("admin.html", resultados=resultados)

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

PREGUNTAS_FILE = os.path.join(DATA_PATH, "preguntas.json")
VOTOS_FILE = os.path.join(DATA_PATH, "votos.json")

def cargar_preguntas():
    if os.path.exists(PREGUNTAS_FILE):
        with open(PREGUNTAS_FILE, "r", encoding="utf-8") as f:
            preguntas = json.load(f)
            for p in preguntas.values():
                if isinstance(p.get("fecha_caducidad"), str):
                    try:
                        p["fecha_caducidad"] = datetime.strptime(p["fecha_caducidad"], "%Y-%m-%d %H:%M:%S")
                    except:
                        p["fecha_caducidad"] = None
            return preguntas
    return {}

def guardar_preguntas(preguntas):
    serializable = {
        k: {**v, "fecha_caducidad": v["fecha_caducidad"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(v.get("fecha_caducidad"), datetime) else None}
        for k, v in preguntas.items()
    }
    with open(PREGUNTAS_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=4, ensure_ascii=False)

def registrar_pregunta(texto, tiempo_segundos):
    preguntas = cargar_preguntas()
    id_pregunta = str(uuid.uuid4())
    fecha_caducidad = datetime.now() + timedelta(seconds=tiempo_segundos)
    preguntas[id_pregunta] = {
        "texto": texto,
        "fecha_caducidad": fecha_caducidad,
        "estado": "activa"
    }
    guardar_preguntas(preguntas)

    resultados = cargar_resultados()
    resultados[id_pregunta] = {
        "Apruebo": 0,
        "No apruebo": 0,
        "Me abstengo": 0,
        "Voto en blanco": 0
    }
    guardar_resultados(resultados)

    return True, "Pregunta registrada exitosamente."

def cargar_preguntas_activas():
    ahora = datetime.now()
    preguntas = cargar_preguntas()
    activas = {
        k: v for k, v in preguntas.items()
        if v.get("estado") == "activa" and isinstance(v.get("fecha_caducidad"), datetime) and v["fecha_caducidad"] > ahora
    }
    return activas
def cargar_pregunta_por_id(pregunta_id):
    preguntas = cargar_preguntas()
    return preguntas.get(pregunta_id)
def registrar_voto(id_pregunta, id_usuario, opcion):
    votos = {}
    if os.path.exists(VOTOS_FILE):
        with open(VOTOS_FILE, "r", encoding="utf-8") as f:
            votos = json.load(f)

    if id_pregunta not in votos:
        votos[id_pregunta] = {}

    if id_usuario in votos[id_pregunta]:
        return False, "Ya has votado para esta pregunta."

    preguntas = cargar_preguntas()
    pregunta = preguntas.get(id_pregunta)
    if not pregunta or pregunta.get("estado") != "activa":
        return False, "La pregunta no está activa."

    if datetime.now() >= pregunta["fecha_caducidad"]:
        preguntas[id_pregunta]["estado"] = "cerrada"
        guardar_preguntas(preguntas)
        return False, "La votación ha cerrado por tiempo."

    votos[id_pregunta][id_usuario] = opcion
    with open(VOTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(votos, f, indent=4, ensure_ascii=False)

    resultados = cargar_resultados()
    if id_pregunta not in resultados:
        resultados[id_pregunta] = {
            "Apruebo": 0,
            "No apruebo": 0,
            "Me abstengo": 0,
            "Voto en blanco": 0
        }

    resultados[id_pregunta][opcion] += 1
    guardar_resultados(resultados)

    return True, "Voto registrado exitosamente."
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
 
    preguntas = cargar_preguntas_activas()
    ahora = datetime.now()
    for p in preguntas.values():
        if isinstance(p.get("fecha_caducidad"), datetime):
            restante = int((p["fecha_caducidad"] - ahora).total_seconds())
            p["restante"] = max(restante, 0)
        else:
            p["restante"] = "desconocido"

    return render_template("votar.html", preguntas=preguntas)
@app.route("/extender_tiempo/<pregunta_id>", methods=["POST"])
def extender_tiempo(pregunta_id):
    if "usuario" not in session or session.get("tipo") != "Administrador":
        flash("Acceso restringido", "danger")
        return redirect(url_for("login"))

    nuevo_tiempo = int(request.form["nuevo_tiempo"])
    preguntas = cargar_preguntas()
    pregunta = preguntas.get(pregunta_id)
    if not pregunta:
        flash("Pregunta no encontrada", "danger")
        return redirect(url_for("admin"))

    if pregunta.get("estado") != "activa":
        flash("Solo se puede extender el tiempo de preguntas activas", "danger")
        return redirect(url_for("admin"))

    pregunta["fecha_caducidad"] = datetime.now() + timedelta(seconds=nuevo_tiempo)
    guardar_preguntas(preguntas)
    flash("Tiempo extendido correctamente", "success")
    return redirect(url_for("admin"))