from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange

class LoginForm(FlaskForm):
    """Formulario para el inicio de sesión de usuarios."""
    username = StringField('Usuario', validators=[DataRequired(), Email(message="Por favor, introduce una dirección de correo válida.")])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recuérdame')
    submit = SubmitField('Entrar')

class RegistrationForm(FlaskForm):
    """Formulario para el registro de nuevos usuarios."""
    nombre = StringField('Nombre completo', validators=[DataRequired(), Length(min=2, max=100)])
    correo = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Repetir Contraseña', validators=[DataRequired(), EqualTo('password', message='Las contraseñas deben coincidir.')])
    genero = SelectField('Género', choices=[('f', 'Femenino'), ('m', 'Masculino'), ('otro', 'Otro')], validators=[DataRequired()])
    edad = IntegerField('Edad', validators=[DataRequired(), NumberRange(min=13, max=120, message='Debes ser mayor de 13 años.')])
    submit = SubmitField('Registrarse')

