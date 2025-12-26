from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.archivo_adjunto_service import ArchivoAdjuntoService
from app.auth.dependencies import get_current_user
from app.models import User
from app.config import settings
import boto3
from botocore.client import Config
from typing import List, Optional

router = APIRouter(
    prefix="/archivos_adjuntos",
    tags=["archivos_adjuntos"]
)

@router.post("/subir")
async def subir_archivo_adjunto(
    archivo: UploadFile = File(...),
    id_aporte: Optional[int] = Form(None),
    id_pago_prestamo: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sube un archivo adjunto para un aporte o pago de préstamo.
    """
    archivo_adjunto = ArchivoAdjuntoService.subir_archivo_adjunto(
        db=db,
        archivo=archivo,
        id_usuario=current_user.id,
        id_aporte=id_aporte,
        id_pago_prestamo=id_pago_prestamo
    )
    return {
        "id": archivo_adjunto.id,
        "nombre_archivo": archivo_adjunto.nombre_archivo,
        "ruta_archivo": archivo_adjunto.ruta_archivo,
        "tipo_archivo": archivo_adjunto.tipo_archivo,
        "tamano": archivo_adjunto.tamano,
        "fecha_subida": archivo_adjunto.fecha_subida
    }

@router.get("/aporte/{id_aporte}")
def obtener_archivos_por_aporte(
    id_aporte: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los archivos adjuntos de un aporte.
    """
    archivos = ArchivoAdjuntoService.obtener_archivos_por_aporte(
        db=db,
        id_aporte=id_aporte,
        id_usuario=current_user.id
    )
    return [
        {
            "id": a.id,
            "nombre_archivo": a.nombre_archivo,
            "ruta_archivo": a.ruta_archivo,
            "tipo_archivo": a.tipo_archivo,
            "tamano": a.tamano,
            "fecha_subida": a.fecha_subida
        }
        for a in archivos
    ]

@router.get("/pago_prestamo/{id_pago_prestamo}")
def obtener_archivos_por_pago_prestamo(
    id_pago_prestamo: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todos los archivos adjuntos de un pago de préstamo.
    """
    archivos = ArchivoAdjuntoService.obtener_archivos_por_pago_prestamo(
        db=db,
        id_pago_prestamo=id_pago_prestamo,
        id_usuario=current_user.id
    )
    return [
        {
            "id": a.id,
            "nombre_archivo": a.nombre_archivo,
            "ruta_archivo": a.ruta_archivo,
            "tipo_archivo": a.tipo_archivo,
            "tamano": a.tamano,
            "fecha_subida": a.fecha_subida
        }
        for a in archivos
    ]

@router.get("/{id_archivo}/descargar")
def descargar_archivo(
    id_archivo: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Redirige a la URL de descarga de un archivo adjunto.
    """
    archivo = ArchivoAdjuntoService.obtener_archivo_por_id(
        db=db,
        id_archivo=id_archivo,
        id_usuario=current_user.id
    )
    # El método obtener_archivo_por_id ya genera la URL presigned en ruta_archivo
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=archivo.ruta_archivo)

@router.delete("/{id_archivo}")
def eliminar_archivo(
    id_archivo: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un archivo adjunto.
    """
    ArchivoAdjuntoService.eliminar_archivo(
        db=db,
        id_archivo=id_archivo,
        id_usuario=current_user.id
    )
    return {"message": "Archivo eliminado exitosamente"}

@router.get("/proxy/{id_archivo}")
def proxy_archivo(
    id_archivo: int,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Proxy para servir archivos adjuntos desde el mismo dominio, evitando problemas de CORS.
    """
    from app.auth.firebase_auth import verify_token

    try:
        # Si no hay token, intentar obtener el usuario actual de la sesión
        # Para desarrollo, permitir acceso sin token (solo para testing)
        current_user = None

        if token:
            current_user = verify_token(token, db)
            if not current_user:
                raise HTTPException(status_code=401, detail="Token inválido")
        else:
            # Para testing: buscar el primer usuario
            # En producción, esto debería requerir autenticación
            current_user = db.query(User).first()
            if not current_user:
                raise HTTPException(status_code=401, detail="Usuario no encontrado")

        # Obtener información del archivo directamente de la BD
        archivo = db.query(ArchivoAdjunto).filter(ArchivoAdjunto.id == id_archivo).first()
        if not archivo:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")

        print(f"Archivo encontrado: ID={archivo.id}, Ruta={archivo.ruta_archivo}")

        # Verificar permisos
        if archivo.id_usuario != current_user.id:
            # Si no es el propietario, verificar si es miembro de la natillera
            has_permission = False
            if archivo.aporte and archivo.aporte.natillera:
                has_permission = any(u.id == current_user.id for u in archivo.aporte.natillera.members)
            elif archivo.pago_prestamo and archivo.pago_prestamo.prestamo and archivo.pago_prestamo.prestamo.natillera:
                has_permission = any(u.id == current_user.id for u in archivo.pago_prestamo.prestamo.natillera.members)

            if not has_permission:
                raise HTTPException(status_code=403, detail="No tienes permisos para acceder a este archivo")

        # Descargar el archivo desde MinIO
        s3_client = boto3.client(
            's3',
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(
                signature_version='s3v4',
                region_name='us-east-1',
                s3={'addressing_style': 'path'}
            ),
            verify=False
        )

        # Obtener el objeto desde MinIO
        response = s3_client.get_object(Bucket=settings.MINIO_BUCKET_NAME, Key=archivo.ruta_archivo)

        # Leer el contenido
        file_content = response['Body'].read()

        # Crear respuesta con el contenido del archivo
        return Response(
            content=file_content,
            media_type=archivo.tipo_archivo,
            headers={
                "Content-Disposition": f"inline; filename={archivo.nombre_archivo}",
                "Cache-Control": "private, max-age=3600"
            }
        )

    except HTTPException:
        # Re-lanzar excepciones HTTP
        raise
    except Exception as e:
        print(f"Error en proxy_archivo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo archivo: {str(e)}")