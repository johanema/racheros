from flask import Flask
from flask_bootstrap import Bootstrap5

# La variable principal se llama 'app'
app = Flask(__name__)

# --- CAMBIO CLAVE ---
# La configuración ahora está directamente aquí para simplificar las importaciones
# y evitar el error que estabas viendo.
app.config['SECRET_KEY'] = 'llave-secreta-y-debe-ser-dificil-de-adivinar'

bootstrap = Bootstrap5(app)

# Importamos las rutas al final para evitar importaciones circulares
from app import routes