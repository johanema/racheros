import psutil 
from flask import render_template, flash, redirect, url_for, request, session, make_response, jsonify
from app import app
# IMPORTANTE: Añadimos los formularios de recuperación que faltaban
from app.forms import LoginForm, RegistrationForm, HabitForm, RequestResetForm, ResetPasswordForm
from datetime import date, timedelta
from functools import wraps
from itsdangerous import URLSafeTimedSerializer 

# ==== IMPORTS DEL BACKEND REAL ====
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

# --- NUEVO: IMPORTS PARA EL ADMINISTRADOR ---
from app.backend.ms_admin import verificar_es_admin, obtener_dashboard_admin, eliminar_usuario_desde_admin
# ===================================

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

# --- LÓGICA DE RECUPERACIÓN DE CONTRASEÑA ---

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
    print(f" [SIMULACIÓN DE CORREO] Para: {user_email}")
    print(f" Enlace: {link}")
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
            flash('Enlace enviado a tu consola.', 'info')
            return redirect(url_for('login'))
        else:
            flash('No existe una cuenta con ese correo.', 'warning')
            
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
        flash('Tu contraseña ha sido actualizada.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_token.html', title='Nueva Contraseña', form=form)


# ========= LOGIN ============
@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        resp = login_usuario(
            correo=form.username.data,
            contrasena=form.password.data
        )

        if not resp["ok"]:
            flash("Usuario o contraseña incorrectos.", "danger")
            return render_template("login.html", form=form)

        session["logged_in"] = True
        session["id_usuario"] = resp["user"]["id_usuario"]
        session["remember_me"] = form.remember_me.data
        
        nombre_db = resp["user"]["nombre"]
        session["username"] = nombre_db.title() if nombre_db else "Usuario"

        # --- Verificar Admin ---
        datos_admin = verificar_es_admin(session["id_usuario"])
        
        if datos_admin["es_admin"]:
            session["es_admin"] = True
            session["nivel_admin"] = datos_admin["nivel"]
            flash(f"⚡ Modo Maestro: {datos_admin['nivel'].upper()}", "info")
        else:
            session["es_admin"] = False
            flash(f"Bienvenido de nuevo, {session['username']}!", "success")

        return redirect(url_for("index"))

    return render_template("login.html", form=form)


# ========= LOGOUT ============
@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))


# ========= DASHBOARD (CEREBRO CENTRAL) ============
@app.route('/')
@app.route('/dashboard')
@login_required
def index():
    """
    Ruta inteligente:
    - Si es Admin -> Carga datos reales (gráficas, rankings) y muestra admin_dashboard.html
    - Si es Usuario -> Carga hábitos y muestra dashboard.html
    """
    
    # 1. ADMIN
    if session.get("es_admin"):
        resp = obtener_dashboard_admin()
        
        # Valores por defecto para seguridad
        kpis = {}
        usuarios = []
        logs = []
        rankings = {"top_rachas": [], "top_cumplimiento": [], "top_disciplinados": []}
        graficas = {"actividad": {"labels": [], "data": []}, "categorias": {"labels": [], "data": []}}

        if not resp["ok"]:
            flash(f"Error panel admin: {resp.get('error')}", "danger")
        else:
            kpis = resp.get("kpis", {})
            usuarios = resp.get("usuarios", [])
            logs = resp.get("logs", [])
            rankings = resp.get("rankings", rankings)
            graficas = resp.get("graficas", graficas) # <--- DATOS REALES PARA CHART.JS

        return render_template(
            "admin_dashboard.html", 
            user={"username": session["username"], "es_admin": True},
            kpis=kpis,
            usuarios=usuarios,
            logs=logs,
            rankings=rankings,
            graficas=graficas
        )

    # 2. USUARIO NORMAL
    else:
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
                cursor.execute("SELECT completado FROM registro_progreso WHERE id_habito = %s AND fecha = %s", (h["id_habito"], today_str))
                row = cursor.fetchone()
            h["completado_hoy"] = row["completado"] if row else False
            if h["completado_hoy"]: completados_hoy_count += 1

        total_hoy = len(habitos)
        porcentaje = int((completados_hoy_count / total_hoy) * 100) if total_hoy > 0 else 0

        # Datos gráfica usuario (placeholder simple o real según desees)
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
        
        conn.close() 

        estadisticas = {"racha_actual": (1 if completados_hoy_count > 0 else 0), "porcentaje_semanal": porcentaje}

        return render_template(
            "dashboard.html",
            user={"username": session["username"], "es_admin": False},
            habitos_de_hoy=habitos,
            estadisticas=estadisticas,
            datos_grafico=datos_grafico 
        )


# ========= REGISTRO DE USUARIO ============
@app.route('/register', methods=['GET','POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        nombre_limpio = form.nombre.data.strip().title()
        resp = crear_usuario(
            nombre=nombre_limpio,
            correo=form.correo.data,
            contrasena=form.password.data,
            genero=form.genero.data,
            edad=form.edad.data
        )
        if resp["ok"]:
            flash("Registrado correctamente.", "success")
            return redirect(url_for("login"))
        else:
            flash(f"Error: {resp.get('error')}", "danger")
    return render_template("register.html", form=form)


# ========= LISTAR HÁBITOS ============
@app.route('/habits')
@login_required
def habits():
    id_usuario = session["id_usuario"]
    resp = listar_habitos_por_usuario(id_usuario)
    form = HabitForm()
    form.categoria.choices = [(1,"Salud"),(2,"Ejercicio"),(3,"Productividad"),(4,"Sueño"),(5,"Alimentación")]
    return render_template("habits.html", habitos=resp["habitos"], form=form)


# ========= CREAR HÁBITO ============
@app.route('/habits/crear', methods=['POST'])
@login_required
def crear_habito():
    form = HabitForm()
    form.categoria.choices = [(1,"Salud"),(2,"Ejercicio"),(3,"Productividad"),(4,"Sueño"),(5,"Alimentación")]

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


# ========= REGISTRO DE PROGRESO ============
@app.route('/registro_progreso')
@login_required
def registro_progreso():
    id_usuario = session["id_usuario"]
    today = date.today()
    conn = get_connection()

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM habitos WHERE id_usuario = %s AND frecuencia = 'diario'", (id_usuario,))
        habitos = cursor.fetchall()

    habitos_diarios = []
    for h in habitos:
        with conn.cursor() as cursor:
            cursor.execute("SELECT completado FROM registro_progreso WHERE id_habito = %s AND fecha = %s", (h["id_habito"], today.isoformat()))
            row = cursor.fetchone()
        h["completado_hoy"] = row["completado"] if row else False
        habitos_diarios.append(h)
    conn.close()

    total_hoy = len(habitos_diarios)
    completados_hoy = sum(1 for h in habitos_diarios if h["completado_hoy"])
    porcentaje = int((completados_hoy / total_hoy) * 100) if total_hoy > 0 else 0

    return render_template("registro_progreso.html", 
        habitos_diarios=habitos_diarios, 
        total_hoy=total_hoy, 
        completados_hoy=completados_hoy, 
        porcentaje_completado=porcentaje,
        today_date=today.strftime("%A, %d de %B de %Y"),
        motivational_message="¡Sigue así!"
    )


# ========= REPORTES ============
@app.route('/reportes')
@login_required
def reportes():
    id_usuario = session["id_usuario"]
    resultado = generar_reporte_semanal(id_usuario)
    return render_template("reportes.html", reportes=[resultado] if resultado["hay_reporte"] else None)


# ========= NUEVA RUTA ADMIN: ELIMINAR USUARIO (SIN PARPADEO) ============
@app.route('/admin/eliminar/<int:id_user>', methods=['POST'])
@login_required
def admin_eliminar_usuario(id_user):
    """
    Ruta híbrida:
    - Si recibe ?ajax=1 (desde el JS de SweetAlert), responde JSON.
    - Si no, hace redirect (fallback tradicional).
    """
    # Seguridad
    if not session.get("es_admin"):
        if request.args.get('ajax'):
            return jsonify({"ok": False, "error": "No autorizado"}), 403
        return redirect(url_for("index"))
    
    resp = eliminar_usuario_desde_admin(
        id_admin=session["id_usuario"], 
        id_usuario_a_eliminar=id_user, 
        motivo="Eliminado desde Dashboard Web"
    )
    
    # 1. RESPUESTA JSON PARA AJAX (EVITA RECARGA)
    if request.args.get('ajax'):
        return jsonify(resp)
    
    # 2. RESPUESTA NORMAL (FALLBACK)
    if resp["ok"]:
        flash("Usuario eliminado correctamente.", "success")
    else:
        flash(f"Error al eliminar: {resp.get('error')}", "danger")
        
    return redirect(url_for("index"))
