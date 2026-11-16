# utils/imagenes.py
"""Reduce el peso de las imágenes de estudios antes de subirlas a Supabase Storage."""
import io

from PIL import Image, ImageOps

LADO_MAXIMO = 1600      # px del lado más largo
CALIDAD_JPG = 85        # buena calidad visual, archivos 5–10 veces más ligeros que PNG


def _tiene_transparencia(img):
    if img.mode in ("RGBA", "LA"):
        return img.getchannel("A").getextrema()[0] < 255
    return img.mode == "P" and "transparency" in img.info


def optimizar_imagen(datos: bytes):
    """Devuelve (bytes, extension, content_type).
    - Redimensiona a máximo LADO_MAXIMO px conservando proporción.
    - Convierte a JPG (o PNG optimizado si la imagen tiene transparencia).
    - Si por alguna razón el resultado pesa más, conserva el original.
    """
    try:
        img = Image.open(io.BytesIO(datos))
        formato_original = (img.format or "PNG").upper()
        img = ImageOps.exif_transpose(img)  # respeta la orientación de fotos de celular
        if max(img.size) > LADO_MAXIMO:
            img.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)

        salida = io.BytesIO()
        if _tiene_transparencia(img):
            img.save(salida, format="PNG", optimize=True)
            ext, tipo = "png", "image/png"
        else:
            modo = "L" if img.mode in ("L", "LA", "I", "I;16", "1") else "RGB"
            img.convert(modo).save(salida, format="JPEG", quality=CALIDAD_JPG, optimize=True, progressive=True)
            ext, tipo = "jpg", "image/jpeg"

        nuevo = salida.getvalue()
        if len(nuevo) < len(datos):
            return nuevo, ext, tipo
        ext_orig = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}.get(formato_original, "png")
        return datos, ext_orig, f"image/{'jpeg' if ext_orig == 'jpg' else ext_orig}"
    except Exception as e:
        print(f"⚠️ No se pudo optimizar la imagen, se sube original: {e}")
        return datos, "png", "image/png"


def ruta_desde_url(url_publica: str, bucket: str = "casos_clinicos"):
    """Extrae la ruta dentro del bucket a partir de la URL pública de Supabase."""
    marca = f"/object/public/{bucket}/"
    if url_publica and marca in url_publica:
        return url_publica.split(marca, 1)[1].split("?", 1)[0]
    return None
