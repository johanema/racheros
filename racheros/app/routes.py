from flask import render_template, flash, redirect, url_for
from app import app
from app.forms import LoginForm, RegistrationForm

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html',title="Inicio")

@app.route('/login',methods=['GET','POST'])
def login():
    form=LoginForm()
    if form.validate_on_submit():
        flash('inicio de sesión para el usuario {}, recuerdame={}'.format(form.username.data, form.remember_me))
        return redirect('/')
    return render_template('login.html',form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Aquí irá la lógica para crear el usuario en la base de datos
        # Por ejemplo: User(nombre=form.nombre.data, correo=form.correo.data, ...)
        flash('¡Felicidades, te has registrado correctamente!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Registro', form=form)
