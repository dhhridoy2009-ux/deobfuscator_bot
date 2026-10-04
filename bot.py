import os
import io
import re
import html
import base64
import hashlib
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MAX_FILE_SIZE = 5 * 1024 * 1024

def main_menu():
    keyboard = [
        ["🔓 Deobfuscator", "🔒 Obfuscator", "🛡️ HTML Security", "🖼️ Photo → URL"],
        ["📜 JS Mode", "🔍 Analyze", "ℹ️ Help", "⚙️ Settings"],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Menu খুলতে keyboard icon চাপুন"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    text = """🔒 <b>𝗛𝗧𝗠𝗟 𝗢𝗕𝗙𝗨𝗦𝗖𝗔𝗧𝗢𝗥 𝗕𝗢𝗧</b>

🛡️ <i>Protect, inspect and process your HTML / JavaScript files.</i>

✨ <b>Features:</b>
• 🔓 Deobfuscator
• 🔒 HTML / JS Obfuscator
• 🛡️ HTML Security
• 🖼️ Photo → URL
• 📜 JS Mode
• 🔍 Static Code Analysis

📄 Menu থেকে একটি feature নির্বাচন করুন এবং প্রয়োজনীয় file পাঠান।"""
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu())

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🔓 Deobfuscator":
        context.user_data["mode"] = "deob"
        await update.message.reply_text("🔓 <b>DEOBFUSCATOR</b>\n\nআপনার .html, .htm, .js অথবা .txt file পাঠান।", parse_mode="HTML")

    elif text == "🔒 Obfuscator":
        context.user_data["mode"] = "obfuscate"
        await update.message.reply_text("🔒 <b>HTML / JS OBFUSCATOR</b>\n\nআপনার HTML অথবা JavaScript file পাঠান।", parse_mode="HTML")

    elif text == "🛡️ HTML Security":
        context.user_data["mode"] = "security"
        await update.message.reply_text("🛡️ <b>HTML SECURITY</b>\n\nআপনার HTML file পাঠান।", parse_mode="HTML")

    elif text == "🖼️ Photo → URL":
        context.user_data["mode"] = "photo"
        await update.message.reply_text("🖼️ একটি photo পাঠান।", parse_mode="HTML")

    elif text == "📜 JS Mode":
        context.user_data["mode"] = "js"
        await update.message.reply_text("📜 <b>JS MODE</b>\n\nআপনার JavaScript file পাঠান।", parse_mode="HTML")

    elif text == "🔍 Analyze":
        context.user_data["mode"] = "analyze"
        await update.message.reply_text("🔍 HTML / JS file পাঠান। Bot static analysis report দেবে।", parse_mode="HTML")

    elif text == "ℹ️ Help":
        await update.message.reply_text(
            "ℹ️ <b>HELP</b>\n\n"
            "1️⃣ Menu থেকে feature নির্বাচন করুন।\n"
            "2️⃣ প্রয়োজনীয় file/photo পাঠান।\n"
            "3️⃣ Bot result তৈরি করে পাঠাবে।\n\n"
            "Maximum file size: 5 MB.",
            parse_mode="HTML"
        )

    elif text == "⚙️ Settings":
        await update.message.reply_text("⚙️ <b>SETTINGS</b>\n\nবর্তমানে কোনো additional setting নেই।", parse_mode="HTML")

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document:
        return

    mode = context.user_data.get("mode")
    if not mode:
        await update.message.reply_text("আগে Menu থেকে একটি feature নির্বাচন করুন।")
        return

    if document.file_size and document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("❌ File too large. Maximum size: 5 MB.")
        return

    filename = document.file_name or "input.txt"
    lower = filename.lower()

    if not lower.endswith((".html", ".htm", ".js", ".txt")):
        await update.message.reply_text("❌ Supported files: .html, .htm, .js, .txt")
        return

    tg_file = await document.get_file()
    data = await tg_file.download_as_bytearray()
    source = bytes(data).decode("utf-8", errors="replace")

    if mode == "deob":
        await send_file(update, deobfuscate(source), "deobfuscated_" + filename)

    elif mode == "security":
        if not lower.endswith((".html", ".htm")):
            await update.message.reply_text("❌ HTML Security requires an HTML file.")
            return
        await send_file(update, secure_html(source), "secured_" + filename)

    elif mode == "obfuscate":
        await send_file(update, safe_obfuscate(source), "protected_" + filename)

    elif mode == "js":
        await send_file(update, beautify_js(source), "formatted_" + filename)

    elif mode == "analyze":
        await update.message.reply_text(analyze_code(source), parse_mode="HTML")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "photo":
        return

    photo = update.message.photo[-1]
    tg_file = await photo.get_file()
    data = await tg_file.download_as_bytearray()

    encoded = base64.b64encode(bytes(data)).decode()
    data_url = "data:image/jpeg;base64," + encoded

    if len(data_url) > 3_500_000:
        await update.message.reply_text("❌ Image is too large for a Telegram message.")
        return

    await update.message.reply_text(
        "🖼️ <b>Photo Data URL</b>\n\n<code>" + html.escape(data_url) + "</code>",
        parse_mode="HTML"
    )

async def send_file(update, content, filename):
    bio = io.BytesIO(content.encode("utf-8"))
    bio.name = filename
    await update.message.reply_document(document=bio, caption="✅ Processing complete.")

def decode_hex(text):
    def repl(m):
        try:
            return chr(int(m.group(1), 16))
        except Exception:
            return m.group(0)
    return re.sub(r"\\x([0-9a-fA-F]{2})", repl, text)

def decode_unicode(text):
    def repl(m):
        try:
            return chr(int(m.group(1), 16))
        except Exception:
            return m.group(0)
    return re.sub(r"\\u([0-9a-fA-F]{4})", repl, text)

def deobfuscate(source):
    result = source
    for _ in range(3):
        old = result
        result = decode_hex(result)
        result = decode_unicode(result)
        result = html.unescape(result)
        if result == old:
            break
    result = re.sub(r"\n{3,}", "\n\n", result)
    return beautify_html(result) if re.search(r"<html|<body|<script|<div", result, re.I) else beautify_js(result)

def beautify_html(source):
    source = re.sub(r">\s+<", "><", source)
    tokens = re.split(r"(<[^>]+>)", source)
    void = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
    indent = 0
    output = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token.startswith("</"):
            indent = max(0, indent - 1)
        output.append("  " * indent + token)
        opening = re.match(r"<([a-zA-Z][\w:-]*)[^>]*>$", token)
        if opening:
            tag = opening.group(1).lower()
            if not token.startswith("</") and not token.startswith("<!") and not token.endswith("/>") and tag not in void:
                indent += 1
    return "\n".join(output)

def beautify_js(source):
    result = re.sub(r"\s*{\s*", " {\n", source)
    result = re.sub(r"\s*}\s*", "\n}\n", result)
    result = re.sub(r";\s*", ";\n", result)
    lines = []
    indent = 0
    for line in result.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("}"):
            indent = max(0, indent - 1)
        lines.append("  " * indent + line)
        if line.endswith("{"):
            indent += 1
    return "\n".join(lines)

def secure_html(source):
    security_meta = """<!-- HTML SECURITY HARDENING -->
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="Referrer-Policy" content="strict-origin-when-cross-origin">
<meta http-equiv="Permissions-Policy" content="camera=(), microphone=(), geolocation=()">
"""
    if re.search(r"<head\b", source, re.I):
        result = re.sub(r"(<head[^>]*>)", r"\1\n" + security_meta, source, count=1, flags=re.I)
    else:
        result = security_meta + "\n" + source

    result = re.sub(
        r'\s+(href|src)\s*=\s*(["\'])\s*javascript:[^"\']*\2',
        "",
        result,
        flags=re.I
    )
    return beautify_html(result)

def safe_obfuscate(source):
    banner = "/* Protected HTML / JavaScript - static protection build */\n\n"

    def encode_string(m):
        quote, value = m.group(1), m.group(2)
        if len(value) < 5:
            return m.group(0)
        encoded = "".join("\\x%02x" % ord(c) for c in value)
        return quote + encoded + quote

    return banner + re.sub(r'(["\'])([^"\']{5,})\1', encode_string, source)

def analyze_code(source):
    patterns = {
        "eval()": r"\beval\s*\(",
        "Function()": r"\bFunction\s*\(",
        "Base64 / atob": r"\batob\s*\(|\bbase64\b",
        "Hex escapes": r"\\x[0-9a-fA-F]{2}",
        "Unicode escapes": r"\\u[0-9a-fA-F]{4}",
        "Debugger": r"\bdebugger\b",
        "String arrays": r"\b(?:const|let|var)\s+\w+\s*=\s*\["
    }
    report = ["🔍 <b>STATIC CODE ANALYSIS</b>", ""]
    for name, pattern in patterns.items():
        count = len(re.findall(pattern, source, flags=re.I))
        if count:
            report.append(f"• {html.escape(name)}: <b>{count}</b>")
    if len(report) == 2:
        report.append("✅ No common patterns detected.")
    return "\n".join(report)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Menu থেকে feature নির্বাচন করে HTML/JS file পাঠান।")

async def error_handler(update, context):
    print("BOT ERROR:", context.error)

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, file_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_error_handler(error_handler)

    print("HTML Security Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
