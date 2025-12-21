import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from app.config import settings
import os

# Inicializar Firebase solo si no está inicializado
if not firebase_admin._apps:
    if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
    else:
        # Para desarrollo local sin credenciales
        print("⚠️  Firebase credentials not found. Using development mode without Firebase Auth validation.")
        print("   Set FIREBASE_CREDENTIALS_PATH in .env to enable Firebase Auth")

def verify_firebase_token(token: str):
    """Verifica el token de Firebase y retorna el usuario decodificado"""
    try:
        if not firebase_admin._apps:
            # Modo desarrollo sin Firebase
            return None
        
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except firebase_auth.InvalidIdTokenError:
        return None
    except firebase_auth.ExpiredIdTokenError:
        return None
    except Exception as e:
        print(f"Error verificando token: {e}")
        return None

def get_firebase_user_by_uid(uid: str):
    """Obtiene información del usuario de Firebase por UID"""
    try:
        if not firebase_admin._apps:
            return None
        return firebase_auth.get_user(uid)
    except Exception as e:
        print(f"Error obteniendo usuario de Firebase: {e}")
        return None
