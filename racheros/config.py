import os

class Config:
    """Configuraciones para la aplicación."""
    # Es una mejor práctica usar variables de entorno para la llave secreta,
    # pero definimos una por defecto para que funcione de inmediato.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'llave-secreta'

