from flask import render_template, flash, redirect, url_for, request
from app import app
from app.forms import LoginForm, RegistrationForm, HabitForm
from datetime import date, timedelta
import random

# --- "Base de datos" simulada principal para los hábitos creados por el usuario ---
habitos_db = [
    {'id': 1, 'nombre_habito': 'Leer 30 minutos al día', 'descripcion': 'Un capítulo de un libro de no-ficción.', 'frecuencia': 'Diario', 'id_categoria': 2, 'categoria': 'Crecimiento Personal'},
    {'id': 2, 'nombre_habito': 'Hacer ejercicio', 'descripcion': 'Rutina de 45 minutos en el gimnasio.', 'frecuencia': 'Semanal', 'id_categoria': 1, 'categoria': 'Salud'},
    {'id': 3, 'nombre_habito': 'Meditar 10 minutos', 'descripcion': 'Usando una app de meditación guiada.', 'frecuencia': 'Diario', 'id_categoria': 3, 'categoria': 'Bienestar Mental'}
]
categorias_db = {1: 'Salud', 2: 'Crecimiento personal', 3: 'Bienestar mental'}
next_habit_id = 4

# --- "Base de datos" simulada para el progreso diario ---
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


@app.route('/')
@app.route('/index')
def index():
    return redirect(url_for('registro_progreso'))

@app.route('/login',methods=['GET','POST'])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        flash('inicio de sesión para el usuario {}, recuerdame={}'.format(form.username.data, form.remember_me))
        return redirect(url_for('registro_progreso'))
    return render_template('login.html',form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        flash('¡Felicidades, te has registrado correctamente!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Registro', form=form)

# RUTA PARA MOSTRAR Y GESTIONAR HÁBITOS (READ)
@app.route('/habits')
def habits():
    form = HabitForm()
    form.categoria.choices = list(categorias_db.items())
    return render_template('habits.html', title='Mis hábitos', habitos=habitos_db, form=form, racha_actual=12, mejor_racha=45)

# RUTA PARA CREAR UN NUEVO HÁBITO (CREATE)
@app.route('/habits/crear', methods=['POST'])
def crear_habito():
    global next_habit_id
    form = HabitForm()
    form.categoria.choices = list(categorias_db.items())
    if form.validate_on_submit():
        nuevo_habito = {
            'id': next_habit_id, 'nombre_habito': form.nombre_habito.data,
            'descripcion': form.descripcion.data, 'frecuencia': form.frecuencia.data,
            'id_categoria': int(form.categoria.data), 'categoria': categorias_db.get(int(form.categoria.data))
        }
        habitos_db.append(nuevo_habito)
        next_habit_id += 1
        flash('¡Hábito creado con éxito!', 'success')
    else:
        flash('Hubo un error al crear el hábito.', 'danger')
    return redirect(url_for('habits'))

# RUTA PARA EDITAR UN HÁBITO EXISTENTE (UPDATE)
@app.route('/habits/editar/<int:habito_id>', methods=['POST'])
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

# RUTA PARA ELIMINAR UN HÁBITO (DELETE)
@app.route('/habits/eliminar/<int:habito_id>', methods=['POST'])
def eliminar_habito(habito_id):
    global habitos_db
    habito_a_eliminar = next((h for h in habitos_db if h['id'] == habito_id), None)
    if habito_a_eliminar:
        habitos_db = [h for h in habitos_db if h['id'] != habito_id]
        flash('Hábito eliminado.', 'warning')
    else:
        flash('No se pudo eliminar el hábito.', 'danger')
    return redirect(url_for('habits'))


# --- INICIO DE LA CORRECCIÓN ---

@app.route('/registro')
def registro_progreso():
    today_str = date.today().isoformat()
    
    # ---- ESTA ES LA LÍNEA CORREGIDA ----
    # Antes filtraba solo los 'Diarios'. Ahora toma TODOS los hábitos.
    habitos_a_registrar = habitos_db
    
    habitos_para_mostrar = []
    # Iteramos sobre la lista completa
    for habito in habitos_a_registrar:
        progreso_hoy = progreso_diario_db.get(today_str, {})
        completado = progreso_hoy.get(habito['id'], False)
        habitos_para_mostrar.append({
            'id': habito['id'],
            'nombre': habito['nombre_habito'],
            'categoria': habito['categoria'],
            'completado': completado
        })

    # Ya no necesitamos 'total_hoy' ni 'completados_hoy' porque
    # la plantilla HTML ya no muestra la barra de progreso general.

    return render_template(
        'registro_progreso.html', 
        title='Registro de hoy', 
        habitos=habitos_para_mostrar
        # Quitamos total_hoy y completados_hoy de aquí
    )
    
# --- FIN DE LA CORRECCIÓN ---


@app.route('/habito/toggle/<int:habito_id>', methods=['POST'])
def toggle_habito(habito_id):
    today_str = date.today().isoformat()
    if today_str not in progreso_diario_db:
        progreso_diario_db[today_str] = {}
    
    estado_actual = progreso_diario_db[today_str].get(habito_id, False)
    progreso_diario_db[today_str][habito_id] = not estado_actual
        
    return redirect(url_for('registro_progreso'))

@app.route('/reportes')
def reportes():
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
        
        reporte = {
            'id': i,
            'semana': f"Semana del {fecha_inicio_semana.strftime('%d/%m')} al {fecha_fin_semana.strftime('%d/%m')}",
            'total_habitos': total_habitos_semanales,
            'completados': habitos_semanales_completados,
            'porcentaje_cumplimiento': porcentaje,
            'mejor_racha': random.randint(3, 7),
            'ruta_pdf_s3': url_for('descargar_reporte_pdf', semana_id=i)
        }
        reportes_generados.append(reporte)
        
    return render_template('reportes.html', title='Mis reportes', reportes=reportes_generados)

@app.route('/reporte/pdf/<int:semana_id>')
def descargar_reporte_pdf(semana_id):
    today = date.today()
    fecha_fin_semana = today - timedelta(days=(today.weekday() + 1 + (semana_id * 7)))
    fecha_inicio_semana = fecha_fin_semana - timedelta(days=6)
    semana_str = f"Semana del {fecha_inicio_semana.strftime('%d/%m/%Y')} al {fecha_fin_semana.strftime('%d/%m/%Y')}"

    return render_template('reporte_pdf.html', semana=semana_str)