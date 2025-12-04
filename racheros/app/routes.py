from flask import render_template, flash, redirect, url_for, request, session, make_response
from app import app
from app.forms import LoginForm, RegistrationForm, HabitForm, RequestResetForm, ResetPasswordForm
from datetime import date, timedelta
from functools import wraps
from itsdangerous import URLSafeTimedSerializer 

# ==== IMPORTS DEL BACKEND ====
from app.backend.db_connection import get_connection
from app.backend.ms_usuarios import login_usuario, crear_usuario, verificar_correo_existe, actualizar_contrasena
from app.backend.ms_habitos import (
    crear_habito as crear_habito_micro,
    actualizar_habito as actualizar_habito_micro,
    eliminar_habito as eliminar_habito_micro,
    listar_habitos_por_usuario
)
from app.backend.ms_progreso import registrar_progreso
from app.backend.ms_reportes import generar_reporte_semanal

# --- NUEVO IMPORT PARA ADMIN ---
# (Asegúrate de haber creado este archivo en app/backend/ms_admin.py)
from app.backend.ms_admin import verificar_es_admin, obtener_dashboard_admin, eliminar_usuario_desde_admin
# ===============================

# --- CONFIGURACIÓN DE SEGURIDAD Y SESIÓN ---

@app.before_request
def session_management():
    session.permanent = True
    if session.get("remember_me"):
        app.permanent_session_lifetime = timedelta(days=30)
    else:
        app.permanent_session_lifetime = timedelta(minutes=5)

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# --- RECUPERACIÓN DE CONTRASEÑA ---

def get_reset_token(email, expires_sec=1800):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return s.dumps(email, salt='email-reset-salt')

def verify_reset_token(token):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='email-reset-salt', max_age=1800)
    except:
        return None
    return email

def send_reset_email(user_email, token):
    link = url_for('reset_token', token=token, _external=True)
    print("\n" + "="*50)
    print(f" [SIMULACIÓN EMAIL] Para: {user_email}")
    print(f" Link: {link}")
    print("="*50 + "\n")

# ========= LOGIN REQUIRED ==========
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "id_usuario" not in session:
            flash("Inicia sesión para acceder.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ========= RUTAS DE RECUPERACIÓN ============

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if "id_usuario" in session:
        return redirect(url_for('index'))
    
    form = RequestResetForm()
    if request.method == 'GET' and not form.email.data:
        email_from_login = request.args.get('email')
        if email_from_login:
            form.email.data = email_from_login
    
    if form.validate_on_submit():
        user = verificar_correo_existe(form.email.data)
        if user:
            token = get_reset_token(form.email.data)
            send_reset_email(form.email.data, token)
            flash('Enlace enviado a tu consola/correo.', 'info')
            return redirect(url_for('login'))
        else:
            flash('No existe cuenta con ese correo.', 'warning')
            
    return render_template('reset_request.html', title='Restablecer Contraseña', form=form)

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if "id_usuario" in session:
        return redirect(url_for('index'))
    
    email = verify_reset_token(token)
    if not email:
        flash('Enlace inválido o expirado.', 'warning')
        return redirect(url_for('reset_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        actualizar_contrasena(email, form.password.data)
        flash('Contraseña actualizada. Inicia sesión.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_token.html', title='Nueva Contraseña', form=form)


# ========= LOGIN (MODIFICADO PARA ADMIN) ============
@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():

        # 1. Login Normal (Backend Usuarios)
        resp = login_usuario(
            correo=form.username.data,
            contrasena=form.password.data
        )

        if not resp["ok"]:
            flash("Usuario o contraseña incorrectos.", "danger")
            return render_template("login.html", form=form)

        # 2. Guardar datos básicos en sesión
        session["logged_in"] = True
        session["id_usuario"] = resp["user"]["id_usuario"]
        session["remember_me"] = form.remember_me.data
        nombre_db = resp["user"]["nombre"]
        session["username"] = nombre_db.title() if nombre_db else "Usuario"

        # 3. --- VERIFICACIÓN DE ADMIN (NUEVO) ---
        datos_admin = verificar_es_admin(session["id_usuario"])
        
        if datos_admin["es_admin"]:
            session["es_admin"] = True
            session["nivel_admin"] = datos_admin["nivel"]
            flash(f"⚡ Modo Admin Activado: {datos_admin['nivel'].upper()}", "info")
        else:
            session["es_admin"] = False
            flash(f"Bienvenido de nuevo, {session['username']}!", "success")
        # ----------------------------------------

        return redirect(url_for("index"))

    return render_template("login.html", form=form)


# ========= LOGOUT ============
@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))


# ========= DASHBOARD (INDEX) ============
@app.route('/')
@app.route('/dashboard')
@login_required
def index():
    # Si es admin y quiere ir a su panel, podría haber un botón en el dashboard normal
    # Aquí cargamos el dashboard normal de hábitos
    id_usuario = session["id_usuario"]
    conn = get_connection()
    today_str = date.today().isoformat()

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT h.*, c.nombre_categoria
            FROM habitos h
            LEFT JOIN categorias c ON h.id_categoria = c.id_categoria
            WHERE h.id_usuario = %s AND h.frecuencia = 'diario'
        """, (id_usuario,))
        habitos = cursor.fetchall()

    completados_hoy_count = 0
    for h in habitos:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT completado FROM registro_progreso
                WHERE id_habito = %s AND fecha = %s
            """, (h["id_habito"], today_str))
            row = cursor.fetchone()
        h["completado_hoy"] = row["completado"] if row else False
        if h["completado_hoy"]: completados_hoy_count += 1

    total_hoy = len(habitos)
    porcentaje = int((completados_hoy_count / total_hoy) * 100) if total_hoy > 0 else 0
    
    # Datos para el gráfico (últimos 7 días)
    datos_grafico = []
    today = date.today()
    for i in range(6, -1, -1):
        fecha_str = (today - timedelta(days=i)).isoformat()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as total FROM registro_progreso r
                INNER JOIN habitos h ON r.id_habito = h.id_habito
                WHERE h.id_usuario = %s AND r.fecha = %s AND r.completado = 1
            """, (id_usuario, fecha_str))
            datos_grafico.append(cursor.fetchone()['total'])

    estadisticas = {"racha_actual": (1 if completados_hoy_count > 0 else 0), "porcentaje_semanal": porcentaje}

    return render_template(
        "dashboard.html",
        user={"username": session["username"], "es_admin": session.get("es_admin", False)},
        habitos_de_hoy=habitos,
        estadisticas=estadisticas,
        datos_grafico=datos_grafico 
    )

# ========= NUEVAS RUTAS DE ADMIN ============

@app.route('/admin')
@login_required
def admin_dashboard():
    # Protección: Solo admins pueden ver esto
    if not session.get("es_admin"):
        flash("Acceso denegado. Zona restringida.", "danger")
        return redirect(url_for("index"))

    # Llamada al microservicio de admin
    resp = obtener_dashboard_admin()
    if not resp["ok"]:
        flash(f"Error cargando datos: {resp.get('error')}", "danger")
        return redirect(url_for("index"))

    return render_template(
        "admin_dashboard.html", 
        kpis=resp["kpis"], 
        usuarios=resp["usuarios"]
    )

@app.route('/admin/eliminar/<int:id_user>', methods=['POST'])
@login_required
def admin_eliminar_usuario(id_user):
    # Protección
    if not session.get("es_admin"):
        return redirect(url_for("index"))
    
    # Llamada al microservicio para eliminar
    resp = eliminar_usuario_desde_admin(
        id_admin=session["id_usuario"], 
        id_usuario_a_eliminar=id_user, 
        motivo="Eliminado desde el panel web"
    )
    
    if resp["ok"]:
        flash("Usuario eliminado correctamente.", "success")
    else:
        flash(f"Error al eliminar: {resp['error']}", "danger")
        
    return redirect(url_for("admin_dashboard"))

# ============================================

# ========= REGISTRO DE USUARIO ============
@app.route('/register', methods=['GET','POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        resp = crear_usuario(
            nombre=form.nombre.data.strip().title(),
            correo=form.correo.data,
            contrasena=form.password.data,
            genero=form.genero.data,
            edad=form.edad.data
        )
        if resp["ok"]:
            flash("Registrado correctamente. Por favor inicia sesión.", "success")
            return redirect(url_for("login"))
        else:
            flash(f"Error: {resp.get('error', 'Error desconocido')}", "danger")
            
    return render_template("register.html", form=form)

# ========= LISTAR HÁBITOS ============
@app.route('/habits')
@login_required
def habits():
    resp = listar_habitos_por_usuario(session["id_usuario"])
    categorias = {1: "Salud", 2: "Crecimiento Personal", 3: "Bienestar Mental"}
    form = HabitForm()
    form.categoria.choices = list(categorias.items())

    return render_template("habits.html", habitos=resp["habitos"], form=form)

# ========= CREAR HÁBITO ============
@app.route('/habits/crear', methods=['POST'])
@login_required
def crear_habito():
    form = HabitForm()
    form.categoria.choices = [(1, "Salud"), (2, "Crecimiento Personal"), (3, "Bienestar Mental")]

    if form.validate_on_submit():
        crear_habito_micro(
            id_usuario=session["id_usuario"],
            id_categoria=form.categoria.data,
            nombre_habito=form.nombre_habito.data,
            descripcion=form.descripcion.data,
            frecuencia=form.frecuencia.data,
            hora_objetivo=None
        )
        flash("Hábito creado.", "success")
    else:
        flash("Error creando hábito.", "danger")

    return redirect(url_for('habits'))

# ========= ELIMINAR HÁBITO ============
@app.route('/habits/eliminar/<int:habito_id>', methods=['POST'])
@login_required
def eliminar_habito(habito_id):
    eliminar_habito_micro(habito_id)
    flash("Hábito eliminado", "warning")
    return redirect(url_for('habits'))

# ========= TOGGLE PROGRESO ============
@app.route('/habito/toggle/<int:habito_id>', methods=['POST'])
@login_required
def toggle_habito(habito_id):
    today_str = date.today().isoformat()
    registrar_progreso(id_habito=habito_id, fecha=today_str, completado=True)
    return redirect(url_for("index"))

# ========= REGISTRO DE PROGRESO (PÁGINA) ============
@app.route('/registro_progreso')
@login_required
def registro_progreso_page(): # Cambié nombre para evitar colisión con import
    id_usuario = session["id_usuario"]
    today = date.today()
    today_str = today.isoformat()
    conn = get_connection()

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM habitos WHERE id_usuario = %s AND frecuencia = 'diario'", (id_usuario,))
        habitos = cursor.fetchall()

    habitos_diarios = []
    for h in habitos:
        with conn.cursor() as cursor:
            cursor.execute("SELECT completado FROM registro_progreso WHERE id_habito = %s AND fecha = %s", (h["id_habito"], today_str))
            row = cursor.fetchone()
        h["completado_hoy"] = row["completado"] if row else False
        habitos_diarios.append(h)

    total = len(habitos_diarios)
    completados = sum(1 for h in habitos_diarios if h["completado_hoy"])
    porcentaje = int((completados / total) * 100) if total > 0 else 0
    
    msgs = ["¡Cada paso cuenta!", "¡Vas por buen camino!", "¡Casi lo logras!", "¡Excelente trabajo!"]
    idx = 0 if porcentaje < 25 else 1 if porcentaje < 50 else 2 if porcentaje < 75 else 3

    return render_template(
        "registro_progreso.html",
        habitos_diarios=habitos_diarios,
        total_hoy=total,
        completados_hoy=completados,
        porcentaje_completado=porcentaje,
        today_date=today.strftime("%A, %d de %B de %Y"),
        motivational_message=msgs[idx]
    )

# ========= REPORTES ============
@app.route('/reportes')
@login_required
def reportes():
    resultado = generar_reporte_semanal(session["id_usuario"])
    if not resultado["hay_reporte"]:
        return render_template("reportes.html", reportes=None)

    lista_reportes = [{
        "semana": resultado["semana"],
        "completados": resultado["completados"],
        "total_habitos": resultado["total"], 
        "porcentaje_cumplimiento": resultado["porcentaje"],
        "mejor_racha": resultado["racha"],
        "archivo_pdf": resultado["archivo_pdf"],
        "archivo_excel": resultado["archivo_excel"]
    }]
    return render_template("reportes.html", reportes=lista_reportes)