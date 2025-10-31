from flask import render_template, flash, redirect, url_for, request, session
from app import app
from app.forms import LoginForm, RegistrationForm, HabitForm
from datetime import date, timedelta
from functools import wraps
import random

# --- "Base de datos" simulada principal (sin cambios) ---
habitos_db = [
    {'id': 1, 'nombre_habito': 'Leer 30 minutos al día', 'descripcion': 'Un capítulo de un libro de no-ficción.', 'frecuencia': 'Diario', 'id_categoria': 2, 'categoria': 'Crecimiento Personal'},
    {'id': 2, 'nombre_habito': 'Hacer ejercicio', 'descripcion': 'Rutina de 45 minutos en el gimnasio.', 'frecuencia': 'Semanal', 'id_categoria': 1, 'categoria': 'Salud'},
    {'id': 3, 'nombre_habito': 'Meditar 10 minutos', 'descripcion': 'Usando una app de meditación guiada.', 'frecuencia': 'Diario', 'id_categoria': 3, 'categoria': 'Bienestar Mental'}
]
categorias_db = {1: 'Salud', 2: 'Crecimiento personal', 3: 'Bienestar mental'}
next_habit_id = 4

# --- "Base de datos" simulada para el progreso (sin cambios) ---
progreso_diario_db = {}
today = date.today()
for i in range(15):
    current_date = today - timedelta(days=i)
    date_str = current_date.isoformat()
    progreso_diario_db[date_str] = {}
    habitos_diarios = [h for h in habitos_db if h['frecuencia'] == 'Diario']
    for habito in habitos_diarios:
        if random.random() > 0.3:
            progreso_diario_db[date_str][habito['id']] = True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Por favor inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- CORRECCIÓN: La función principal ahora se llama 'index' ---
@app.route('/') 
@app.route('/dashboard') # Mantenemos /dashboard por si hay enlaces antiguos
@login_required
def index(): # <-- FUNCIÓN RENOMBRADA DE 'dashboard' A 'index'
    # --- Lógica para el Dashboard (sin cambios) ---
    today = date.today()
    today_str = today.isoformat()
    habitos_hoy_raw = [h for h in habitos_db if h['frecuencia'] == 'Diario']
    habitos_de_hoy = []
    for habito in habitos_hoy_raw:
        progreso_hoy = progreso_diario_db.get(today_str, {})
        completado = progreso_hoy.get(habito['id'], False)
        habitos_de_hoy.append({**habito, 'completado_hoy': completado})
    
    racha_actual = 0
    for i in range(len(progreso_diario_db)):
        check_date = today - timedelta(days=i)
        check_date_str = check_date.isoformat()
        progreso_del_dia = progreso_diario_db.get(check_date_str, {})
        if any(progreso_del_dia.values()):
             racha_actual += 1
        else:
             break

    completados_semana = 0
    total_posibles_semana = 0
    for i in range(7):
        check_date = today - timedelta(days=i)
        check_date_str = check_date.isoformat()
        habitos_ese_dia = [h for h in habitos_db if h['frecuencia'] == 'Diario']
        total_posibles_semana += len(habitos_ese_dia)
        progreso_del_dia = progreso_diario_db.get(check_date_str, {})
        completados_semana += sum(1 for status in progreso_del_dia.values() if status)

    porcentaje_semanal = int((completados_semana / total_posibles_semana) * 100) if total_posibles_semana > 0 else 0
    estadisticas = { 'racha_actual': racha_actual, 'porcentaje_semanal': porcentaje_semanal }
    user = {'username': session.get('username', 'Usuario')}

    return render_template('dashboard.html', user=user, habitos_de_hoy=habitos_de_hoy, estadisticas=estadisticas)

# --- CORRECCIÓN: La ruta de login ahora redirige a 'index' ---
@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session['logged_in'] = True
        session['username'] = form.username.data
        flash(f'¡Bienvenido de vuelta, {form.username.data}!', 'success')
        return redirect(url_for('index')) # <-- CORREGIDO a 'index'
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))

@app.route('/habito/toggle/<int:habito_id>', methods=['POST'])
@login_required
def toggle_habito(habito_id):
    today_str = date.today().isoformat()
    if today_str not in progreso_diario_db:
        progreso_diario_db[today_str] = {}
    
    estado_actual = progreso_diario_db[today_str].get(habito_id, False)
    progreso_diario_db[today_str][habito_id] = not estado_actual
    
    return redirect(url_for('index')) # <-- CORREGIDO a 'index'

# --- La ruta de reportes sigue sin cambios ---
@app.route('/reportes')
@login_required
def reportes():
    # El resto de la función sigue igual...
    reportes_generados = []
    today = date.today()
    for i in range(4):
        fecha_fin_semana = today - timedelta(days=(today.weekday() + 1 + (i * 7)))
        fecha_inicio_semana = fecha_fin_semana - timedelta(days=6)
        habitos_semanales_completados = 0
        total_habitos_semanales = 0
        for day_offset in range(7):
            current_date = fecha_inicio_semana + timedelta(days=day_offset)
            date_str = current_date.isoformat()
            habitos_de_ese_dia = [h for h in habitos_db if h['frecuencia'] == 'Diario']
            total_habitos_semanales += len(habitos_de_ese_dia)
            progreso_ese_dia = progreso_diario_db.get(date_str, {})
            habitos_semanales_completados += sum(1 for h_id in progreso_ese_dia if progreso_ese_dia[h_id])
        porcentaje = int((habitos_semanales_completados / total_habitos_semanales) * 100) if total_habitos_semanales > 0 else 0
        reporte = { 'id': i, 'semana': f"Semana del {fecha_inicio_semana.strftime('%d/%m')} al {fecha_fin_semana.strftime('%d/%m')}", 'total_habitos': total_habitos_semanales, 'completados': habitos_semanales_completados, 'porcentaje_cumplimiento': porcentaje, 'mejor_racha': random.randint(3, 7), 'ruta_pdf_s3': url_for('descargar_reporte_pdf', semana_id=i) }
        reportes_generados.append(reporte)
    return render_template('reportes.html', title='Mis reportes', reportes=reportes_generados)


# --- RUTAS SIN CAMBIOS (Siguen funcionando igual) ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        flash('¡Felicidades, te has registrado correctamente!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Registro', form=form)

@app.route('/habits')
@login_required
def habits():
    form = HabitForm()
    form.categoria.choices = list(categorias_db.items())
    return render_template('habits.html', title='Mis hábitos', habitos=habitos_db, form=form, racha_actual=12, mejor_racha=45)

@app.route('/habits/crear', methods=['POST'])
@login_required
def crear_habito():
    global next_habit_id
    form = HabitForm()
    form.categoria.choices = list(categorias_db.items())
    if form.validate_on_submit():
        nuevo_habito = { 'id': next_habit_id, 'nombre_habito': form.nombre_habito.data, 'descripcion': form.descripcion.data, 'frecuencia': form.frecuencia.data, 'id_categoria': int(form.categoria.data), 'categoria': categorias_db.get(int(form.categoria.data)) }
        habitos_db.append(nuevo_habito)
        next_habit_id += 1
        flash('¡Hábito creado con éxito!', 'success')
    else:
        flash('Hubo un error al crear el hábito.', 'danger')
    return redirect(url_for('habits'))

@app.route('/habits/editar/<int:habito_id>', methods=['POST'])
@login_required
def editar_habito(habito_id):
    form = HabitForm()
    form.categoria.choices = list(categorias_db.items())
    if form.validate_on_submit():
        habito_a_editar = next((h for h in habitos_db if h['id'] == habito_id), None)
        if habito_a_editar:
            habito_a_editar['nombre_habito'] = form.nombre_habito.data
            habito_a_editar['descripcion'] = form.descripcion.data
            habito_a_editar['frecuencia'] = form.frecuencia.data
            habito_a_editar['id_categoria'] = int(form.categoria.data)
            habito_a_editar['categoria'] = categorias_db.get(int(form.categoria.data))
            flash('¡Hábito actualizado!', 'info')
        else:
            flash('Hábito no encontrado.', 'danger')
    else:
        flash('Error al editar el hábito.', 'danger')
    return redirect(url_for('habits'))

@app.route('/habits/eliminar/<int:habito_id>', methods=['POST'])
@login_required
def eliminar_habito(habito_id):
    global habitos_db
    habito_a_eliminar = next((h for h in habitos_db if h['id'] == habito_id), None)
    if habito_a_eliminar:
        habitos_db = [h for h in habitos_db if h['id'] != habito_id]
        flash('Hábito eliminado.', 'warning')
    else:
        flash('No se pudo eliminar el hábito.', 'danger')
    return redirect(url_for('habits'))

@app.route('/reporte/pdf/<int:semana_id>')
@login_required
def descargar_reporte_pdf(semana_id):
    today = date.today()
    fecha_fin_semana = today - timedelta(days=(today.weekday() + 1 + (semana_id * 7)))
    fecha_inicio_semana = fecha_fin_semana - timedelta(days=6)
    semana_str = f"Semana del {fecha_inicio_semana.strftime('%d/%m/%Y')} al {fecha_fin_semana.strftime('%d/%m/%Y')}"
    return render_template('reporte_pdf.html', semana=semana_str)

@app.route('/registro_progreso')
@login_required
def registro_progreso():
    today = date.today()
    today_str = today.isoformat()
    
    habitos_diarios_raw = [h for h in habitos_db if h['frecuencia'] == 'Diario']
    habitos_diarios = []
    
    for habito in habitos_diarios_raw:
        progreso_hoy = progreso_diario_db.get(today_str, {})
        completado = progreso_hoy.get(habito['id'], False)
        habitos_diarios.append({**habito, 'completado_hoy': completado})
    
    total_hoy = len(habitos_diarios)
    completados_hoy = sum(1 for h in habitos_diarios if h['completado_hoy'])
    porcentaje_completado = int((completados_hoy / total_hoy) * 100) if total_hoy > 0 else 0
    
    motivational_messages = [
        "¡Cada paso cuenta! Comienza con el primer hábito.",
        "¡Vas por buen camino! Sigue así.",
        "¡Increíble progreso! Ya casi terminas.",
        "¡Último empujón! Estás a punto de completar el día."
    ]
    
    if porcentaje_completado < 25:
        motivational_message = motivational_messages[0]
    elif porcentaje_completado < 50:
        motivational_message = motivational_messages[1]
    elif porcentaje_completado < 75:
        motivational_message = motivational_messages[2]
    else:
        motivational_message = motivational_messages[3]
    
    return render_template('registro_progreso.html',
                         habitos_diarios=habitos_diarios,
                         total_hoy=total_hoy,
                         completados_hoy=completados_hoy,
                         porcentaje_completado=porcentaje_completado,
                         today_date=today.strftime('%A, %d de %B de %Y'),
                         motivational_message=motivational_message)
