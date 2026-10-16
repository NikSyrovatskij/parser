import io
import qrcode
from qrcode.constants import ERROR_CORRECT_M


def generate_qr_code(data: str, box_size: int = 8, border: int = 2) -> bytes:
    """
    Генерирует PNG-изображение QR-кода из переданных данных (ссылки vless, hysteria2 и т.д.).
    Возвращает байты изображения (PNG).
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio.getvalue()

