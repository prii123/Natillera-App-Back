from sqlalchemy.orm import Session
from app.models import User
from app.schemas import UserCreate
from typing import Optional
import random
import string

class UserService:
    @staticmethod
    def _generate_unique_username(db: Session, base_username: str) -> str:
        """Genera un username único basado en el username base"""
        username = base_username
        counter = 1
        
        # Intentar con el username base primero
        while UserService.get_user_by_username(db, username):
            # Si ya existe, agregar un número
            username = f"{base_username}{counter}"
            counter += 1
            
            # Si el contador es muy alto, agregar caracteres aleatorios
            if counter > 100:
                random_suffix = ''.join(random.choices(string.digits, k=4))
                username = f"{base_username}{random_suffix}"
                break
        
        return username
    
    @staticmethod
    def create_user(db: Session, firebase_uid: str, email: str, username: str, full_name: str) -> User:
        """Crea un nuevo usuario vinculado a Firebase"""
        # Generar username único si el proporcionado ya existe
        unique_username = UserService._generate_unique_username(db, username)
        
        db_user = User(
            firebase_uid=firebase_uid,
            email=email,
            username=unique_username,
            full_name=full_name
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Obtiene un usuario por email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Obtiene un usuario por username"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Obtiene un usuario por ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_firebase_uid(db: Session, firebase_uid: str) -> Optional[User]:
        """Obtiene un usuario por Firebase UID"""
        return db.query(User).filter(User.firebase_uid == firebase_uid).first()
