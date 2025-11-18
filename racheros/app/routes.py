from flask import (
    render_template,
    flash,
    redirect,
    url_for,
    request,
    session,
    send_file,
)
from app import app
from app.forms import LoginForm, RegistrationForm, HabitForm
from datetime import date
from functools import wraps
import os

from app.backend.db_connection import get_connection
from app.backend.ms_usuarios import login_usuario, crear_usuario
from app.backend.ms_habitos import (
    crear_habito as crear_habito_micro,
    actualizar_habito as actualizar_habito_micro,
    eliminar_habito as eliminar_habito_micro,
    listar_habitos_por_usuario,
)
from app.backend.ms_progreso import registrar_progreso
from app.backend.ms_reportes import generar_reporte_semanal


# ========= LOGIN REQUIRED ==========
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "id_usuario" not in session:
            flash("Inicia sesión para acceder.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


# ========= LOGIN ==========
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        resp = login_usuario(
            correo=form.username.data,
            contrasena=form.password.data,
        )

        if not resp["ok"]:
            flash("Usuario o contraseña incorrectos.", "danger")
            return render_template("login.html", form=form)

        session["logged_in"] = True
        session["username"] = resp["user"]["correo"]
        session["id_usuario"] = resp["user"]["id_usuario"]

        flash("¡Bienvenido!", "success")
        return redirect(url_for("index"))

    return render_template("login.html", form=form)


# ========= LOGOUT ==========
@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))


# ========= DASHBOARD ==========
@app.route("/")
@app.route("/dashboard")
@login_required
def index():
    id_usuario = session["id_usuario"]
    conn = get_connection()

    today = date.today()
    today_str = today.isoformat()

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT h.*, c.nombre_categoria
            FROM habitos h
            LEFT JOIN categorias c ON h.id_categoria = c.id_categoria
            WHERE h.id_usuario = %s AND h.frecuencia = 'diario'
            """,
            (id_usuario,),
        )
        habitos = cursor.fetchall()

    for h in habitos:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT completado
                FROM registro_progreso
                WHERE id_habito = %s AND fecha = %s
                """,
                (h["id_habito"], today_str),
            )
            row = cursor.fetchone()
        h["completado_hoy"] = row["completado"] if row else False

    completados_hoy = sum(1 for h in habitos if h["completado_hoy"])
    total_hoy = len(habitos)
    porcentaje = int((completados_hoy / total_hoy) * 100) if total_hoy else 0

    estadisticas = {
        "racha_actual": 1,
        "porcentaje_semanal": porcentaje,
    }

    return render_template(
        "dashboard.html",
        user={"username": session["username"]},
        habitos_de_hoy=habitos,
        estadisticas=estadisticas,
    )


# ========= REGISTRO DE USUARIO ==========
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        resp = crear_usuario(
            nombre=form.nombre.data,
            correo=form.correo.data,
            contrasena=form.password.data,
            genero=form.genero.data,
            edad=form.edad.data,
        )
        if resp["ok"]:
            flash("Registrado correctamente.", "success")
            return redirect(url_for("login"))
        else:
            flash("Error creando usuario.", "danger")
    return render_template("register.html", form=form)


# ========= LISTAR HÁBITOS ==========
@app.route("/habits")
@login_required
def habits():
    id_usuario = session["id_usuario"]

    resp = listar_habitos_por_usuario(id_usuario)

    categorias = {
        1: "Salud",
        2: "Crecimiento Personal",
        3: "Bienestar Mental",
    }

    form = HabitForm()
    form.categoria.choices = list(categorias.items())

    return render_template(
        "habits.html",
        habitos=resp["habitos"],
        form=form,
        racha_actual=10,
        mejor_racha=40,
    )


# ========= CREAR HÁBITO ==========
@app.route("/habits/crear", methods=["POST"])
@login_required
def crear_habito():
    id_usuario = session["id_usuario"]
    form = HabitForm()

    categorias = {
        1: "Salud",
        2: "Crecimiento Personal",
        3: "Bienestar Mental",
    }
    form.categoria.choices = list(categorias.items())

    if form.validate_on_submit():
        crear_habito_micro(
            id_usuario=id_usuario,
            id_categoria=form.categoria.data,
            nombre_habito=form.nombre_habito.data,
            descripcion=form.descripcion.data,
            frecuencia=form.frecuencia.data,
        )
        flash("Hábito creado.", "success")
    else:
        flash("Error al crear hábito.", "danger")

    return redirect(url_for("habits"))


# ========= EDITAR HÁBITO ==========
@app.route("/habits/editar/<int:habito_id>", methods=["POST"])
@login_required
def editar_habito(habito_id):
    form = HabitForm()
    if form.validate_on_submit():
        actualizar_habito_micro(
            id_habito=habito_id,
            nombre_habito=form.nombre_habito.data,
            descripcion=form.descripcion.data,
            frecuencia=form.frecuencia.data,
        )
        flash("Hábito actualizado.", "info")
    else:
        flash("Error actualizando.", "danger")

    return redirect(url_for("habits"))


# ========= ELIMINAR HÁBITO ==========
@app.route("/habits/eliminar/<int:habito_id>", methods=["POST"])
@login_required
def eliminar_habito(habito_id):
    eliminar_habito_micro(habito_id)
    flash("Hábito eliminado.", "warning")
    return redirect(url_for("habits"))


# ========= TOGGLE PROGRESO ==========
@app.route("/habito/toggle/<int:habito_id>", methods=["POST"])
@login_required
def toggle_habito(habito_id):
    today_str = date.today().isoformat()

    registrar_progreso(
        id_habito=habito_id,
        fecha=today_str,
        completado=True,
    )

    return redirect(url_for("registro_progreso"))


# ========= REGISTRO DE PROGRESO ==========
@app.route("/registro_progreso")
@login_required
def registro_progreso():
    id_usuario = session["id_usuario"]
    today = date.today()
    today_str = today.isoformat()

    conn = get_connection()

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM habitos 
            WHERE id_usuario = %s AND frecuencia = 'diario'
            """,
            (id_usuario,),
        )
        habitos = cursor.fetchall()

    habitos_diarios = []
    for h in habitos:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT completado
                FROM registro_progreso
                WHERE id_habito = %s AND fecha = %s
                """,
                (h["id_habito"], today_str),
            )
            row = cursor.fetchone()

        h["completado_hoy"] = row["completado"] if row else False
        habitos_diarios.append(h)

    total_hoy = len(habitos_diarios)
    completados_hoy = sum(1 for h in habitos_diarios if h["completado_hoy"])
    porcentaje = int((completados_hoy / total_hoy) * 100) if total_hoy else 0

    mensaje = (
        "¡Cada paso cuenta!" if porcentaje < 25
        else "¡Vas por buen camino!" if porcentaje < 50
        else "¡Casi lo logras!" if porcentaje < 75
        else "¡Excelente trabajo!"
    )

    return render_template(
        "registro_progreso.html",
        habitos_diarios=habitos_diarios,
        total_hoy=total_hoy,
        completados_hoy=completados_hoy,
        porcentaje_completado=porcentaje,
        motivational_message=mensaje,
        today_date=today.strftime("%A, %d de %B de %Y"),
    )


# ========= REPORTES (GENERAR Y MOSTRAR PDFs LOCALES) ==========
@app.route("/reportes")
@login_required
def reportes():
    id_usuario = session["id_usuario"]

    # Llamamos al microservicio de reportes
    rep = generar_reporte_semanal(id_usuario)

    reportes = []

    # Caso típico: ms_reportes devuelve un dict
    if isinstance(rep, dict):
        if rep.get("hay_reporte"):
            nombre_pdf = rep.get("archivo")   # p.ej. reporte_1_2025-11-18.pdf
            ruta_local = rep.get("ruta")      # p.ej. app/static/reportes/...

            if ruta_local and os.path.exists(ruta_local) and nombre_pdf:
                ruta_descarga = url_for("descargar_reporte", nombre=nombre_pdf)
            else:
                ruta_descarga = None

            reportes.append(
                {
                    "semana": f"Semana del {date.today().strftime('%d/%m/%Y')}",
                    "total_habitos": rep.get("total_habitos", 0),
                    "completados": rep.get("completados", 0),
                    "mejor_racha": rep.get("mejor_racha", 0),
                    "porcentaje_cumplimiento": rep.get(
                        "porcentaje_cumplimiento", 0
                    ),
                    "ruta_pdf_s3": ruta_descarga,
                }
            )
        else:
            reportes = []  # no hay reporte

    # Por si en el futuro generas varios reportes y devuelves lista
    elif isinstance(rep, list):
        for r in rep:
            nombre_pdf = r.get("archivo")
            ruta_local = r.get("ruta")
            if ruta_local and os.path.exists(ruta_local) and nombre_pdf:
                ruta_descarga = url_for("descargar_reporte", nombre=nombre_pdf)
            else:
                ruta_descarga = None

            reportes.append(
                {
                    "semana": r.get("semana", ""),
                    "total_habitos": r.get("total_habitos", 0),
                    "completados": r.get("completados", 0),
                    "mejor_racha": r.get("mejor_racha", 0),
                    "porcentaje_cumplimiento": r.get(
                        "porcentaje_cumplimiento", 0
                    ),
                    "ruta_pdf_s3": ruta_descarga,
                }
            )

    return render_template("reportes.html", reportes=reportes)


# ========= DESCARGAR PDF ==========
@app.route("/descargar/<path:nombre>")
@login_required
def descargar_reporte(nombre):
    # Carpeta donde ms_reportes guarda los PDFs
    ruta = os.path.join("app", "static", "reportes", nombre)

    if not os.path.exists(ruta):
        flash("El archivo no existe.", "danger")
        return redirect(url_for("reportes"))

    return send_file(ruta, as_attachment=True)
