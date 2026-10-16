import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Default Detection Thresholds
DEFAULT_MIN_DROP_PERCENT = float(os.getenv("MIN_DROP_PERCENT", "30.0"))  # Mínimo % de bajada (ej. 30%)
DEFAULT_MIN_PRICE_EUR = float(os.getenv("MIN_PRICE_EUR", "20.0"))        # Filtrar baratijas (cables, fundas de 2€)
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "120")) # Escanear cada 2 minutos

# Keywords de Electrónica y Tecnología (Productos pequeños / Tech)
TECH_KEYWORDS = [
    # Portátiles y Laptops (Específico)
    "portátil", "portatil", "laptop", "macbook", "notebook", "ultrabook", "chromebook",
    "thinkpad", "ideapad", "legion", "yoga", "zenbook", "vivobook", "tuf gaming",
    "rog strix", "zephyrus", "omen", "victus", "pavilion", "surface pro", "surface laptop",
    "galaxy book", "swift go", "msi gaming",

    # eBooks, e-Readers y Lectura Digital (Específico)
    "ebook", "e-book", "ereader", "e-reader", "lector de libros", "libro electrónico",
    "libro electronico", "lector electrónico", "lector electronico",
    "kindle", "paperwhite", "kindle oasis", "kindle scribe", "kobo", "kobo clara",
    "kobo libra", "kobo elipsa", "pocketbook", "onyx boox", "boox", "tagus", "woxter scriba",

    # Dispositivos Móviles y Tablets
    "smartphone", "móvil", "movil", "teléfono", "telefono", "iphone", "galaxy", "xiaomi", "redmi", "pixel",
    "tablet", "ipad",

    # Cámaras y Fotografía
    "cámara", "camara", "dslr", "mirrorless", "gopro", "action cam", "dji", "osmo", "canon", "sony", "nikon", "fujifilm", "objetivo", "lente",

    # Sonido y Wearables
    "auriculares", "headphones", "earbuds", "airpods", "altavoz", "speaker", "bluetooth", "soundbar",
    "smartwatch", "reloj inteligente", "garmin", "amazfit", "apple watch",

    # Informática y Gaming
    "monitor", "teclado", "ratón", "raton", "mouse", "teclado mecánico", "corsair", "logitech", "razer",
    "ssd", "nvme", "disco duro", "memoria ram", "tarjeta gráfica", "tarjeta grafica", "rtx", "rx",
    "consola", "nintendo switch", "playstation", "ps5", "xbox", "steam deck"
]

# Palabras a excluir para evitar accesorios no deseados si el precio es bajo
EXCLUDE_KEYWORDS = [
    "funda de silicona", "cristal templado", "protector de pantalla",
    "funda para portátil", "funda para kindle", "funda para tablet", "funda kindle",
    "cordón", "colgante para móvil", "tapa de objetivo", "pegatina"
]
