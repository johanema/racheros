from flask import Flask
from flask_bootstrap import Bootstrap5

# La variable principal se llama 'app'
app = Flask(__name__)

# Configuración de la llave secreta
app.config['SECRET_KEY'] = 'una-llave-secreta-muy-dificil-de-adivinar'

# Inicialización de Bootstrap
bootstrap = Bootstrap5(app)

# Importamos las rutas al final para evitar importaciones circulares
from app import routes

