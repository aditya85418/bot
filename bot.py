from __future__ import annotations

import re
import json
from dataclasses import dataclass
from typing import Dict, Optional
from keep_alive import keep_alive

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# CONFIG
# =========================
BOT_TOKEN = "8625545005:AAHDRRzF7Qmf3RRV3x4gkbpLPhN1ZjeqXYU"
OWNER_ID = 8011957004
REQUIRED_CHANNEL = "@PlayStoreDealsZone"

CONFIG_FILE = "config.json"
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

plan_status = {"bt1": True, "bt2": True, "bt3": True, "bt4": True}
pending_approvals: Dict[int, int] = {}

plan_names = {
    "bt1": "₹100 → ₹80",
    "bt2": "₹500 → ₹320",
    "bt3": "₹1000 → ₹550",
    "bt4": "₹1500 → ₹750",
}

# =========================
# CONFIG LOAD
# =========================
def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}

    data.setdefault("admins", [OWNER_ID])
    data.setdefault("qr_image", None)

    return data


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)


config_data = load_config()


def get_admins():
    return config_data.get("admins", [OWNER_ID])


def is_admin(uid):
    return uid in get_admins()


def is_owner(uid):
    return uid == OWNER_ID

# =========================
# USER STATE
# =========================
@dataclass
class UserFlow:
    selected_plan: Optional[str] = None
    email: Optional[str] = None
    waiting_for_email: bool = False
    waiting_for_proof: bool = False
    proof_file_id: Optional[str] = None


user_flow: Dict[int, UserFlow] = {}


def get_flow(uid):
    if uid not in user_flow:
        user_flow[uid] = UserFlow()
    return user_flow[uid]

# =========================
# UI
# =========================
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@','')}")],
        [InlineKeyboardButton("I Joined ✅", callback_data="verify")]
    ])


def plan_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("₹100 → ₹80", callback_data="plan_bt1")],
        [InlineKeyboardButton("₹500 → ₹320", callback_data="plan_bt2")],
        [InlineKeyboardButton("₹1000 → ₹550", callback_data="plan_bt3")],
        [InlineKeyboardButton("₹1500 → ₹750", callback_data="plan_bt4")],
    ])

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Buy Google Play Redeem Codes – Fast & Secure 🔥\n\n"
        "👉 Join our channel to continue",
        reply_markup=main_kb()
    )

# =========================
# VERIFY
# =========================
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, q.from_user.id)
        if member.status in ["member", "administrator", "creator"]:
            await q.message.reply_text(
                "🔥 Best Deals 🔥\n\n"
                "₹100 → ₹80\n₹500 → ₹320\n₹1000 → ₹550\n₹1500 → ₹750\n\n👇 Choose:",
                reply_markup=plan_kb()
            )
        else:
            raise Exception
    except:
        await q.message.reply_text("❌ Join channel first", reply_markup=main_kb())

# =========================
# PLAN
# =========================
async def select_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plan = q.data.replace("plan_", "")

    if not plan_status.get(plan, True):
        await q.message.reply_text("❌ Out of stock")
        return

    flow = get_flow(q.from_user.id)
    flow.selected_plan = plan
    flow.waiting_for_email = True

    await q.message.reply_text(f"✅ {plan_names.get(plan)}\n📧 Enter email:")

# =========================
# TEXT
# =========================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # ADMIN CODE
    if is_admin(uid) and uid in pending_approvals:
        user_id = pending_approvals.pop(uid)
        code = update.message.text.strip()

        await context.bot.send_message(
            user_id,
            f"✅ Approved\n\n🔑 Code:\n<pre>{code}</pre>",
            parse_mode=ParseMode.HTML
        )

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("Yes", callback_data=f"post_yes_{user_id}"),
            InlineKeyboardButton("No", callback_data=f"post_no_{user_id}")
        ]])

        await update.message.reply_text("Post proof to channel?", reply_markup=kb)
        return

    flow = get_flow(uid)

    if flow.waiting_for_email:
        email = update.message.text

        if not EMAIL_RE.match(email):
            await update.message.reply_text("❌ Invalid email")
            return

        flow.email = email
        flow.waiting_for_proof = True
        flow.waiting_for_email = False

        caption = "💸 Scan QR & Pay\n📸 Send screenshot after payment"

        if config_data.get("qr_image"):
            await update.message.reply_photo(config_data["qr_image"], caption=caption)
        else:
            await update.message.reply_text(caption)

# =========================
# PHOTO HANDLER
# =========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # 👉 QR SET MODE
    if context.user_data.get("set_qr") and is_admin(uid):
        file_id = update.message.photo[-1].file_id
        config_data["qr_image"] = file_id
        save_config(config_data)

        context.user_data["set_qr"] = False
        await update.message.reply_text("QR saved ✅")
        return

    # 👉 NORMAL USER PROOF
    flow = get_flow(uid)

    if not flow.waiting_for_proof:
        return

    file_id = update.message.photo[-1].file_id
    flow.proof_file_id = file_id

    text = f"📥 Order\n👤 {uid}\n📦 {plan_names.get(flow.selected_plan)}\n📧 {flow.email}"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Approve", callback_data=f"approve_{uid}"),
        InlineKeyboardButton("Reject", callback_data=f"reject_{uid}")
    ]])

    for admin in get_admins():
        await context.bot.send_message(admin, text, reply_markup=kb)
        await context.bot.send_photo(admin, file_id)

    await update.message.reply_text("⏳ Waiting for approval \nFor any problem, contact to our admin on whatsapp \nPh no: +916205794548")

# =========================
# ADMIN ACTION
# =========================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    action, uid = q.data.split("_")
    uid = int(uid)

    if action == "approve":
        pending_approvals[q.from_user.id] = uid
        await q.message.reply_text("Send code")
    else:
        await context.bot.send_message(uid, "Rejected ❌")
        await q.message.edit_text("Rejected")

# =========================
# POST
# =========================
async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    _, action, uid = q.data.split("_")
    uid = int(uid)

    if action == "yes":
        flow = get_flow(uid)
        await context.bot.send_photo(REQUIRED_CHANNEL, flow.proof_file_id, caption="🔥 New Code Sold")
        await q.message.edit_text("Posted ✅")
    else:
        await q.message.edit_text("Skipped ❌")

# =========================
# ADMIN COMMANDS
# =========================
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    new_admin = int(context.args[0])
    admins = set(get_admins())
    admins.add(new_admin)
    config_data["admins"] = list(admins)
    save_config(config_data)
    await update.message.reply_text("Admin added ✅")


async def delete_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    rem = int(context.args[0])
    admins = set(get_admins())
    admins.discard(rem)
    config_data["admins"] = list(admins)
    save_config(config_data)
    await update.message.reply_text("Admin removed ❌")


async def off_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan = context.args[0]
    if plan.isdigit():
        plan = f"bt{plan}"
    plan_status[plan] = False
    await update.message.reply_text(f"{plan} OFF")


async def on_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan = context.args[0]
    if plan.isdigit():
        plan = f"bt{plan}"
    plan_status[plan] = True
    await update.message.reply_text(f"{plan} ON")

# =========================
# SET QR
# =========================
async def set_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["set_qr"] = True
    await update.message.reply_text("Send QR image")

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("deleteadmin", delete_admin))
    app.add_handler(CommandHandler("off", off_plan))
    app.add_handler(CommandHandler("on", on_plan))
    app.add_handler(CommandHandler("setqr", set_qr))

    app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
    app.add_handler(CallbackQueryHandler(select_plan, pattern="plan_"))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="approve_|reject_"))
    app.add_handler(CallbackQueryHandler(handle_post, pattern="^post_"))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text), group=0)

    # Standard polling handles asyncio internally and won't conflict with Flask thread
    app.run_polling()

if __name__ == "__main__":
    keep_alive()  # Starts the Flask server in thread
    main()        # Starts Telegram bot
