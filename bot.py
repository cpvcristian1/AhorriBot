import asyncio
import logging
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    DEFAULT_MIN_DROP_PERCENT,
    DEFAULT_MIN_PRICE_EUR,
    CHECK_INTERVAL_SECONDS
)
from database import (
    init_db,
    is_already_notified,
    mark_as_notified,
    get_user_settings,
    update_user_setting,
    get_connection
)
from scrapers import fetch_camel_top_drops, fetch_chollometro_deals, is_tech_product

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuración global en memoria
GLOBAL_SETTINGS = {
    "filter_mode": "tech", # 'tech' o 'all'
    "chat_id": TELEGRAM_CHAT_ID
}

async def send_deal_notification(bot, chat_id: str, deal: dict):
    """Envía la alerta del producto con la gráfica de Keepa y botones de acción."""
    drop_pct = deal.get("drop_pct", 0)
    new_price = deal.get("new_price", 0)
    old_price = deal.get("old_price", 0)
    saved = old_price - new_price if old_price > new_price else 0
    title = deal.get("title", "Producto sin título")
    asin = deal.get("asin", "")
    amazon_url = deal.get("amazon_url", f"https://www.amazon.es/dp/{asin}")
    keepa_graph = deal.get("keepa_graph_url", f"https://graph.keepa.com/pricehistory.png?asin={asin}&domain=es")
    keepa_web = deal.get("keepa_web_url", f"https://keepa.com/#!product/4-{asin}")
    source = deal.get("source", "Amazon")

    caption = (
        f"🚨 <b>¡BAJADA DRÁSTICA DETECTADA! (-{drop_pct:.1f}%)</b>\n\n"
        f"📦 <b>{title}</b>\n\n"
        f"💰 <b>Precio Actual:</b> <code>{new_price:.2f} €</code>\n"
    )
    if old_price > 0:
        caption += f"❌ <b>Precio Anterior:</b> <s>{old_price:.2f} €</s>\n"
    if saved > 0:
        caption += f"📉 <b>Ahorro:</b> <code>{saved:.2f} €</code> (-{drop_pct:.1f}%)\n"
        
    caption += (
        f"🆔 <b>ASIN:</b> <code>{asin}</code>\n"
        f"📡 <b>Fuente:</b> {source}\n\n"
        f"<i>📊 Abajo tienes la gráfica histórica de Keepa: comprueba si está en mínimo histórico antes de comprar.</i>"
    )

    keyboard = [
        [
            InlineKeyboardButton("🛒 Ver en Amazon.es", url=amazon_url),
            InlineKeyboardButton("📈 Ver en Keepa", url=keepa_web)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Intentar enviar con la imagen de la gráfica de Keepa
        await bot.send_photo(
            chat_id=chat_id,
            photo=keepa_graph,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.warning(f"No se pudo cargar la imagen de Keepa ({e}), enviando mensaje de texto...")
        await bot.send_message(
            chat_id=chat_id,
            text=caption,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=False
        )

async def run_scan_and_notify(bot, chat_id: str):
    """Ejecuta una ronda de escaneo y notifica si encuentra chollos nuevos."""
    settings = get_user_settings(chat_id, DEFAULT_MIN_DROP_PERCENT, DEFAULT_MIN_PRICE_EUR)
    min_drop = settings["min_drop_pct"]
    min_price = settings["min_price"]
    mode = GLOBAL_SETTINGS.get("filter_mode", "tech")

    logger.info(f"Escaneando... Filtros: min_drop={min_drop}%, min_price={min_price}€, modo={mode}")
    
    # 1. Escaneo desde CamelCamelCamel
    camel_deals = fetch_camel_top_drops()
    notified_count = 0

    for deal in camel_deals:
        asin = deal["asin"]
        drop_pct = deal["drop_pct"]
        new_price = deal["new_price"]
        title = deal["title"]

        # Filtro de modo (tech vs all)
        if mode == "tech" and not is_tech_product(title):
            continue

        # Filtro de umbral de descuento
        if drop_pct < min_drop:
            continue

        # Filtro de precio mínimo
        if new_price < min_price:
            continue

        # Evitar duplicados
        if is_already_notified(asin):
            continue

        # Enviar notificación
        await send_deal_notification(bot, chat_id, deal)
        mark_as_notified(asin, title, new_price, deal["old_price"], drop_pct)
        notified_count += 1
        await asyncio.sleep(2) # Pequeño delay entre mensajes

    return notified_count

async def background_deal_scanner(application: Application):
    """Tarea en segundo plano que escanea permanentemente en busca de bajadas."""
    logger.info(f"Iniciando escáner en segundo plano (intervalo: {CHECK_INTERVAL_SECONDS}s)...")
    while True:
        target_chat = GLOBAL_SETTINGS.get("chat_id")
        if target_chat:
            try:
                await run_scan_and_notify(application.bot, target_chat)
            except Exception as e:
                logger.error(f"Error en escaneo en segundo plano: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

# --- COMANDOS DE TELEGRAM ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    GLOBAL_SETTINGS["chat_id"] = chat_id
    settings = get_user_settings(chat_id, DEFAULT_MIN_DROP_PERCENT, DEFAULT_MIN_PRICE_EUR)

    msg = (
        "👋 <b>¡Bienvenido al Cazador de Bajadas de Amazon!</b> 🎯\n\n"
        "Este bot vigila Amazon España 24/7 y te notificará al instante en el móvil "
        "cada vez que un producto de electrónica tenga una bajada de precio drástica.\n\n"
        f"📱 <b>Tu Chat ID:</b> <code>{chat_id}</code>\n"
        f"📉 <b>Bajada mínima requerida:</b> <code>{settings['min_drop_pct']}%</code>\n"
        f"💶 <b>Precio mínimo:</b> <code>{settings['min_price']} €</code>\n"
        f"🔍 <b>Modo actual:</b> <code>{GLOBAL_SETTINGS['filter_mode'].upper()}</code>\n\n"
        "<b>Comandos útiles:</b>\n"
        "• /test - Envía una alerta de prueba con gráfica Keepa\n"
        "• /scan - Fuerza un escaneo ahora mismo\n"
        "• /drop 40 - Cambia el % mínimo de caída (ej. 40%)\n"
        "• /minprice 25 - Cambia el precio mínimo (evita baratijas)\n"
        "• /mode tech - Solo electrónica (o <code>/mode all</code> para todo)\n"
        "• /status - Ver estadísticas y configuración activa"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía una notificación de prueba para verificar que las fotos y botones funcionan."""
    chat_id = str(update.effective_chat.id)
    sample_deal = {
        "source": "Prueba de Demostración",
        "asin": "B0B46PQNVS",
        "title": "Corsair K65 RGB MINI 60% Teclado Mecánico Gaming (Cherry MX Red)",
        "new_price": 39.99,
        "old_price": 63.94,
        "drop_pct": 37.5,
        "amazon_url": "https://www.amazon.es/dp/B0B46PQNVS",
        "keepa_graph_url": "https://graph.keepa.com/pricehistory.png?asin=B0B46PQNVS&domain=es",
        "keepa_web_url": "https://keepa.com/#!product/4-B0B46PQNVS"
    }
    await update.message.reply_text("🔔 Enviando alerta de prueba...")
    await send_deal_notification(context.bot, chat_id, sample_deal)

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("🔎 Escaneando las últimas bajadas de Amazon.es...")
    count = await run_scan_and_notify(context.bot, chat_id)
    if count == 0:
        await update.message.reply_text("✅ Escaneo completado. No hay nuevas bajadas que cumplan tus filtros ahora mismo.")
    else:
        await update.message.reply_text(f"🎯 Escaneo completado. Se han enviado {count} alertas nuevas.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    settings = get_user_settings(chat_id, DEFAULT_MIN_DROP_PERCENT, DEFAULT_MIN_PRICE_EUR)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM notified_deals")
    total_notified = cursor.fetchone()["total"]
    conn.close()

    msg = (
        "⚙️ <b>Estado del Sistema:</b>\n\n"
        f"• <b>Chat ID activo:</b> <code>{chat_id}</code>\n"
        f"• <b>Descuento mínimo:</b> <code>{settings['min_drop_pct']}%</code>\n"
        f"• <b>Precio mínimo:</b> <code>{settings['min_price']} €</code>\n"
        f"• <b>Modo de filtro:</b> <code>{GLOBAL_SETTINGS['filter_mode'].upper()}</code>\n"
        f"• <b>Intervalo de escaneo:</b> <code>{CHECK_INTERVAL_SECONDS} segundos</code>\n"
        f"• <b>Historial de chollos registrados:</b> <code>{total_notified}</code>\n\n"
        "<i>El robot sigue escuchando y enviará avisos en cuanto salte una oferta.</i>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def drop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not context.args:
        await update.message.reply_text("Uso: <code>/drop 35</code> (para filtrar por un 35% de bajada mínima)", parse_mode="HTML")
        return
    try:
        new_val = float(context.args[0])
        update_user_setting(chat_id, min_drop_pct=new_val)
        await update.message.reply_text(f"✅ Filtro actualizado: Ahora solo te avisaré con bajadas de al menos <b>{new_val}%</b>", parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ Por favor indica un número válido. Ejemplo: <code>/drop 40</code>", parse_mode="HTML")

async def minprice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not context.args:
        await update.message.reply_text("Uso: <code>/minprice 25</code> (para ignorar productos de menos de 25€)", parse_mode="HTML")
        return
    try:
        new_val = float(context.args[0])
        update_user_setting(chat_id, min_price=new_val)
        await update.message.reply_text(f"✅ Precio mínimo fijado en <b>{new_val} €</b>.", parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ Por favor indica un número válido. Ejemplo: <code>/minprice 20</code>", parse_mode="HTML")

async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0].lower() not in ["tech", "all"]:
        await update.message.reply_text("Uso: <code>/mode tech</code> (solo electrónica) o <code>/mode all</code> (todas las categorías)", parse_mode="HTML")
        return
    mode = context.args[0].lower()
    GLOBAL_SETTINGS["filter_mode"] = mode
    await update.message.reply_text(f"✅ Modo cambiado a: <b>{mode.upper()}</b>", parse_mode="HTML")

async def post_init(application: Application):
    """Inicia el escáner asíncrono en segundo plano tras arrancar el bot."""
    init_db()
    asyncio.create_task(background_deal_scanner(application))

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("[ERROR] Falta TELEGRAM_BOT_TOKEN en el archivo .env o variables de entorno.")
        print("Crea un bot con @BotFather en Telegram y coloca el token en el archivo .env")
        sys.exit(1)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("test", test_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("drop", drop_command))
    app.add_handler(CommandHandler("minprice", minprice_command))
    app.add_handler(CommandHandler("mode", mode_command))

    print("🤖 Bot de Chollos de Amazon iniciado. Pulsa Ctrl+C para detener.")
    app.run_polling()

if __name__ == "__main__":
    main()
