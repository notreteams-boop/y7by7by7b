#!/usr/bin/env python3
"""
Telegram bot для изменения цен на сайте Šeherezāde.
Цены хранятся в GitHub Gist — нет кэша, обновляется мгновенно.
"""

import os
import json
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)

# ─── НАСТРОЙКИ — читаем из переменных окружения ───────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GITHUB_TOKEN       = os.environ["GITHUB_TOKEN"]
GIST_ID            = os.environ["GIST_ID"]  # fa7f542720a5a6391b57399314345670
OWNER_IDS          = [int(x.strip()) for x in os.environ["OWNER_IDS"].split(",")]
# ──────────────────────────────────────────────────────────────────────────────

ITEM_NAMES = {
    "s1": "Dārzeņu salāti (Овощной салат)",
    "s2": "Grieķu salāti (Греческий салат)",
    "s3": '"Šeherezāde" salāti (Салат «Шехерезада»)',
    "s4": "Cēzara salāti ar vistu (Цезарь с курицей)",
    "s5": "Ķiploku grauzdiņi (Чесночные гренки)",
    "s6": "Kartupeļi Frī 200g (Картошка Фри)",
    "s7": "Kartupeļi Daiviņas 200g (Картошка Дольки)",
    "s8": "Mājas kartupeļi (Домашняя картошка)",
    "s9": "Rīsi (Рис)",
    "s10": "Baklažānu rullīši ar fetu (Рулетики из баклажан)",
    "sh1": "Vistas šašliks (Шашлык из курицы)",
    "sh2": "Cūkgaļas šašliks (Шашлык из свинины)",
    "sh3": "Cūkgaļas ribiņas (Свиные рёбрышки)",
    "sh4": "Jēra lula kebabs (Люля-кебаб из баранины)",
    "sh5": "Jēra ribiņas (Бараньи рёбрышки)",
    "sh6": "Jēra karbonāde (Баранья корейка)",
    "sh7": "Grilēts lasis (Гриль лосось)",
    "sh8": "Cepti dārzeņi uz oglēm (Овощи на углях)",
    "p1": "Harčo (Харчо)",
    "p2": "Frikadeļu zupa (Суп с фрикадельками)",
    "p3": "Turku kebabs / курица (Турецкий кебаб)",
    "p4": "Uzbeku plovs (Узбекский плов)",
    "p5": "Dolma (Долма)",
    "p6": "Hinkaļi / gurza (Хинкали)",
    "p7": "Gutabs ar zaļumiem (Гутаб с зеленью)",
    "p8": "Gutabs ar gaļu (Гутаб с мясом)",
    "m1": "Čureks 1 gab. (Чурек шт.)",
    "m2": "Lavašs 1 gab. (Лаваш шт.)",
    "mc1": "Adžika (Аджика)",
    "mc2": "Kečups (Кетчуп)",
    "mc3": "Majonēze ar ķiplokiem (Майонез с чесноком)",
    "mc4": "Krējums (Сметана)",
    "mc5": "Narsarab (Наршараб)",
    "p_breakfast": "Karaliskās brokastis (Королевский завтрак)",
    "p_sali": "Sāļumi (Соления)",
    "p_liell": "Liellopu šašliks (Шашлык из говядины)",
    "p_azplov": "Azerbaidžāņu plovs (Азербайджанский плов)",
    "p_kufta": "Kufta bozbaš (Куфта бозбаш)",
    "d1": "Pahlava (Пахлава)",
    "d2": "Saldējums ar augļiem (Мороженое с фруктами)",
    "d3": "Pankūkas ar saldējumu (Блины с мороженым)",
    "dz1": "Tēja krūze (Чай кружка)",
    "dz2": "Tēja tējkanna (Чай чайник)",
    "dz3": "Melnā kafija (Чёрный кофе)",
    "dz4": "Balta kafija (Белый кофе)",
    "dz5": "Latte kafija (Кофе латте)",
    "dz6": "Sula (Сок)",
    "dz7": "Ūdens gāzēts/negāzēts (Вода)",
    "dz8": "Boržomi (Боржоми)",
    "dz9": "Limonādes (Лимонад)",
    "dz10": "Piena kokteilis (Молочный коктейль)",
    "dz11": "Kvass (Квас)",
    "al1": "Tērvetes alus (Тервете пиво)",
    "al2": "Užavas alus (Ужавас пиво)",
    "al3": "Valmiermuiža alus (Валмиермуйжа)",
    "vi1": "Baltvīns KARABAKH 100ml (Белое вино)",
    "vi2": "Sarkanvīns KARABAKH 100ml (Красное вино)",
    "vi3": "Granātābolu vīns 100ml (Гранатовое вино)",
}

CATEGORIES = {
    "🥗 Salāti & Piedevas": ["s1","s2","s3","s4","s5","s6","s7","s8","s9","s10"],
    "🔥 Šašliki":           ["sh1","sh2","sh3","sh4","sh5","sh6","sh7","sh8"],
    "🍲 Pamatēdieni":       ["p1","p2","p3","p4","p5","p6","p7","p8","p_breakfast","p_sali","p_liell","p_azplov","p_kufta"],
    "🍞 Maize & Mērces":    ["m1","m2","mc1","mc2","mc3","mc4","mc5"],
    "🍰 Deserti":           ["d1","d2","d3"],
    "☕ Dzērieni":          ["dz1","dz2","dz3","dz4","dz5","dz6","dz7","dz8","dz9","dz10","dz11"],
    "🍺 Alus & Vīni":       ["al1","al2","al3","vi1","vi2","vi3"],
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SELECT_CATEGORY, SELECT_ITEM, ENTER_PRICE = range(3)


# ─── GIST API ─────────────────────────────────────────────────────────────────

def get_prices_from_gist():
    """Скачать текущий prices.json из Gist."""
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    content = data["files"]["prices.json"]["content"]
    return json.loads(content)


def update_prices_in_gist(prices, changed_item, new_price):
    """Обновить prices.json в Gist."""
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content = json.dumps(prices, ensure_ascii=False, indent=2) + "\n"
    payload = {
        "files": {
            "prices.json": {"content": content}
        }
    }
    r = requests.patch(url, headers=headers, json=payload, timeout=10)
    return r.status_code == 200


# ─── HANDLERS ─────────────────────────────────────────────────────────────────

def is_owner(user_id):
    return user_id in OWNER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    await update.message.reply_text(
        "👋 Привет! Я бот для управления ценами Šeherezāde.\n\n"
        "Команды:\n"
        "  /cena — изменить цену блюда\n"
        "  /vse — показать все текущие цены\n"
        "  /otmena — отменить"
    )


async def show_all_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    try:
        prices = get_prices_from_gist()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при загрузке цен: {e}")
        return
    lines = ["📋 *Текущие цены на сайте:*\n"]
    for cat, ids in CATEGORIES.items():
        lines.append(f"\n*{cat}*")
        for item_id in ids:
            name = ITEM_NAMES.get(item_id, item_id)
            price = prices.get(item_id, "?")
            lines.append(f"  `{item_id}` {name} — *{price} €*")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def change_price_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ Нет доступа.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat:{cat}")] for cat in CATEGORIES]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Отменено.")
        return ConversationHandler.END
    cat = query.data.replace("cat:", "")
    context.user_data["category"] = cat
    items = CATEGORIES.get(cat, [])
    try:
        prices = get_prices_from_gist()
    except Exception:
        prices = {}
    keyboard = []
    for item_id in items:
        name = ITEM_NAMES.get(item_id, item_id)
        price = prices.get(item_id, "?")
        keyboard.append([InlineKeyboardButton(f"{name}  [{price} €]", callback_data=f"item:{item_id}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_cat")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await query.edit_message_text(
        f"Категория: *{cat}*\nВыберите блюдо:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return SELECT_ITEM


async def select_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Отменено.")
        return ConversationHandler.END
    if query.data == "back_cat":
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat:{cat}")] for cat in CATEGORIES]
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
        await query.edit_message_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_CATEGORY
    item_id = query.data.replace("item:", "")
    context.user_data["item_id"] = item_id
    name = ITEM_NAMES.get(item_id, item_id)
    try:
        prices = get_prices_from_gist()
        current = prices.get(item_id, "?")
    except Exception:
        current = "?"
    await query.edit_message_text(
        f"📝 *{name}*\nТекущая цена: *{current} €*\n\nВведите новую цену (например: `12.50`):",
        parse_mode="Markdown"
    )
    return ENTER_PRICE


async def enter_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".")
    try:
        new_price = float(text)
        if new_price < 0 or new_price > 9999:
            raise ValueError
        new_price_str = f"{new_price:.2f}"
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Введите число, например `12.50`:", parse_mode="Markdown")
        return ENTER_PRICE
    item_id = context.user_data.get("item_id")
    name = ITEM_NAMES.get(item_id, item_id)
    await update.message.reply_text("⏳ Обновляю цену на сайте...")
    try:
        prices = get_prices_from_gist()
        old_price = prices.get(item_id, "?")
        prices[item_id] = new_price_str
        success = update_prices_in_gist(prices, item_id, new_price_str)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка Gist API: {e}")
        return ConversationHandler.END
    if success:
        await update.message.reply_text(
            f"✅ Цена обновлена!\n\n🍽️ *{name}*\n  Было: {old_price} €\n  Стало: *{new_price_str} €*\n\n"
            f"Сайт обновится мгновенно!\nИспользуй /cena для следующего изменения.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Не удалось обновить. Проверь GITHUB_TOKEN.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("cena", change_price_start)],
        states={
            SELECT_CATEGORY: [CallbackQueryHandler(select_category)],
            SELECT_ITEM:     [CallbackQueryHandler(select_item)],
            ENTER_PRICE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_price)],
        },
        fallbacks=[
            CommandHandler("otmena", cancel),
            CallbackQueryHandler(lambda u, c: (u.callback_query.answer(), ConversationHandler.END)[1], pattern="^cancel$"),
        ],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("vse", show_all_prices))
    app.add_handler(conv)
    print("🤖 Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()
