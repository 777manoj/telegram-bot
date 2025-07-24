import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# 🔧 Config
BOT_TOKEN = "8086903911:AAET2LySb45-Y8AzeV4RtPuMq3iZQeyQuio"
API_URL = "https://tntsmm.in/api/v2"
API_KEY = "35f4e886bfa3cd37ea77f9500696565c"
UPI_ID = "9382777247@ybl"
PAYMENT_CHANNEL = "@smmpanelpament"
SUPPORT_CHANNEL = "https://t.me/suppet123"
ADMIN_ID = 123456789  # <-- Replace with your Telegram ID

user_balances = {}
pending_transactions = {}  # user_id: txn_id

logging.basicConfig(level=logging.INFO)

# ✅ Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Welcome to the SMM Bot!\n\n💳 To add funds, send to *{UPI_ID}*.\n"
        "Then reply with: `/addfunds TXN_ID`\nAnd upload payment screenshot.\n\n"
        f"📢 Support: {SUPPORT_CHANNEL}",
        parse_mode="Markdown"
    )

# ✅ Add funds with TXN ID
async def addfunds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("❗ Usage: /addfunds TXN_ID")
        return

    txn_id = context.args[0]
    user_id = update.message.from_user.id
    pending_transactions[user_id] = txn_id

    await update.message.reply_text("✅ Now please send your payment *screenshot*.", parse_mode="Markdown")

# ✅ Handle screenshot
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    txn_id = pending_transactions.get(user_id)

    if not txn_id:
        await update.message.reply_text("❗ Please first send: /addfunds TXN_ID")
        return

    photo_file = update.message.photo[-1].file_id
    caption = f"🧾 *New Payment Received*\n\n👤 User: @{user.username or user.first_name}\n🆔 ID: `{user_id}`\n💳 TXN: `{txn_id}`"
    buttons = [
        [InlineKeyboardButton("✅ Approve ₹", callback_data=f"approve|{user_id}|{txn_id}")],
        [InlineKeyboardButton("❌ Deny", callback_data=f"deny|{user_id}|{txn_id}")]
    ]

    await context.bot.send_photo(
        chat_id=PAYMENT_CHANNEL,
        photo=photo_file,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    await update.message.reply_text("✅ Payment screenshot sent to admin.")
    del pending_transactions[user_id]

# ✅ Admin callback to approve/deny
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('|')
    action, user_id, txn_id = data[0], int(data[1]), data[2]

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_caption(caption="❌ Unauthorized action.")
        return

    if action == "approve":
        amount = 50  # Default ₹ amount. Later you can use custom UIs.
        user_balances[user_id] = user_balances.get(user_id, 0) + amount
        await context.bot.send_message(chat_id=user_id, text=f"✅ ₹{amount} added to your balance.")
        await query.edit_message_caption(caption=f"✅ Approved ₹{amount} to user `{user_id}`\nTXN: `{txn_id}`", parse_mode="Markdown")
    elif action == "deny":
        await context.bot.send_message(chat_id=user_id, text=f"❌ Your payment was not approved.\nTXN: `{txn_id}`", parse_mode="Markdown")
        await query.edit_message_caption(caption=f"❌ Payment denied.\nTXN: `{txn_id}`")

# ✅ Check balance
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    balance = user_balances.get(user_id, 0)
    await update.message.reply_text(f"💰 Your current balance: ₹{balance}")

# ✅ Place order
async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("❗ Usage: /order SERVICE_ID LINK QUANTITY")
        return

    user_id = update.message.from_user.id
    service_id, link, quantity = args[0], args[1], int(args[2])

    # Price checking (optional, assume ₹1 per quantity)
    cost = quantity * 1
    balance = user_balances.get(user_id, 0)

    if balance < cost:
        await update.message.reply_text(f"❌ Insufficient balance.\nCost: ₹{cost} | Your Balance: ₹{balance}")
        return

    # Send order to SMM API
    payload = {
        'key': API_KEY,
        'action': 'add',
        'service': service_id,
        'link': link,
        'quantity': quantity
    }

    response = requests.post(API_URL, data=payload).json()

    if "order" in response:
        user_balances[user_id] -= cost
        await update.message.reply_text(f"✅ Order placed!\n🆔 Order ID: {response['order']}\n💰 Deducted ₹{cost}")
    else:
        await update.message.reply_text("❌ Failed to place order.\n" + str(response))

# ✅ Get services
async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = {
        'key': API_KEY,
        'action': 'services'
    }

    response = requests.post(API_URL, data=payload).json()

    msg = "📋 *Available Services:*\n"
    for service in response[:10]:  # limit to 10 for Telegram size
        msg += f"\n🆔 {service['service']} - {service['name']}\n💸 ₹{service['rate']} per 1000\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

# ✅ Main
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("services", services))
    app.add_handler(CommandHandler("addfunds", addfunds))
    app.add_handler(CommandHandler("order", order))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()