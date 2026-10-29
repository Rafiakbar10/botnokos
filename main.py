import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Konfigurasi Logging untuk memantau error di Railway
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Mengambil variabel token dari Environment Variables Railway
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NOMERIN_API_KEY = os.getenv("NOMERIN_API_KEY")

NOMERIN_BASE_URL = "https://api.nomerin.id/v1"

def get_headers():
    return {
        "Authorization": f"Bearer {NOMERIN_API_KEY}",
        "Content-Type": "application/json"
    }

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Cek Saldo", callback_data="cek_saldo")],
        [InlineKeyboardButton("📦 Cara Order", callback_data="cara_order")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_msg = (
        "👋 **Selamat Datang di Bot Order Nomerin!**\n\n"
        "Gunakan tombol di bawah atau perintah berikut:\n"
        "• `/order <service_id> <country_id> <harga>` - Buat pesanan baru\n"
        "• `/cek <order_id>` - Cek SMS / Kode OTP\n"
        "• `/batal <order_id>` - Batalkan pesanan"
    )
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")

# Handler Tombol Menu
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cek_saldo":
        try:
            res = requests.get(f"{NOMERIN_BASE_URL}/profile", headers=get_headers())
            data = res.json()
            if data.get("success"):
                balance = data["data"].get("balance", 0)
                await query.edit_message_text(f"💰 **Saldo Nomerin Anda:** Rp{balance:,}", parse_mode="Markdown")
            else:
                err = data.get("error", {}).get("message", "Gagal mengambil data saldo.")
                await query.edit_message_text(f"❌ {err}")
        except Exception as e:
            await query.edit_message_text(f"⚠️ Terjadi kesalahan: {str(e)}")

    elif query.data == "cara_order":
        msg = (
            "📌 **Format Perintah Order:**\n"
            "`/order <service_id> <country_id> <harga>`\n\n"
            "**Contoh:**\n"
            "`/order 1 62 3000`\n\n"
            "*(Sesuaikan service_id, country_id, dan harga sesuai daftar layanan Nomerin)*"
        )
        await query.edit_message_text(msg, parse_mode="Markdown")

# Command /order <service_id> <country_id> <harga>
async def make_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "❌ **Format Salah!**\nGunakan format: `/order <service_id> <country_id> <harga>`", 
            parse_mode="Markdown"
        )
        return

    try:
        service_id = int(context.args[0])
        country_id = int(context.args[1])
        price = int(context.args[2])

        payload = {
            "service_id": service_id,
            "country_id": country_id,
            "price": price
        }

        res = requests.post(f"{NOMERIN_BASE_URL}/orders", json=payload, headers=get_headers())
        data = res.json()

        if data.get("success"):
            order = data["data"]
            order_id = order["id"]
            number = order.get("number", "Menunggu...")
            
            msg = (
                f"✅ **Order Berhasil Dibuat!**\n\n"
                f"🆔 **ID Order:** `{order_id}`\n"
                f"📱 **Nomor:** `{number}`\n"
                f"💰 **Harga:** Rp{order['price']:,}\n\n"
                f"💡 Ketik `/cek {order_id}` untuk mengecek SMS OTP."
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            err_msg = data.get("error", {}).get("message", "Gagal memproses order.")
            await update.message.reply_text(f"❌ **Order Gagal:** {err_msg}")

    except ValueError:
        await update.message.reply_text("❌ Input ID/Harga harus berupa angka.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Terjadi error: {str(e)}")

# Command /cek <order_id>
async def check_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Masukkan ID Order! Contoh: `/cek 123456`", parse_mode="Markdown")
        return

    order_id = context.args[0]
    try:
        res = requests.get(f"{NOMERIN_BASE_URL}/orders/{order_id}", headers=get_headers())
        data = res.json()

        if data.get("success"):
            order = data["data"]
            otp = order.get("otp_code")
            status = order.get("status")

            if otp:
                await update.message.reply_text(f"📩 **Kode OTP:** `{otp}`\nStatus: {status}", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"⏳ **OTP belum masuk.**\nStatus Order: `{status}`", parse_mode="Markdown")
        else:
            err_msg = data.get("error", {}).get("message", "Order tidak ditemukan.")
            await update.message.reply_text(f"❌ {err_msg}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Terjadi error: {str(e)}")

# Command /batal <order_id>
async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Masukkan ID Order! Contoh: `/batal 123456`", parse_mode="Markdown")
        return

    order_id = context.args[0]
    try:
        res = requests.post(f"{NOMERIN_BASE_URL}/orders/{order_id}/cancel", headers=get_headers())
        data = res.json()

        if data.get("success"):
            await update.message.reply_text(f"✅ Order ID `{order_id}` berhasil dibatalkan.", parse_mode="Markdown")
        else:
            err_msg = data.get("error", {}).get("message", "Gagal membatalkan order.")
            await update.message.reply_text(f"❌ {err_msg}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Terjadi error: {str(e)}")

def main():
    if not TELEGRAM_BOT_TOKEN or not NOMERIN_API_KEY:
        print("ERROR: TELEGRAM_BOT_TOKEN atau NOMERIN_API_KEY belum diatur di Environment Variables!")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Pendaftaran Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("order", make_order))
    app.add_handler(CommandHandler("cek", check_otp))
    app.add_handler(CommandHandler("batal", cancel_order))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot berhasil aktif!")
    app.run_polling()

if __name__ == "__main__":
    main()
