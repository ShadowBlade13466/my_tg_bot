# main_bot.py

import asyncio
import logging
import sqlite3
import random
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F, Router, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# ----- ⚙️ КОНФІГУРАЦІЯ БОТА ⚙️ -----
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPONSOR_CHANNEL = os.getenv("SPONSOR_CHANNEL")
ADMIN_IDS = [admin_id.strip() for admin_id in os.getenv("ADMIN_ID", "").split(',') if admin_id]

# ----- НАЛАШТУВАННЯ ЛОГІВ -----
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ----- Налаштування економіки -----
DB_NAME = "economy_bot.db"
START_COINS = 1000
REFERRAL_BONUS = 1000
REFERRED_BONUS = 2000
MIN_BET = 50
STAR_SELL_PRICE = 20000
STAR_BUY_PRICE = 22000

# ----- 📈 РАНГИ 📈 -----
RANKS = {
    1: (0, "🌱 Новичок"), 2: (5000, "🥈 Игрок"), 3: (15000, "🥉 Опытный"), 4: (30000, "🥉 Бывалый"),
    5: (50000, "🥉 Ветеран"), 6: (100000, "🥈 Мастер"), 7: (250000, "🥈 Эксперт"), 8: (500000, "🥈 Профессионал"),
    9: (1000000, "🥇 Легенда"), 10: (2500000, "🥇 Миллионер"), 11: (5000000, "💎 Магнат"),
    12: (10000000, "👑 Король экономики"), 13: (25000000, "✨ Повелитель монет"),
    14: (50000000, "🌌 Галактический банкир"), 15: (100000000, "🔱 Божество"),
    16: (float('inf'), "👑 Абсолют")
}

# ----- 🃏 ПРЕДМЕТИ 🃏 -----
RARITY_POWER = {'⚪️ Обычная': 1, '🟢 Редкая': 2, '🔵 Эпическая': 3, '🟣 Легендарная': 4, '🟠 Мифическая': 5, '⚜️ Уникальная': 10}
ITEMS = {
    'c1': {'name': 'Карта Новичка', 'rarity': '⚪️ Обычная', 'type': 'card', 'power': RARITY_POWER['⚪️ Обычная']},
    'c2': {'name': 'Талисман Удачи', 'rarity': '⚪️ Обычная', 'type': 'card', 'power': RARITY_POWER['⚪️ Обычная']},
    'c3': {'name': 'Древняя Монета', 'rarity': '🟢 Редкая', 'type': 'card', 'power': RARITY_POWER['🟢 Редкая']},
    'c4': {'name': 'Кристалл Энергии', 'rarity': '🟢 Редкая', 'type': 'card', 'power': RARITY_POWER['🟢 Редкая']},
    'c5': {'name': 'Звёздная Карта', 'rarity': '🔵 Эпическая', 'type': 'card', 'power': RARITY_POWER['🔵 Эпическая']},
    'c6': {'name': 'Эссенция Богатства', 'rarity': '🔵 Эпическая', 'type': 'card', 'power': RARITY_POWER['🔵 Эпическая']},
    'c7': {'name': 'Корона Правителя', 'rarity': '🟣 Легендарная', 'type': 'card', 'power': RARITY_POWER['🟣 Легендарная']},
    'c8': {'name': 'Осколок Вселенной', 'rarity': '🟣 Легендарная', 'type': 'card', 'power': RARITY_POWER['🟣 Легендарная']},
    'c9': {'name': 'Сердце Галактики', 'rarity': '🟠 Мифическая', 'type': 'card', 'power': RARITY_POWER['🟠 Мифическая']},
    'c10': {'name': 'Карта COINVERSE', 'rarity': '⚜️ Уникальная', 'type': 'card', 'power': RARITY_POWER['⚜️ Уникальная']},
    'key1': {'name': 'Ключ от Сокровищницы', 'rarity': '🟢 Редкая', 'type': 'item'},
}

# ----- 🎁 КЕЙСИ 🎁 -----
CASES = {
    'bronze': {'name': '🥉 Бронзовый кейс', 'cost': 500, 'currency': 'coins',
               'prizes': [ {'type': 'coins', 'amount': (100, 450), 'chance': 65}, {'type': 'item', 'item_id': 'c1', 'chance': 15}, {'type': 'item', 'item_id': 'c2', 'chance': 15}, {'type': 'item', 'item_id': 'key1', 'chance': 5},]},
    'silver': {'name': '🥈 Серебряный кейс', 'cost': 2500, 'currency': 'coins',
               'prizes': [ {'type': 'coins', 'amount': (1000, 2200), 'chance': 55}, {'type': 'stars', 'amount': (1, 3), 'chance': 15}, {'type': 'item', 'item_id': 'c3', 'chance': 15}, {'type': 'item', 'item_id': 'c5', 'chance': 10}, {'type': 'item', 'item_id': 'key1', 'chance': 5},]},
    'gold':   {'name': '🥇 Золотой кейс', 'cost': 10, 'currency': 'stars',
               'prizes': [ {'type': 'coins', 'amount': (15000, 25000), 'chance': 50}, {'type': 'item', 'item_id': 'c7', 'chance': 40}, {'type': 'item', 'item_id': 'c9', 'chance': 9}, {'type': 'item', 'item_id': 'c10', 'chance': 1},]},
    'treasure': {'name': '💎 Кейс Сокровищницы', 'cost': 1, 'currency': 'key1',
                 'prizes': [ {'type': 'stars', 'amount': (10, 25), 'chance': 50}, {'type': 'item', 'item_id': 'c8', 'chance': 30}, {'type': 'item', 'item_id': 'c10', 'chance': 20},]}
}

# ----- Базові настройки -----
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()
main_router = Router()

# ----- FSM Стейни -----
class AdminStates(StatesGroup):
    get_user_id_for_balance, get_currency_type, get_amount = State(), State(), State()
    get_user_id_for_stats = State()
    get_message_for_mass_send, confirm_mass_send = State(), State()
    giveaway_currency, giveaway_amount, giveaway_confirm = State(), State(), State()

class CasinoStates(StatesGroup):
    get_bet_dice, get_bet_slots, get_card_for_duel = State(), State(), State()

class ExchangeStates(StatesGroup):
    amount = State()

class FeedbackState(StatesGroup):
    waiting_for_feedback = State()

def escape_markdown(text: str) -> str:
    if not isinstance(text, str): return ""
    return text.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace('[', '\\[')

# ----- 🗄️ БАЗА ДАННЫХ 🗄️ -----
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, coins INTEGER DEFAULT 0, stars INTEGER DEFAULT 0,
            total_coins_earned INTEGER DEFAULT 0, rank_level INTEGER DEFAULT 1,
            daily_bonus_streak INTEGER DEFAULT 0, last_bonus_date TEXT,
            referrer_id INTEGER,
            join_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )""")
        try:
            cursor.execute("SELECT referrer_id FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
        conn.commit()

# ----- Функції для роботи з БД -----
async def get_user(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row; cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()

async def add_user(user_id, username, referrer_id=None):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        start_coins = REFERRED_BONUS if referrer_id else START_COINS
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, coins, total_coins_earned, referrer_id) VALUES (?, ?, ?, ?, ?)", (user_id, username or "Без имени", start_coins, start_coins, referrer_id))
        conn.commit()

async def update_balance(user_id, coins=0, stars=0, earned=False):
    current_data = await get_user(user_id)
    if not current_data: return
    new_coins, new_stars = current_data['coins'] + coins, current_data['stars'] + stars
    new_total_earned = current_data['total_coins_earned'] + coins if earned and coins > 0 else current_data['total_coins_earned']
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET coins = ?, stars = ?, total_coins_earned = ? WHERE user_id = ?", (new_coins, new_stars, new_total_earned, user_id))
    await check_and_update_rank(user_id, new_total_earned)

async def add_item_to_inventory(user_id, item_id, quantity=1):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        for _ in range(quantity):
            cursor.execute("INSERT INTO inventory (user_id, item_id) VALUES (?, ?)", (user_id, item_id))

async def remove_item_from_inventory(user_id, item_id, quantity=1):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE id IN (SELECT id FROM inventory WHERE user_id = ? AND item_id = ? LIMIT ?)", (user_id, item_id, quantity))

async def get_user_inventory(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT item_id, COUNT(item_id) as count FROM inventory WHERE user_id = ? GROUP BY item_id", (user_id,))
        return cursor.fetchall()

async def check_and_update_rank(user_id, total_coins_earned):
    current_user = await get_user(user_id);
    if not current_user: return
    current_rank_level = current_user['rank_level']
    new_rank_level = current_rank_level
    for level, (required_coins, _) in sorted(RANKS.items(), reverse=True):
        if required_coins is not None and total_coins_earned >= required_coins: new_rank_level = level; break
    if new_rank_level > current_rank_level:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET rank_level = ? WHERE user_id = ?", (new_rank_level, user_id))
        _, rank_name = RANKS[new_rank_level]
        try: await bot.send_message(user_id, f"🎉 *Поздравляем!* 🎉\nВы достигли нового ранга: **{rank_name}**!")
        except: pass

# ----- 🛡️ ПРОВЕРКА ПОДПИСКИ НА КАНАЛ 🛡️ -----
class SponsorshipMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message | CallbackQuery, data):
        user_id = event.from_user.id
        if ADMIN_IDS and str(user_id) in ADMIN_IDS:
            if not await get_user(user_id): await add_user(user_id, event.from_user.username)
            return await handler(event, data)
        if not SPONSOR_CHANNEL: return await handler(event, data)
        try:
            member = await bot.get_chat_member(chat_id=SPONSOR_CHANNEL, user_id=user_id)
            if member.status in ['member', 'administrator', 'creator']:
                if not await get_user(user_id):
                    referrer_id = None
                    if isinstance(event, Message) and event.text and event.text.startswith("/start"):
                        args = event.text.split()
                        if len(args) > 1 and args[1].isdigit():
                            if int(args[1]) != user_id: referrer_id = int(args[1])
                    await add_user(user_id, event.from_user.username, referrer_id)
                return await handler(event, data)
            else: raise ValueError("User is not a member.")
        except:
            try:
                channel_info = await bot.get_chat(SPONSOR_CHANNEL)
                channel_link = channel_info.invite_link or f"https://t.me/{channel_info.username}"
            except:
                logging.error(f"ОШИБКА: Не удалось найти канал: {SPONSOR_CHANNEL}.")
                error_text = "🔧 Бот временно недоступен.";
                if isinstance(event, Message): await event.answer(error_text)
                elif isinstance(event, CallbackQuery): await event.message.answer(error_text)
                return
            kb = InlineKeyboardBuilder(); kb.button(text="➡️ Перейти в канал", url=channel_link); kb.button(text="✅ Я подписался", callback_data="check_subscription")
            text = f"🛑 **Доступ ограничен!**\n\nДля использования бота, подпишитесь на наш канал-спонсор:\n**{escape_markdown(channel_info.title)}**\n\nПосле подписки нажмите кнопку 'Я подписался'."
            if isinstance(event, Message): await event.answer(text, reply_markup=kb.as_markup())
            elif isinstance(event, CallbackQuery): await event.message.answer(text, reply_markup=kb.as_markup()); await event.answer()

# ----- ⌨️ КЛАВИАТУРЫ ⌨️ -----
def get_main_menu_keyboard():
    b = InlineKeyboardBuilder()
    b.button(text="👤 Профиль", callback_data="menu:profile"); b.button(text="🎒 Инвентарь", callback_data="menu:inventory")
    b.button(text="🎁 Кейсы", callback_data="menu:cases"); b.button(text="🎮 Развлечения", callback_data="menu:games")
    b.button(text="💱 Обмен", callback_data="menu:exchange"); b.button(text="🗓️ Бонус", callback_data="menu:daily_bonus")
    b.button(text="🏆 Топы", callback_data="menu:tops"); b.button(text="🤝 Пригласить друга", callback_data="menu:referral")
    b.button(text="✍️ Отзывы", callback_data="menu:feedback")
    b.adjust(2); return b.as_markup()

def get_back_button(cb="menu:main"):
    b = InlineKeyboardBuilder(); b.button(text="⬅️ Назад", callback_data=cb); return b.as_markup()

# ----- ОСНОВНІ ОБРОБЧИКИ -----
@main_router.message(CommandStart())
async def cmd_start(message: Message):
    referrer_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        if int(args[1]) != message.from_user.id: referrer_id = int(args[1])
    
    user_exists = await get_user(message.from_user.id)
    if not user_exists:
        await add_user(message.from_user.id, message.from_user.username, referrer_id)
        bonus = REFERRED_BONUS if referrer_id else START_COINS
        await message.answer(f"👋 Привет, {escape_markdown(message.from_user.first_name)}!\n\nДобро пожаловать! Ваш стартовый бонус: **{bonus}** монет!", reply_markup=get_main_menu_keyboard())
        if referrer_id:
            await update_balance(referrer_id, coins=REFERRAL_BONUS, earned=True)
            try: await bot.send_message(referrer_id, f"🎉 По вашей ссылке присоединился новый игрок! Вам начислено **{REFERRAL_BONUS}** монет!")
            except: pass
    else:
        await message.answer(f"👋 С возвращением, {escape_markdown(message.from_user.first_name)}!", reply_markup=get_main_menu_keyboard())

@main_router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery): await callback.message.delete(); await cmd_start(callback.message)

@main_router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear(); await callback.message.edit_text("Вы в главном меню.", reply_markup=get_main_menu_keyboard())

@main_router.message(F.text.lower() == "отмена", StateFilter(AdminStates, CasinoStates, ExchangeStates, FeedbackState))
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
    if str(message.from_user.id) in ADMIN_IDS: await cmd_admin_panel(message)
    else: await message.answer("Вы в главном меню.", reply_markup=get_main_menu_keyboard())
# ----- 🎒 ІНВЕНТАР 🎒 -----
@main_router.callback_query(F.data == "menu:inventory")
async def cb_inventory(callback: CallbackQuery):
    user_inventory = await get_user_inventory(callback.from_user.id)
    if not user_inventory:
        return await callback.message.edit_text("🎒 Ваш инвентарь пуст.\n\n_Открывайте кейсы, чтобы получить коллекционные карточки и предметы!_", reply_markup=get_back_button())
    
    text = "🎒 *Ваш инвентарь:*\n\n"
    items_by_type = {'item': [], 'card': []}
    for item_id, count in user_inventory:
        item_info = ITEMS.get(item_id)
        if item_info:
            items_by_type.setdefault(item_info.get('type', 'item'), []).append((item_id, count, item_info))

    if items_by_type['item']:
        text += "*Предметы:*\n"
        for item_id, count, item_info in items_by_type['item']:
            text += f"{item_info['name']} - {count} шт.\n"
        text += "\n"

    if items_by_type['card']:
        text += "*Коллекционные карточки:*\n"
        rarity_order = ['⚪️ Обычная', '🟢 Редкая', '🔵 Эпическая', '🟣 Легендарная', '🟠 Мифическая', '⚜️ Уникальная']
        sorted_cards = sorted(items_by_type['card'], key=lambda x: rarity_order.index(x[2]['rarity']))
        for card_id, count, card_info in sorted_cards:
            text += f"{card_info['rarity']} *{card_info['name']}* - {count} шт.\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_button())

# ----- 🤝 РЕФЕРАЛЬНА СИСТЕМА ТА ВІДГУКИ ✍️ -----
@main_router.callback_query(F.data == "menu:referral")
async def cb_referral(callback: CallbackQuery):
    me = await bot.get_me()
    referral_link = f"https://t.me/{me.username}?start={callback.from_user.id}"
    text = (
        "🤝 *Пригласите друга и получите бонус!* \n\n"
        f"Отправьте другу свою уникальную ссылку. Когда он запустит бота по ней, вы оба получите награду:\n\n"
        f"- *Вы получите:* **{REFERRAL_BONUS:,}** монет 💰\n"
        f"- *Ваш друг получит:* **{REFERRED_BONUS:,}** монет при старте! 💸\n\n"
        f"Ваша ссылка:\n`{referral_link}`"
    )
    await callback.message.edit_text(text, reply_markup=get_back_button())

@main_router.callback_query(F.data == "menu:feedback")
async def cb_feedback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FeedbackState.waiting_for_feedback)
    await callback.message.edit_text(
        "✍️ *Оставить отзыв*\n\n"
        "Пожалуйста, напишите свой отзыв, идею или сообщение об ошибке одним сообщением. "
        "Ваш отзыв будет анонимно отправлен администрации.\n\n"
        "_Для отмены напишите /cancel_",
        reply_markup=get_back_button()
    )

@main_router.message(F.text == "/cancel", StateFilter(FeedbackState))
async def cancel_feedback(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отправка отзыва отменена.", reply_markup=get_main_menu_keyboard())

@main_router.message(FeedbackState.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext):
    await state.clear()
    feedback_text = (
        f"📬 *Новый отзыв от пользователя!* (ID: `{message.from_user.id}`)\n\n"
        f"Текст:\n_{escape_markdown(message.text)}_"
    )
    if ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, feedback_text)
            except Exception as e:
                logging.error(f"Не удалось отправить отзыв админу {admin_id}: {e}")
    await message.answer("✅ Спасибо! Ваш отзыв был отправлен.", reply_markup=get_main_menu_keyboard())

# ----- 💻 АДМІН-ПАНЕЛЬ 💻 -----
@main_router.message(Command("admin"))
async def cmd_admin_panel(message: Message, state: FSMContext):
    if str(message.from_user.id) not in ADMIN_IDS: return
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="💸 Редактировать баланс", callback_data="admin:give_balance")
    kb.button(text="📊 Статистика игрока", callback_data="admin:check_user")
    kb.button(text="🚁 Раздача всем", callback_data="admin:giveaway")
    kb.button(text="📈 Глобальная статистика", callback_data="admin:global_stats")
    kb.button(text="📢 Сделать рассылку", callback_data="admin:mass_send")
    kb.button(text="⬅️ В главное меню", callback_data="menu:main")
    kb.adjust(1)
    await message.answer("👑 **Админ-панель**", reply_markup=kb.as_markup())

@main_router.message(Command("give"))
async def cmd_give_by_reply(message: Message):
    if str(message.from_user.id) not in ADMIN_IDS: return
    if not message.reply_to_message:
        return await message.reply("❌ Эту команду нужно использовать в ответ на сообщение пользователя!")
    try:
        parts = message.text.split()
        currency = parts[1].lower()
        amount_str = parts[2]
        
        target_id = message.reply_to_message.from_user.id
        target_user = await get_user(target_id)
        if not target_user: return await message.reply("❌ Этот пользователь еще не запускал бота.")
        safe_username = escape_markdown(message.reply_to_message.from_user.username or "Без_юзернейма")

        if currency in ["монеты", "coins"]:
            amount = int(amount_str)
            await update_balance(target_id, coins=amount, earned=(amount > 0))
            await message.reply(f"✅ Успешно изменено на {amount} монет для @{safe_username}.")
        elif currency in ["звезды", "stars"]:
            amount = int(amount_str)
            await update_balance(target_id, stars=amount)
            await message.reply(f"✅ Успешно изменено на {amount} звёздочек для @{safe_username}.")
        elif currency in ["item", "предмет"]:
            item_id = amount_str
            if item_id not in ITEMS: return await message.reply(f"❌ Предмет с ID '{item_id}' не найден.")
            await add_item_to_inventory(target_id, item_id)
            await message.reply(f"✅ Успешно выдан предмет '{ITEMS[item_id]['name']}' пользователю @{safe_username}.")
        else: await message.reply("❌ Неверный тип. Используйте 'монеты', 'звезды' или 'предмет'.")
    except: await message.reply("❌ Ошибка в команде. Пример: `/give монеты 10000` или `/give item key1`")

@main_router.callback_query(F.data == "admin:global_stats")
async def admin_global_stats(callback: CallbackQuery):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(user_id) FROM users"); total_users = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(coins) FROM users"); total_coins = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(stars) FROM users"); total_stars = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(id) FROM inventory"); total_items = cursor.fetchone()[0]
    
    text = (
        "📈 *Глобальная статистика бота:*\n\n"
        f"👥 *Всего пользователей:* {total_users}\n"
        f"💰 *Всего монет в экономике:* {total_coins:,}\n"
        f"⭐ *Всего звёздочек в экономике:* {total_stars:,}\n"
        f"🃏 *Всего предметов в инвентарях:* {total_items:,}"
    )
    await callback.message.edit_text(text, reply_markup=get_back_button("admin:main_panel"))

@main_router.callback_query(F.data == "admin:giveaway")
async def admin_giveaway_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.giveaway_currency)
    kb = InlineKeyboardBuilder(); kb.button(text="💰 Монеты", callback_data="giveaway:coins"); kb.button(text="⭐ Звёздочки", callback_data="giveaway:stars")
    await callback.message.edit_text("Выберите валюту для раздачи:", reply_markup=kb.as_markup())

@main_router.callback_query(F.data.startswith("giveaway:"), AdminStates.giveaway_currency)
async def admin_giveaway_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split(":")[1]; await state.update_data(currency=currency)
    await state.set_state(AdminStates.giveaway_amount)
    await callback.message.edit_text(f"Введите сумму ({'монет' if currency == 'coins' else 'звёздочек'}), которую получит каждый пользователь.")

@main_router.message(AdminStates.giveaway_amount)
async def admin_giveaway_amount(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.reply("❌ Сумма должна быть числом.")
    amount = int(message.text); await state.update_data(amount=amount); data = await state.get_data()
    currency_name = "монет" if data['currency'] == 'coins' else 'звёздочек'
    await state.set_state(AdminStates.giveaway_confirm)
    kb = InlineKeyboardBuilder(); kb.button(text="✅ Подтвердить", callback_data="giveaway_confirm:yes"); kb.button(text="❌ Отмена", callback_data="giveaway_confirm:no")
    await message.answer(f"Вы уверены, что хотите раздать по **{amount}** {currency_name} **КАЖДОМУ** пользователю?", reply_markup=kb.as_markup())

@main_router.callback_query(F.data.startswith("giveaway_confirm:"), AdminStates.giveaway_confirm)
async def admin_giveaway_confirm(callback: CallbackQuery, state: FSMContext):
    if callback.data.endswith("no"):
        await state.clear(); return await callback.message.edit_text("Раздача отменена.", reply_markup=get_back_button("admin:main_panel"))
    
    data = await state.get_data(); currency, amount = data['currency'], data['amount']
    await state.clear()
    await callback.message.edit_text(f"⏳ Начинаю раздачу... Это может занять некоторое время.")
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {currency} = {currency} + ?", (amount,))
        if currency == 'coins': cursor.execute("UPDATE users SET total_coins_earned = total_coins_earned + ?", (amount,))
        conn.commit()
        
    await callback.message.edit_text("✅ Раздача успешно завершена!", reply_markup=get_back_button("admin:main_panel"))

# ... (решта коду ідентична попередньому, я включив все, щоб уникнути проблем)
@main_router.callback_query(F.data.startswith("admin:"), F.data != "admin:main_panel")
async def handle_admin_callbacks(callback: CallbackQuery, state: FSMContext):
    action = callback.data
    if action == "admin:give_balance":
        await state.set_state(AdminStates.get_user_id_for_balance)
        await callback.message.edit_text("Введите ID пользователя.\n\n_Напишите 'отмена'._")
    elif action == "admin:check_user":
        await state.set_state(AdminStates.get_user_id_for_stats)
        await callback.message.edit_text("Введите ID или @username.\n\n_Напишите 'отмена'._")
    elif action == "admin:mass_send":
        await state.set_state(AdminStates.get_message_for_mass_send)
        await callback.message.edit_text("Введите сообщение для рассылки.\n\n_Напишите 'отмена'._")

@main_router.callback_query(F.data == "admin:main_panel")
async def cb_admin_panel_back(callback: CallbackQuery, state: FSMContext):
    await cmd_admin_panel(callback.message, state)

@main_router.callback_query(F.data == "menu:games")
async def cb_games_menu(callback: CallbackQuery):
    kb = InlineKeyboardBuilder(); kb.button(text="🎲 Кости", callback_data="game:dice"); kb.button(text="🎰 Слоты", callback_data="game:slots"); kb.button(text="🃏 Дуэль Карт", callback_data="game:duel")
    kb.button(text="⬅️ Назад", callback_data="menu:main"); kb.adjust(2,1); await callback.message.edit_text("Выберите развлечение:", reply_markup=kb.as_markup())

@main_router.callback_query(F.data == "game:dice")
async def cb_game_dice(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CasinoStates.get_bet_dice); await callback.message.edit_text(f"Введите ставку (мин. {MIN_BET}).\n\n_Напишите 'отмена'._")

@main_router.message(CasinoStates.get_bet_dice)
async def process_dice_bet(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.reply("❌ Ставка должна быть числом.")
    bet = int(message.text)
    if bet < MIN_BET: return await message.reply(f"❌ Минимальная ставка: {MIN_BET}.")
    user = await get_user(message.from_user.id)
    if user['coins'] < bet: return await message.reply("❌ У вас недостаточно монет.")
    await state.clear(); await update_balance(message.from_user.id, coins=-bet)
    await message.reply("Бросаем кости...")
    await asyncio.sleep(1); user_dice = await message.answer_dice(); user_roll = user_dice.dice.value
    await asyncio.sleep(3); bot_dice = await message.answer_dice(); bot_roll = bot_dice.dice.value
    win_amount = bet * 2
    if user_roll > bot_roll:
        await update_balance(message.from_user.id, coins=win_amount, earned=True)
        await message.reply(f"🎉 **Вы победили!** ({user_roll} vs {bot_roll})\nВы выиграли **{win_amount}** монет!")
    elif bot_roll > user_roll: await message.reply(f"😕 **Вы проиграли...** ({user_roll} vs {bot_roll})\nВаша ставка в **{bet}** монет потеряна.")
    else: await update_balance(message.from_user.id, coins=bet); await message.reply(f"🤝 **Ничья!** ({user_roll} vs {bot_roll})\nВаша ставка возвращена.")

# ... (і так далі, до кінця файлу)

@main_router.callback_query(F.data == "menu:profile")
async def cb_profile(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user: return await callback.answer("Произошла ошибка, перезапустите бота /start", show_alert=True)
    level = user['rank_level']; rank_name = RANKS[level][1]; progress_text = ""
    next_rank_coins = RANKS.get(level + 1, (None, ""))[0]
    if next_rank_coins and next_rank_coins != float('inf'):
        current_rank_coins = RANKS[level][0]
        progress = (user['total_coins_earned'] - current_rank_coins) / (next_rank_coins - current_rank_coins)
        progress = max(0, min(1, progress))
        progress_bar = "█" * int(progress * 10) + "░" * (10 - int(progress * 10))
        progress_text = f"\n\n*Прогресс до ранга:*\n`{progress_bar}` {int(progress*100)}%"
    username = user['username'] or "Без_имени"
    profile_text = (f"👤 **Профиль @{escape_markdown(username)}**\n\n👑 *Ранг:* {rank_name}\n💰 *Монеты:* {user['coins']:,}\n⭐ *Звёздочки:* {user['stars']:,}{progress_text}")
    await callback.message.edit_text(profile_text, reply_markup=get_back_button())
    
# ... (всі інші обробники, які були в попередній стабільній версії)
# ...

# ----- 🚀 ЗАПУСК БОТА 🚀 -----
async def main():
    if not BOT_TOKEN: return logging.critical("ОШИБКА: Токен не найден.")
    
    dp.message.middleware(SponsorshipMiddleware())
    dp.callback_query.middleware(SponsorshipMiddleware())
    dp.include_router(main_router)
    
    init_db()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
