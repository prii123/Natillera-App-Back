# Natillera - Sistema de Ahorro Colaborativo

Sistema de ahorro colaborativo (natilleras) con autenticación Firebase y backend FastAPI + PostgreSQL.

## 🚀 Tecnologías

### Backend
- **FastAPI** - Framework web moderno de Python
- **PostgreSQL** - Base de datos relacional
- **SQLAlchemy** - ORM para Python
- **Alembic** - Migraciones de base de datos
- **Firebase Admin SDK** - Autenticación

### Frontend
- **HTML + CSS + JavaScript** vanilla
- **Firebase Authentication** - Gestión de usuarios
- **Firebase Hosting** - Hosting del frontend

## 📦 Instalación y Configuración

### 1. Configurar Firebase y MinIO

1. Crea un proyecto en [Firebase Console](https://console.firebase.google.com)
2. Habilita **Authentication** con método Email/Password
3. Configura **Hosting**
4. Descarga las credenciales del servicio:
   - Ve a Project Settings > Service Accounts
   - Genera una nueva clave privada
   - Guarda el archivo JSON como `firebase-credentials.json` en la raíz del proyecto

5. Configura **MinIO** para almacenamiento de archivos:
   - Instala y ejecuta MinIO server (e.g., `minio server /data`)
   - Crea un bucket llamado `natillera-files`
   - Obtén las credenciales de acceso (access key y secret key)

6. Copia la configuración web de Firebase:
   - Ve a Project Settings > General
   - En "Your apps", copia la configuración
   - Pega en `frontend/firebase-config.js`

### 2. Configurar variables de entorno

Edita el archivo `.env`:

```env
DATABASE_URL=postgresql://natillera_user:natillera_password@db:5432/natillera_db
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=tu_access_key
MINIO_SECRET_KEY=tu_secret_key
MINIO_BUCKET_NAME=natillera-files
SECRET_KEY=tu-secret-key-aqui
```

### 3. Ejecutar con Docker

```bash
docker-compose up --build
```

Acceso:
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:8000/static/login.html

### 4. Desarrollo local (sin Docker)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar migraciones
alembic upgrade head

# Ejecutar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🌐 Desplegar Frontend en Firebase Hosting

```bash
cd frontend

# Instalar Firebase CLI (si no lo tienes)
npm install -g firebase-tools

# Login
firebase login

# Inicializar (solo primera vez)
firebase init hosting

# Desplegar
firebase deploy --only hosting
```

## 📚 Estructura del Proyecto

```
natillera/
├── app/
│   ├── auth/
│   │   ├── firebase_auth.py       # Verificación de tokens Firebase
│   │   └── dependencies.py        # Dependencias de autenticación
│   ├── models/                    # Modelos SQLAlchemy
│   ├── routers/                   # Endpoints de la API
│   ├── schemas/                   # Schemas Pydantic
│   ├── services/                  # Lógica de negocio
│   ├── config.py                  # Configuración
│   ├── database.py                # Conexión a BD
│   └── main.py                    # Aplicación principal
├── frontend/
│   ├── auth.js                    # Autenticación Firebase
│   ├── natilleras.js              # Gestión de natilleras
│   ├── aportes.js                 # Gestión de aportes
│   ├── styles.css                 # Estilos
│   ├── login.html                 # Página de login
│   ├── register.html              # Página de registro
│   ├── dashboard_usuario.html     # Panel de usuario
│   ├── dashboard_creador.html     # Panel de creador
│   ├── firebase-config.js         # Configuración Firebase
│   ├── firebase.json              # Configuración Hosting
│   └── .firebaserc                # Proyecto Firebase
├── alembic/                       # Migraciones
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

## 🔐 Flujo de Autenticación

1. Usuario se registra/login en Firebase (frontend)
2. Firebase genera un token JWT
3. Frontend envía el token al backend
4. Backend verifica el token con Firebase Admin SDK
5. Backend sincroniza el usuario en PostgreSQL
6. Todas las operaciones usan el token de Firebase

## 📖 API Endpoints

### Autenticación
- `POST /auth/sync-user` - Sincronizar usuario de Firebase

### Usuarios
- `GET /users/me` - Obtener información del usuario actual

### Natilleras
- `POST /natilleras/` - Crear natillera
- `GET /natilleras/` - Obtener natilleras del usuario
- `GET /natilleras/created` - Obtener natilleras creadas
- `GET /natilleras/{id}` - Obtener detalle de natillera
- `POST /natilleras/{id}/members/{user_id}` - Agregar miembro

### Aportes
- `POST /aportes/` - Registrar aporte
- `GET /aportes/my-aportes` - Obtener aportes del usuario
- `GET /aportes/natillera/{id}` - Obtener aportes de natillera (creador)
- `PATCH /aportes/{id}` - Aprobar/rechazar aporte (creador)

## 🎯 Funcionalidades

✅ Autenticación con Firebase  
✅ Registro y login de usuarios  
✅ Crear y gestionar natilleras  
✅ Agregar miembros a natilleras  
✅ Registrar aportes mensuales  
✅ Aprobar/rechazar aportes (creadores)  
✅ Panel de usuario con historial  
✅ Panel de creador con vista completa  
✅ Validaciones de permisos por rol  
✅ Subida de archivos adjuntos para aportes y pagos de préstamos (almacenados en MinIO)

## 📝 API Endpoints - Archivos Adjuntos

- `POST /archivos_adjuntos/subir` - Subir archivo adjunto (para aporte o pago de préstamo)
- `GET /archivos_adjuntos/aporte/{id_aporte}` - Listar archivos de un aporte
- `GET /archivos_adjuntos/pago_prestamo/{id_pago_prestamo}` - Listar archivos de un pago de préstamo
- `GET /archivos_adjuntos/{id}/descargar` - Obtener URL de descarga de un archivo
- `DELETE /archivos_adjuntos/{id}` - Eliminar archivo adjunto

## 📝 Licencia

MIT
- JWT Authentication
- Pydantic

### Frontend
- HTML5
- CSS3
- JavaScript (Vanilla)

### DevOps
- Docker
- Docker Compose

## 🚀 Instalación y Uso

### Requisitos Previos
- Docker
- Docker Compose

### Pasos para ejecutar

1. Clonar el repositorio y navegar a la carpeta:
```bash
cd natillera
```

2. Crear archivo `.env` (ya existe uno de ejemplo):
```bash
cp .env.example .env
```

3. Levantar los contenedores:
```bash
docker-compose up --build
```

4. La aplicación estará disponible en:
- **Frontend**: http://localhost:8000/static/login.html
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📁 Estructura del Proyecto

```
natillera/
├── app/
│   ├── auth/               # Autenticación y seguridad
│   │   ├── security.py     # Funciones JWT y hashing
│   │   └── dependencies.py # Dependencias de autenticación
│   ├── models/             # Modelos SQLAlchemy
│   │   └── __init__.py     # User, Natillera, Aporte
│   ├── routers/            # Endpoints de la API
│   │   ├── auth.py         # /auth/register, /auth/login
│   │   ├── users.py        # /users/me
│   │   ├── natilleras.py   # /natilleras/*
│   │   └── aportes.py      # /aportes/*
│   ├── schemas/            # Schemas Pydantic
│   │   └── __init__.py
│   ├── services/           # Lógica de negocio
│   │   ├── user_service.py
│   │   ├── natillera_service.py
│   │   └── aporte_service.py
│   ├── config.py           # Configuración
│   ├── database.py         # Conexión a BD
│   └── main.py             # Aplicación FastAPI
├── alembic/                # Migraciones de BD
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── frontend/               # Archivos estáticos
│   ├── login.html
│   ├── register.html
│   ├── dashboard_usuario.html
│   ├── dashboard_creador.html
│   ├── styles.css
│   ├── auth.js
│   ├── natilleras.js
│   └── aportes.js
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
└── README.md
```

## 🔑 Endpoints de la API

### Autenticación
- `POST /auth/register` - Registrar nuevo usuario
- `POST /auth/login` - Iniciar sesión (OAuth2)

### Usuarios
- `GET /users/me` - Obtener usuario actual

### Natilleras
- `POST /natilleras/` - Crear natillera
- `GET /natilleras/` - Listar natilleras del usuario
- `GET /natilleras/created` - Listar natilleras creadas
- `GET /natilleras/{id}` - Obtener detalles de natillera
- `POST /natilleras/{id}/members/{user_id}` - Agregar miembro

### Aportes
- `POST /aportes/` - Registrar aporte
- `GET /aportes/my-aportes` - Listar aportes del usuario
- `GET /aportes/natillera/{id}` - Listar aportes de natillera (creador)
- `PATCH /aportes/{id}` - Aprobar/rechazar aporte (creador)

## 👥 Flujo de Uso

### Para Usuarios
1. Registrarse en `/static/register.html`
2. Iniciar sesión en `/static/login.html`
3. Crear o unirse a natilleras
4. Registrar aportes mensuales
5. Ver historial de aportes

### Para Creadores
1. Crear una natillera
2. Agregar miembros
3. Revisar aportes en `/static/dashboard_creador.html`
4. Aprobar o rechazar aportes con motivos

## 🗄️ Base de Datos

### Modelos Principales

**User**
- id, email, username, hashed_password, full_name

**Natillera**
- id, name, monthly_amount, creator_id

**Aporte**
- id, user_id, natillera_id, amount, month, year, status, rejection_reason

## 🔐 Seguridad

- Contraseñas hasheadas con bcrypt
- Autenticación JWT
- Tokens con expiración configurable
- Validación de permisos por rol

## 📝 Variables de Entorno

```env
DATABASE_URL=postgresql://natillera_user:natillera_password@db:5432/natillera_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 🛠️ Desarrollo

### Crear migración de Alembic
```bash
docker-compose exec web alembic revision --autogenerate -m "descripcion"
```

### Aplicar migraciones
```bash
docker-compose exec web alembic upgrade head
```

### Ver logs
```bash
docker-compose logs -f web
```

## 📦 Comandos Útiles

```bash
# Detener contenedores
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v

# Reconstruir contenedores
docker-compose up --build

# Ejecutar shell en contenedor
docker-compose exec web bash
```

## 🎨 Personalización

- Modifica `frontend/styles.css` para cambiar el diseño
- Ajusta las variables CSS en `:root` para cambiar colores
- Edita `app/config.py` para configuraciones del backend

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Haz fork del proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📞 Soporte

Para reportar problemas o sugerencias, abre un issue en el repositorio.
