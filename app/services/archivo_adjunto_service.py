from sqlalchemy.orm import Session
from app.models import ArchivoAdjunto, Aporte, PagoPrestamo, User
from app.config import settings
import boto3
from botocore.client import Config
from fastapi import UploadFile, HTTPException
import uuid
from datetime import datetime
import mimetypes

class ArchivoAdjuntoService:

    @staticmethod
    def subir_archivo_adjunto(
        db: Session,
        archivo: UploadFile,
        id_usuario: int,
        id_aporte: int = None,
        id_pago_prestamo: int = None
    ) -> ArchivoAdjunto:
        """
        Sube un archivo adjunto a Firebase Storage y crea el registro en la base de datos.
        """
        # Validar que se proporcione al menos un ID de aporte o pago
        if not id_aporte and not id_pago_prestamo:
            raise HTTPException(status_code=400, detail="Debe proporcionar id_aporte o id_pago_prestamo")

        # Validar que el usuario existe
        usuario = db.query(User).filter(User.id == id_usuario).first()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Validar aporte si se proporciona y obtener natillera_id
        natillera_id = None
        if id_aporte:
            aporte = db.query(Aporte).filter(Aporte.id == id_aporte).first()
            if not aporte:
                raise HTTPException(status_code=404, detail="Aporte no encontrado")
            # Verificar que el usuario es el propietario del aporte
            if aporte.user_id != id_usuario:
                raise HTTPException(status_code=403, detail="No tienes permisos para subir archivos a este aporte")
            natillera_id = aporte.natillera_id

        # Validar pago de préstamo si se proporciona y obtener natillera_id
        if id_pago_prestamo:
            pago = db.query(PagoPrestamo).filter(PagoPrestamo.id == id_pago_prestamo).first()
            if not pago:
                raise HTTPException(status_code=404, detail="Pago de préstamo no encontrado")
            # Verificar que el usuario es el registrador del pago
            if pago.registrado_por != id_usuario:
                raise HTTPException(status_code=403, detail="No tienes permisos para subir archivos a este pago")
            natillera_id = pago.prestamo.natillera_id

        # Validar tipo de archivo (solo PDFs, imágenes, documentos comunes)
        tipos_permitidos = [
            'application/pdf',
            'image/jpeg', 'image/png', 'image/gif',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        if archivo.content_type not in tipos_permitidos:
            raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

        # Validar tamaño (máximo 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        contenido = archivo.file.read()
        if len(contenido) > max_size:
            raise HTTPException(status_code=400, detail="Archivo demasiado grande (máximo 5MB)")

        # Generar nombre único para el archivo
        extension = mimetypes.guess_extension(archivo.content_type) or '.bin'
        nombre_unico = f"{uuid.uuid4()}{extension}"

        # Subir a MinIO (compatible con S3)
        try:
            print(f"MinIO config: endpoint={settings.MINIO_ENDPOINT}, bucket={settings.MINIO_BUCKET_NAME}")
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

            key = f"{natillera_id}/archivos_adjuntos/{nombre_unico}"
            print(f"Uploading to key: {key}")
            s3_client.put_object(
                Bucket=settings.MINIO_BUCKET_NAME,
                Key=key,
                Body=contenido,
                ContentType=archivo.content_type
                # Removido ACL para evitar errores en MinIO
            )
            print(f"File uploaded to MinIO with key: {key}")
            # Generar URL presigned para acceso temporal (1 hora)
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.MINIO_BUCKET_NAME, 'Key': key},
                ExpiresIn=3600  # 1 hora
            )
            print(f"Generated presigned URL: {url}")

        except Exception as e:
            print(f"Error subiendo a MinIO: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error subiendo archivo a MinIO: {str(e)}")

        # Crear registro en la base de datos
        nuevo_archivo = ArchivoAdjunto(
            nombre_archivo=archivo.filename,
            ruta_archivo=key,  # Guardar la key
            tipo_archivo=archivo.content_type,
            tamano=len(contenido),
            fecha_subida=datetime.utcnow(),
            id_aporte=id_aporte,
            id_pago_prestamo=id_pago_prestamo,
            id_usuario=id_usuario
        )

        db.add(nuevo_archivo)
        db.commit()
        db.refresh(nuevo_archivo)

        # Generar URL para el response
        nuevo_archivo.ruta_archivo = url  # Cambiar temporalmente para response

        return nuevo_archivo

    @staticmethod
    def obtener_archivos_por_aporte(db: Session, id_aporte: int, id_usuario: int) -> list[ArchivoAdjunto]:
        """
        Obtiene todos los archivos adjuntos de un aporte.
        """
        aporte = db.query(Aporte).filter(Aporte.id == id_aporte).first()
        if not aporte:
            raise HTTPException(status_code=404, detail="Aporte no encontrado")

        # Verificar permisos (usuario debe ser miembro de la natillera)
        if aporte.user_id != id_usuario and not any(u.id == id_usuario for u in aporte.natillera.members):
            raise HTTPException(status_code=403, detail="No tienes permisos para ver estos archivos")

        archivos = db.query(ArchivoAdjunto).filter(ArchivoAdjunto.id_aporte == id_aporte).all()
        # Generar URLs para cada archivo
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
        for archivo in archivos:
            archivo.ruta_archivo = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.MINIO_BUCKET_NAME, 'Key': archivo.ruta_archivo},
                ExpiresIn=3600
            )
        return archivos

    @staticmethod
    def obtener_archivos_por_pago_prestamo(db: Session, id_pago_prestamo: int, id_usuario: int) -> list[ArchivoAdjunto]:
        """
        Obtiene todos los archivos adjuntos de un pago de préstamo.
        """
        pago = db.query(PagoPrestamo).filter(PagoPrestamo.id == id_pago_prestamo).first()
        if not pago:
            raise HTTPException(status_code=404, detail="Pago de préstamo no encontrado")

        # Verificar permisos (usuario debe ser miembro de la natillera)
        if pago.registrado_por != id_usuario and not any(u.id == id_usuario for u in pago.prestamo.natillera.members):
            raise HTTPException(status_code=403, detail="No tienes permisos para ver estos archivos")

        archivos = db.query(ArchivoAdjunto).filter(ArchivoAdjunto.id_pago_prestamo == id_pago_prestamo).all()
        # Generar URLs
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
        for archivo in archivos:
            archivo.ruta_archivo = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.MINIO_BUCKET_NAME, 'Key': archivo.ruta_archivo},
                ExpiresIn=3600
            )
        return archivos

    @staticmethod
    def obtener_archivo_por_id(db: Session, id_archivo: int, id_usuario: int) -> ArchivoAdjunto:
        """
        Obtiene un archivo adjunto por ID con verificación de permisos.
        """
        archivo = db.query(ArchivoAdjunto).filter(ArchivoAdjunto.id == id_archivo).first()
        if not archivo:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")

        # Verificar permisos
        if archivo.id_usuario != id_usuario:
            # Si no es el propietario, verificar si es miembro de la natillera relacionada
            if archivo.aporte:
                if not any(u.id == id_usuario for u in archivo.aporte.natillera.members):
                    raise HTTPException(status_code=403, detail="No tienes permisos para acceder a este archivo")
            elif archivo.pago_prestamo:
                if not any(u.id == id_usuario for u in archivo.pago_prestamo.prestamo.natillera.members):
                    raise HTTPException(status_code=403, detail="No tienes permisos para acceder a este archivo")

        # Generar URL
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
        archivo.ruta_archivo = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.MINIO_BUCKET_NAME, 'Key': archivo.ruta_archivo},
            ExpiresIn=3600
        )
        return archivo

    @staticmethod
    def eliminar_archivo(db: Session, id_archivo: int, id_usuario: int):
        """
        Elimina un archivo adjunto y lo borra de Firebase Storage.
        """
        archivo = ArchivoAdjuntoService.obtener_archivo_por_id(db, id_archivo, id_usuario)

        # Solo el propietario puede eliminar
        if archivo.id_usuario != id_usuario:
            raise HTTPException(status_code=403, detail="Solo el propietario puede eliminar este archivo")

        # Eliminar de MinIO
        try:
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
            # La ruta_archivo ahora es la key
            key = archivo.ruta_archivo
            print(f"Deleting key: {key}")
            s3_client.delete_object(Bucket=settings.MINIO_BUCKET_NAME, Key=key)
        except Exception as e:
            # Loggear error pero continuar con eliminación de DB
            print(f"Error eliminando archivo de MinIO: {str(e)}")

        # Eliminar de base de datos
        db.delete(archivo)
        db.commit()
