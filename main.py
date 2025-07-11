# main_bot.py

import asyncio
import logging
import sqlite3
import random
import os
from datetime import datetime, timedelta, date

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
BATTLE_PASS_COST_STARS = 25

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
    'c1': {'name': 'Карта Новичка', 'rarity': '⚪️ Обычная', 'type': 'card', 'power': 1},
    'c2': {'name': 'Талисман Удачи', 'rarity': '⚪️ Обычная', 'type': 'card', 'power': 1},
    'c3': {'name': 'Проклятый Дублон', 'rarity': '⚪️ Обычная', 'type': 'card', 'power': 1},
    'c4': {'name': 'Пыльный Свиток', 'rarity': '⚪️ Обычная', 'type': 'card', 'power': 1},
    'c5': {'name': 'Древняя Монета', 'rarity': '🟢 Редкая', 'type': 'card', 'power': 2},
    'c6': {'name': 'Кристалл Энергии', 'rarity': '🟢 Редкая', 'type': 'card', 'power': 2},
    'c7': {'name': 'Зелье Исцеления', 'rarity': '🟢 Редкая', 'type': 'card', 'power': 2},
    'c8': {'name': 'Амулет Защиты', 'rarity': '🟢 Редкая', 'type': 'card', 'power': 2},
    'c9': {'name': 'Звёздная Карта', 'rarity': '🔵 Эпическая', 'type': 'card', 'power': 3},
    'c10': {'name': 'Эссенция Богатства', 'rarity': '🔵 Эпическая', 'type': 'card', 'power': 3},
    'c11': {'name': 'Плащ-невидимка', 'rarity': '🔵 Эпическая', 'type': 'card', 'power': 3},
    'c12': {'name': 'Сапоги-скороходы', 'rarity': '🔵 Эпическая', 'type': 'card', 'power': 3},
    'c13': {'name': 'Корона Правителя', 'rarity': '🟣 Легендарная', 'type': 'card', 'power': 4},
    'c14': {'name': 'Осколок Вселенной', 'rarity': '🟣 Легендарная', 'type': 'card', 'power': 4},
    'c15': {'name': 'Молот Тора', 'rarity': '🟣 Легендарная', 'type': 'card', 'power': 4},
    'c16': {'name': 'Трезубец Посейдона', 'rarity': '🟣 Легендарная', 'type': 'card', 'power': 4},
    'c17': {'name': 'Сердце Галактики', 'rarity': '🟠 Мифическая', 'type': 'card', 'power': 5},
    'c18': {'name': 'Перо Феникса', 'rarity': '🟠 Мифическая', 'type': 'card', 'power': 5},
    'c19': {'name': 'Кровь Грифона', 'rarity': '🟠 Мифическая', 'type': 'card', 'power': 5},
    'c20': {'name': 'Карта COINVERSE', 'rarity': '⚜️ Уникальная', 'type': 'card', 'power': 10},
    'key1': {'name': 'Ключ от Сокровищницы', 'rarity': '🟢 Редкая', 'type': 'item'},
    'fragment1': {'name': 'Фрагмент карты', 'rarity': '⚪️ Обычная', 'type': 'craft_item'},
    'exp_sphere': {'name': 'Сфера опыта', 'rarity': '🔵 Эпическая', 'type': 'exp_item', 'xp': 50},
}

# ----- 🎁 КЕЙСИ 🎁 -----
CASES = {
    'rusty': {'name': '🔩 Ржавый ящик', 'cost': 100, 'currency': 'coins', 'prizes': [{'type': 'coins', 'amount': (10, 80), 'chance': 90}, {'type': 'item', 'item_id': 'fragment1', 'chance': 10}]},
    'bronze': {'name': '🥉 Бронзовый кейс', 'cost': 500, 'currency': 'coins', 'prizes': [ {'type': 'coins', 'amount': (100, 450), 'chance': 65}, {'type': 'item', 'item_id': 'c1', 'chance': 15}, {'type': 'item', 'item_id': 'c2', 'chance': 15}, {'type': 'item', 'item_id': 'key1', 'chance': 5},]},
    'silver': {'name': '🥈 Серебряный кейс', 'cost': 2500, 'currency': 'coins', 'prizes': [ {'type': 'coins', 'amount': (1000, 2200), 'chance': 55}, {'type': 'stars', 'amount': (1, 3), 'chance': 15}, {'type': 'item', 'item_id': 'c3', 'chance': 15}, {'type': 'item', 'item_id': 'c5', 'chance': 10}, {'type': 'item', 'item_id': 'key1', 'chance': 5},]},
    'gold':   {'name': '🥇 Золотой кейс', 'cost': 10, 'currency': 'stars', 'prizes': [ {'type': 'coins', 'amount': (15000, 25000), 'chance': 50}, {'type': 'item', 'item_id': 'c7', 'chance': 40}, {'type': 'item', 'item_id': 'c9', 'chance': 9}, {'type': 'item', 'item_id': 'c10', 'chance': 1},]},
    'treasure': {'name': '💎 Кейс Сокровищницы', 'cost': 1, 'currency': 'key1', 'prizes': [ {'type': 'stars', 'amount': (10, 25), 'chance': 50}, {'type': 'item', 'item_id': 'c8', 'chance': 30}, {'type': 'item', 'item_id': 'c10', 'chance': 20},]},
    'diamond': {'name': '💎 Алмазный кейс', 'cost': 50, 'currency': 'stars', 'prizes': [ {'type': 'stars', 'amount': (25, 45), 'chance': 50}, {'type': 'item', 'item_id': 'c10', 'chance': 25}, {'type': 'item', 'item_id': 'exp_sphere', 'chance': 25},]},
    'legendary': {'name': '🟣 Легендарный ларец', 'cost': 25, 'currency': 'stars', 'prizes': [{'type': 'item', 'item_id': 'c13', 'chance': 40}, {'type': 'item', 'item_id': 'c14', 'chance': 30}, {'type': 'item', 'item_id': 'c15', 'chance': 30}]},
}

# ----- 📜 КВЕСТИ 📜 -----
QUESTS = {
    'open_case': {'name': 'Откройте 3 кейса', 'target': 3, 'xp': 20},
    'play_casino': {'name': 'Сыграйте в казино 5 раз', 'target': 5, 'xp': 15},
    'invite_friend': {'name': 'Пригласите 1 друга', 'target': 1, 'xp': 50}
}

# ----- 🏆 BATTLE PASS 🏆 -----
BP_LEVELS = {i: {'xp': i * 50, 'free_reward': {'type': 'coins', 'amount': i * 500}, 'premium_reward': {'type': 'stars', 'amount': i}} for i in range(1, 21)}
BP_LEVELS[5]['premium_reward'] = {'type': 'item', 'item_id': 'key1'}
BP_LEVELS[10]['premium_reward'] = {'type': 'item', 'item_id': 'c7'}
BP_LEVELS[20]['premium_reward'] = {'type': 'item', 'item_id': 'c10'}

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
            referrer_id INTEGER, join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            bp_level INTEGER DEFAULT 1, bp_xp INTEGER DEFAULT 0, has_premium_bp INTEGER DEFAULT 0
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quests (
            user_id INTEGER, quest_id TEXT, progress INTEGER DEFAULT 0, last_reset_date TEXT,
            PRIMARY KEY (user_id, quest_id)
        )""")
        user_columns = [i[1] for i in cursor.execute("PRAGMA table_info(users)").fetchall()]
        if 'referrer_id' not in user_columns: cursor.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
        if 'bp_level' not in user_columns: cursor.execute("ALTER TABLE users ADD COLUMN bp_level INTEGER DEFAULT 1")
        if 'bp_xp' not in user_columns: cursor.execute("ALTER TABLE users ADD COLUMN bp_xp INTEGER DEFAULT 0")
        if 'has_premium_bp' not in user_columns: cursor.execute("ALTER TABLE users ADD COLUMN has_premium_bp INTEGER DEFAULT 0")
        conn.commit()

# ----- Функції для роботи з БД та логікою -----
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
    if referrer_id:
        await update_quest_progress(referrer_id, 'invite_friend')

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
        except: pass# ----- 📜 КВЕСТИ и БАТЛ ПАСС 📜 -----
async def get_or_create_quest(user_id, quest_id):
    today = str(date.today())
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quests WHERE user_id = ? AND quest_id = ?", (user_id, quest_id))
        quest_data = cursor.fetchone()
        if not quest_data or quest_data['last_reset_date'] != today:
            cursor.execute("INSERT OR REPLACE INTO quests (user_id, quest_id, progress, last_reset_date) VALUES (?, ?, 0, ?)", (user_id, quest_id, today))
            conn.commit()
            cursor.execute("SELECT * FROM quests WHERE user_id = ? AND quest_id = ?", (user_id, quest_id))
            quest_data = cursor.fetchone()
        return quest_data

async def check_quest_completion(user_id, quest_id):
    quest = await get_or_create_quest(user_id, quest_id)
    quest_info = QUESTS[quest_id]
    
    # Перевіряємо, чи квест вже був завершений
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT progress FROM quests WHERE user_id = ? AND quest_id = ?", (user_id, quest_id))
        current_progress = cursor.fetchone()[0]

    # Якщо прогрес вже достатній, нічого не робимо
    if current_progress < quest_info['target']:
        return

    # Якщо прогрес достатній, але нагорода вже видана (запобігаємо подвійній видачі)
    # Цю логіку можна покращити, додавши поле is_completed в БД, але поки що так
    
    await add_xp(user_id, quest_info['xp'])
    try:
        await bot.send_message(user_id, f"✅ Квест *'{quest_info['name']}'* выполнен! Вам начислено **{quest_info['xp']} XP**.")
    except:
        pass


async def update_quest_progress(user_id, quest_id, value=1):
    quest = await get_or_create_quest(user_id, quest_id)
    quest_info = QUESTS[quest_id]

    if quest['progress'] < quest_info['target']:
        new_progress = quest['progress'] + value
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE quests SET progress = ? WHERE user_id = ? AND quest_id = ?", (new_progress, user_id, quest_id))
        
        if new_progress >= quest_info['target']:
            await check_quest_completion(user_id, quest_id)

async def add_xp(user_id, xp_to_add):
    user = await get_user(user_id)
    if not user: return
    
    new_xp = user['bp_xp'] + xp_to_add
    new_level = user['bp_level']
    
    while BP_LEVELS.get(new_level) and new_xp >= BP_LEVELS[new_level]['xp']:
        new_xp -= BP_LEVELS[new_level]['xp']
        
        # Видаємо нагороди за досягнення рівня
        free_rew = BP_LEVELS[new_level]['free_reward']
        if free_rew['type'] == 'coins': await update_balance(user_id, coins=free_rew['amount'])
        elif free_rew['type'] == 'item': await add_item_to_inventory(user_id, free_rew['item_id'])
        
        if user['has_premium_bp']:
            prem_rew = BP_LEVELS[new_level]['premium_reward']
            if prem_rew['type'] == 'stars': await update_balance(user_id, stars=prem_rew['amount'])
            elif prem_rew['type'] == 'item': await add_item_to_inventory(user_id, prem_rew['item_id'])

        new_level += 1
        try:
            await bot.send_message(user_id, f"🎉 Вы достигли **{new_level}** уровня Боевого Пропуска! Проверьте награды!")
        except: pass

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET bp_level = ?, bp_xp = ? WHERE user_id = ?", (new_level, new_xp, user_id))


# ----- 🛡️ ПРОВЕРКА ПОДПИСКИ НА КАНАЛ 🛡️ -----
class SponsorshipMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message | CallbackQuery, data):
        user_id = event.from_user.id
        if ADMIN_IDS and str(user_id) in ADMIN_IDS:
            if not await get_user(user_id): await add_user(user_id, event.from_user.username)
            return await handler(event, data)
        if not SPONSOR_CHANNEL:
            if not await get_user(user_id): await add_user(user_id, event.from_user.username)
            return await handler(event, data)
        try:
            member = await bot.get_chat_member(chat_id=SPONSOR_CHANNEL, user_id=user_id)
            if member.status in ['member', 'administrator', 'creator']:
                if not await get_user(user_id):
                    referrer_id = None
                    if isinstance(event, Message) and event.text and event.text.startswith("/start"):
                        args = event.text.split()
                        if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id: referrer_id = int(args[1])
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
    b.button(text="📜 Квесты", callback_data="menu:quests"); b.button(text="🏆 Боевой Пропуск", callback_data="menu:battle_pass")
    b.button(text="💱 Обмен", callback_data="menu:exchange"); b.button(text="🗓️ Бонус", callback_data="menu:daily_bonus")
    b.button(text="🏆 Топы", callback_data="menu:tops"); b.button(text="🤝 Пригласить друга", callback_data="menu:referral")
    b.button(text="✍️ Отзывы", callback_data="menu:feedback"); b.button(text="🛠️ Крафт", callback_data="menu:craft")
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
    else:
        await message.answer(f"👋 С возвращением, {escape_markdown(message.from_user.first_name)}!", reply_markup=get_main_menu_keyboard())@main_router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery): await callback.message.delete(); await cmd_start(callback.message)

@main_router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear(); await callback.message.edit_text("Вы в главном меню.", reply_markup=get_main_menu_keyboard())

@main_router.message(F.text.lower().in_(["отмена", "/cancel"]), StateFilter("*"))
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=types.ReplyKeyboardRemove())
    if str(message.from_user.id) in ADMIN_IDS: await cmd_admin_panel(message, state)
    else: await message.answer("Вы в главном меню.", reply_markup=get_main_menu_keyboard())

# ----- 🎒 ІНВЕНТАР ТА КРАФТ 🛠️ -----
@main_router.callback_query(F.data == "menu:inventory")
async def cb_inventory(callback: CallbackQuery):
    user_inventory = await get_user_inventory(callback.from_user.id)
    if not user_inventory:
        return await callback.message.edit_text("🎒 Ваш инвентарь пуст.\n\n_Открывайте кейсы, чтобы получить коллекционные карточки и предметы!_", reply_markup=get_back_button())
    
    text = "🎒 *Ваш инвентарь:*\n\n"
    items_by_type = {'item': [], 'card': [], 'craft_item': []}
    for item_id, count in user_inventory:
        item_info = ITEMS.get(item_id)
        if item_info:
            items_by_type.setdefault(item_info.get('type', 'item'), []).append((item_id, count, item_info))

    if items_by_type['item']:
        text += "*Предметы:*\n"
        for item_id, count, item_info in items_by_type['item']:
            text += f"  - {item_info['name']} - {count} шт.\n"
        text += "\n"
        
    if items_by_type['craft_item']:
        text += "*Материалы для крафта:*\n"
        for item_id, count, item_info in items_by_type['craft_item']:
            text += f"  - {item_info['name']} - {count} шт.\n"
        text += "\n"

    if items_by_type['card']:
        text += "*Коллекционные карточки:*\n"
        rarity_order = ['⚪️ Обычная', '🟢 Редкая', '🔵 Эпическая', '🟣 Легендарная', '🟠 Мифическая', '⚜️ Уникальная']
        sorted_cards = sorted(items_by_type['card'], key=lambda x: rarity_order.index(x[2]['rarity']))
        for card_id, count, card_info in sorted_cards:
            text += f"  - {card_info['rarity']} *{card_info['name']}* - {count} шт.\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_button())
    
@main_router.callback_query(F.data == "menu:craft")
async def cb_craft_menu(callback: CallbackQuery):
    user_inventory = await get_user_inventory(callback.from_user.id)
    fragment_count = next((count for item_id, count in user_inventory if item_id == 'fragment1'), 0)
    
    kb = InlineKeyboardBuilder()
    text = "🛠️ *Мастерская Крафта*\n\nЗдесь вы можете создавать новые предметы из материалов.\n\n"
    text += f"У вас есть **{fragment_count}** фрагментов карт.\n\n"
    
    if fragment_count >= 10:
        text += "Создать случайную редкую карту (требуется 10 фрагментов)."
        kb.button(text="Создать карту (10 фрагментов)", callback_data="craft:rare_card")
    else:
        text += f"Нужно еще **{10 - fragment_count}** фрагментов, чтобы создать случайную редкую карту."
        
    kb.button(text="⬅️ Назад", callback_data="menu:main")
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

@main_router.callback_query(F.data == "craft:rare_card")
async def cb_craft_rare_card(callback: CallbackQuery):
    user_inventory = await get_user_inventory(callback.from_user.id)
    fragment_count = next((count for item_id, count in user_inventory if item_id == 'fragment1'), 0)
    
    if fragment_count < 10:
        return await callback.answer("❌ У вас недостаточно фрагментов!", show_alert=True)
    
    await remove_item_from_inventory(callback.from_user.id, 'fragment1', 10)
    
    rare_cards = [cid for cid, cinfo in ITEMS.items() if cinfo.get('rarity') == '🟢 Редкая' and cinfo.get('type') == 'card']
    crafted_card_id = random.choice(rare_cards)
    await add_item_to_inventory(callback.from_user.id, crafted_card_id)
    
    await callback.answer("✨ Вы успешно создали карту! ✨", show_alert=True)
    await callback.message.answer(f"Вы создали: *{ITEMS[crafted_card_id]['rarity']} {ITEMS[crafted_card_id]['name']}*")
    await cb_craft_menu(callback)

# ----- 🤝 РЕФЕРАЛЬНА СИСТЕМА ТА ВІДГУКИ ✍️ -----
@main_router.callback_query(F.data == "menu:referral")
async def cb_referral(callback: CallbackQuery):
    me = await bot.get_me()
    referral_link = f"https://t.me/{me.username}?start={callback.from_user.id}"
    text = (f"🤝 *Пригласите друга и получите бонус!* \n\n"
            f"Отправьте другу свою уникальную ссылку. Когда он запустит бота по ней, вы оба получите награду:\n\n"
            f"- *Вы получите:* **{REFERRAL_BONUS:,}** монет 💰\n"
            f"- *Ваш друг получит:* **{REFERRED_BONUS:,}** монет при старте! 💸\n\n"
            f"Ваша ссылка:\n`{referral_link}`")
    await callback.message.edit_text(text, reply_markup=get_back_button())

@main_router.callback_query(F.data == "menu:feedback")
async def cb_feedback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FeedbackState.waiting_for_feedback)
    await callback.message.edit_text(
        "✍️ *Оставить отзыв*\n\n"
        "Пожалуйста, напишите свой отзыв, идею или сообщение об ошибке одним сообщением. "
        "Ваш отзыв будет анонимно отправлен администрации.\n\n"
        "_Для отмены напишите 'отмена' или /cancel_",
        reply_markup=get_back_button())

@main_router.message(FeedbackState.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext):
    await state.clear()
    feedback_text = (f"📬 *Новый отзыв от пользователя!* (ID: `{message.from_user.id}`)\n\n"
                     f"Текст:\n_{escape_markdown(message.text)}_")
    if ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try: await bot.send_message(admin_id, feedback_text)
            except Exception as e: logging.error(f"Не удалось отправить отзыв админу {admin_id}: {e}")
    await message.answer("✅ Спасибо! Ваш отзыв был отправлен.", reply_markup=get_main_menu_keyboard())

# ----- 💻 АДМІН-ПАНЕЛЬ 💻 -----
@main_router.message(Command("admin"))
async def cmd_admin_panel(message: Message, state: FSMContext):
    if str(message.from_user.id) not in ADMIN_IDS: return
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="💸 Выдать/Забрать", callback_data="admin:edit_balance")
    kb.button(text="📊 Статистика игрока", callback_data="admin:check_user")
    kb.button(text="🚁 Раздача всем", callback_data="admin:giveaway")
    kb.button(text="📈 Глобальная статистика", callback_data="admin:global_stats")
    kb.button(text="📢 Сделать рассылку", callback_data="admin:mass_send")
    kb.button(text="⬅️ В главное меню", callback_data="menu:main")
    kb.adjust(1)
    await message.answer("👑 **Админ-панель**", reply_markup=kb.as_markup())

@main_router.callback_query(F.data == "admin:main_panel")
async def cb_admin_panel_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_admin_panel(callback.message, state)

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
    except: await message.reply("❌ Ошибка в команде. Пример: `/give монеты 10000` или `/give item key1`")# ----- АДМІН-ПАНЕЛЬ: ЛОГІКА КНОПОК -----
@main_router.callback_query(F.data == "admin:global_stats")
async def admin_global_stats(callback: CallbackQuery):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(user_id) FROM users"); total_users = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(coins) FROM users"); total_coins = cursor.fetchone()[0] or 0
        cursor.execute("SELECT SUM(stars) FROM users"); total_stars = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(id) FROM inventory"); total_items = cursor.fetchone()[0]
    
    text = (f"📈 *Глобальная статистика бота:*\n\n"
            f"👥 *Всего пользователей:* {total_users}\n"
            f"💰 *Всего монет в экономике:* {total_coins:,}\n"
            f"⭐ *Всего звёздочек в экономике:* {total_stars:,}\n"
            f"🃏 *Всего предметов в инвентарях:* {total_items:,}")
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

@main_router.callback_query(F.data == "admin:edit_balance")
async def admin_edit_balance_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.get_user_id_for_balance); await callback.message.edit_text("Введите ID пользователя.\n\n_Напишите 'отмена'._")

@main_router.message(AdminStates.get_user_id_for_balance)
async def admin_edit_balance_get_id(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.reply("❌ ID должен быть числом.")
    target_id = int(message.text)
    if not await get_user(target_id):
        await message.reply("❌ Пользователь с таким ID не найден в базе.")
        await state.clear(); return await cmd_admin_panel(message, state)
    await state.update_data(target_id=target_id); await state.set_state(AdminStates.get_currency_type)
    kb = InlineKeyboardBuilder(); kb.button(text="💰 Монеты", callback_data="admin_edit:coins"); kb.button(text="⭐ Звёздочки", callback_data="admin_edit:stars"); kb.button(text="🃏 Предмет", callback_data="admin_edit:item")
    await message.answer("Выберите, что хотите изменить:", reply_markup=kb.as_markup())

@main_router.callback_query(F.data.startswith("admin_edit:"), AdminStates.get_currency_type)
async def admin_edit_balance_get_type(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.split(":")[1]; await state.update_data(currency=currency); await state.set_state(AdminStates.get_amount)
    prompt = "Введите количество (для списания -100)" if currency != 'item' else "Введите ID предмета (для списания с минусом: -key1)"
    await callback.message.edit_text(f"{prompt}.\n\n_Напишите 'отмена'._")

@main_router.message(AdminStates.get_amount)
async def admin_edit_balance_get_amount(message: Message, state: FSMContext):
    data = await state.get_data(); target_id, currency = data['target_id'], data['currency']
    if currency == 'item':
        item_id = message.text
        if item_id.startswith('-'):
            item_to_remove = item_id[1:]
            if item_to_remove not in ITEMS: return await message.reply(f"❌ Предмет с ID '{item_to_remove}' не найден.")
            await remove_item_from_inventory(target_id, item_to_remove)
            await message.answer(f"✅ Успешно удален 1 предмет '{ITEMS[item_to_remove]['name']}' у пользователя {target_id}.")
        else:
            if item_id not in ITEMS: return await message.reply(f"❌ Предмет с ID '{item_id}' не найден.")
            await add_item_to_inventory(target_id, item_id)
            await message.answer(f"✅ Успешно выдан предмет '{ITEMS[item_id]['name']}' пользователю {target_id}.")
    else:
        try: amount = int(message.text)
        except ValueError: return await message.reply("❌ Количество должно быть целым числом.")
        if currency == "coins": await update_balance(target_id, coins=amount, earned=(amount > 0)); await message.answer(f"✅ Баланс монет пользователя {target_id} изменен на {amount}.")
        elif currency == "stars": await update_balance(target_id, stars=amount); await message.answer(f"✅ Баланс звёздочек пользователя {target_id} изменен на {amount}.")
    await state.clear(); await cmd_admin_panel(message, state)
    
@main_router.callback_query(F.data == "admin:check_user")
async def admin_check_user_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.get_user_id_for_stats); await callback.message.edit_text("Введите ID или @username.\n\n_Напишите 'отмена'._")

@main_router.message(AdminStates.get_user_id_for_stats)
async def admin_show_user_stats(message: Message, state: FSMContext):
    user_id, user = None, None
    user_data_input = message.text
    if user_data_input.isdigit(): user_id = int(user_data_input); user = await get_user(user_id)
    elif user_data_input.startswith('@'):
        username_to_find = user_data_input[1:]
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row; cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username_to_find,)); user = cursor.fetchone()
            if user: user_id = user['user_id']
    else: await message.reply("❌ Неверный формат."); await state.clear(); await cmd_admin_panel(message, state); return
    if not user: await message.reply("❌ Пользователь не найден.")
    else:
        inventory_items = await get_user_inventory(user_id)
        inventory_text = "\n\n*Инвентарь:*\n"
        if not inventory_items: inventory_text += "_Пусто_"
        else:
            for item_id, count in inventory_items:
                inventory_text += f" - {ITEMS.get(item_id, {'name': 'Неизвестный предмет'})['name']} ({item_id}) x{count}\n"
        safe_username = escape_markdown(user['username'])
        stats_text = (f"📊 **Статистика игрока ID `{user_id}`**\n\nЮзернейм: @{safe_username}\nМонеты: {user['coins']:,}\nЗвёздочки: {user['stars']:,}\nРанг: {RANKS[user['rank_level']][1]}"
                      f"{inventory_text}")
        await message.answer(stats_text)
    await state.clear(); await cmd_admin_panel(message, state)

@main_router.callback_query(F.data == "admin:mass_send")
async def admin_mass_send_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.get_message_for_mass_send); await callback.message.edit_text("Введите сообщение для рассылки.\n\n_Напишите 'отмена'._")

@main_router.message(AdminStates.get_message_for_mass_send)
async def admin_mass_send_get_msg(message: Message, state: FSMContext):
    await state.update_data(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(AdminStates.confirm_mass_send)
    kb = InlineKeyboardBuilder(); kb.button(text="✅ Отправить", callback_data="send_yes"); kb.button(text="❌ Отменить", callback_data="send_no")
    await message.answer("Вы уверены?", reply_markup=kb.as_markup()); await bot.copy_message(chat_id=message.chat.id, from_chat_id=message.chat.id, message_id=message.message_id)

@main_router.callback_query(F.data.in_({"send_yes", "send_no"}), AdminStates.confirm_mass_send)
async def admin_mass_send_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if callback.data == "send_no":
        await state.clear(); await callback.message.edit_text("Рассылка отменена."); await cmd_admin_panel(callback.message, state); return
    await state.clear(); await callback.message.edit_text("⏳ Начинаю рассылку...")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor(); cursor.execute("SELECT user_id FROM users"); user_ids = cursor.fetchall()
    sent_count, failed_count = 0, 0
    for (user_id,) in user_ids:
        try: await bot.copy_message(chat_id=user_id, from_chat_id=data['chat_id'], message_id=data['message_id']); sent_count += 1; await asyncio.sleep(0.1)
        except: failed_count += 1
    await callback.message.answer(f"✅ Рассылка завершена!\n\nОтправлено: {sent_count}\nНе удалось: {failed_count}"); await cmd_admin_panel(callback.message, state)

# ----- 🎮 РОЗВАГИ 🎮 -----
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
    await state.clear(); await update_balance(message.from_user.id, coins=-bet); await update_quest_progress(message.from_user.id, 'play_casino')
    await message.reply("Бросаем кости...")
    await asyncio.sleep(1); user_dice = await message.answer_dice(); user_roll = user_dice.dice.value
    await asyncio.sleep(3); bot_dice = await message.answer_dice(); bot_roll = bot_dice.dice.value
    win_amount = bet * 2
    if user_roll > bot_roll:
        await update_balance(message.from_user.id, coins=win_amount, earned=True)
        await message.reply(f"🎉 **Вы победили!** ({user_roll} vs {bot_roll})\nВы выиграли **{win_amount}** монет!")
    elif bot_roll > user_roll: await message.reply(f"😕 **Вы проиграли...** ({user_roll} vs {bot_roll})\nВаша ставка в **{bet}** монет потеряна.")
    else: await update_balance(message.from_user.id, coins=bet); await message.reply(f"🤝 **Ничья!** ({user_roll} vs {bot_roll})\nВаша ставка возвращена.")

@main_router.callback_query(F.data == "game:slots")
async def cb_game_slots(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CasinoStates.get_bet_slots); await callback.message.edit_text(f"Введите ставку (мин. {MIN_BET}).\n\n_Напишите 'отмена'._")

@main_router.message(CasinoStates.get_bet_slots)
async def process_slots_bet(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.reply("❌ Ставка должна быть числом.")
    bet = int(message.text)
    if bet < MIN_BET: return await message.reply(f"❌ Минимальная ставка: {MIN_BET}.")
    user = await get_user(message.from_user.id);
    if user['coins'] < bet: return await message.reply("❌ У вас недостаточно монет.")
    await state.clear(); await update_balance(message.from_user.id, coins=-bet); await update_quest_progress(message.from_user.id, 'play_casino')
    slots = ["🍓", "🍋", "🍀", "💎", "BAR"]; reels = [random.choice(slots) for _ in range(3)]
    result_msg = await message.answer(f"Крутим барабаны...\n\n[❓] [❓] [❓]")
    await asyncio.sleep(1); await result_msg.edit_text(f"Крутим барабаны...\n\n[{reels[0]}] [❓] [❓]")
    await asyncio.sleep(1); await result_msg.edit_text(f"Крутим барабаны...\n\n[{reels[0]}] [{reels[1]}] [❓]")
    await asyncio.sleep(1); await result_msg.edit_text(f"Ваш результат:\n\n[{reels[0]}] [{reels[1]}] [{reels[2]}]")
    win = 0
    if reels[0] == reels[1] == reels[2]: win = {'💎': bet * 25, 'BAR': bet * 15, '🍀': bet * 10}.get(reels[0], bet * 5)
    elif reels[0] == reels[1] or reels[1] == reels[2]: win = {'💎': bet * 3}.get(reels[1], bet * 2)
    if win > 0: await update_balance(message.from_user.id, coins=win, earned=True); await message.answer(f"🎉 **Поздравляем!** Вы выиграли **{win}** монет!")
    else: await message.answer("😕 Увы, не повезло.")
    
@main_router.callback_query(F.data == "game:duel")
async def cb_game_duel(callback: CallbackQuery):
    user_inventory = await get_user_inventory(callback.from_user.id)
    card_items = [item for item in user_inventory if ITEMS.get(item[0], {}).get('type') == 'card']
    if not card_items: return await callback.answer("У вас нет карт для дуэли!", show_alert=True)
    
    kb = InlineKeyboardBuilder()
    for card_id, count in card_items:
        kb.button(text=f"{ITEMS[card_id]['name']} ({count} шт.)", callback_data=f"duel_card:{card_id}")
    kb.button(text="⬅️ Назад", callback_data="menu:games"); kb.adjust(1)
    await callback.message.edit_text("Выберите карту для дуэли:", reply_markup=kb.as_markup())

@main_router.callback_query(F.data.startswith("duel_card:"))
async def process_card_duel(callback: CallbackQuery):
    user_card_id = callback.data.split(":")[1]; user_card = ITEMS[user_card_id]
    
    await remove_item_from_inventory(callback.from_user.id, user_card_id, 1)

    bot_card_id = random.choice([cid for cid, cinfo in ITEMS.items() if cinfo['type'] == 'card'])
    bot_card = ITEMS[bot_card_id]
    
    await callback.message.edit_text(f"Вы выбрали: *{user_card['name']}* ({user_card['rarity']})\nБот выбирает карту...")
    await asyncio.sleep(2)
    
    result_text = f"Вы: *{user_card['name']}* (Сила: {user_card['power']})\nБот: *{bot_card['name']}* (Сила: {bot_card['power']})\n\n"
    
    if user_card['power'] > bot_card['power']:
        win_amount = user_card['power'] * 1000
        await update_balance(callback.from_user.id, coins=win_amount, earned=True)
        result_text += f"🎉 **Вы победили** и получаете **{win_amount:,}** монет!"
    elif bot_card['power'] > user_card['power']: result_text += "😕 **Вы проиграли**."
    else: result_text += "🤝 **Ничья!**"
        
    await callback.message.edit_text(result_text, reply_markup=get_back_button("menu:games"))

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
    
@main_router.callback_query(F.data == "menu:daily_bonus")
async def cb_daily_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id; user = await get_user(user_id); today = datetime.now().date()
    last_bonus_date = datetime.strptime(user['last_bonus_date'], '%Y-%m-%d').date() if user['last_bonus_date'] else None
    if last_bonus_date == today: return await callback.answer("Вы уже получали бонус сегодня!", show_alert=True)
    streak = (user['daily_bonus_streak'] % 7) + 1 if last_bonus_date and (today - last_bonus_date).days == 1 else 1
    base_reward = 100 * streak
    reward_text = f"🎉 Вы получили бонус: **{base_reward}** монет.\nВаша серия: **{streak}** дней."
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET daily_bonus_streak = ?, last_bonus_date = ? WHERE user_id = ?", (streak, today.strftime('%Y-%m-%d'), user_id))
    await update_balance(user_id, coins=base_reward, earned=True)
    await callback.answer(reward_text.replace("*", "").replace("`", ""), show_alert=True)
    
@main_router.callback_query(F.data == "menu:tops")
async def cb_tops_menu(callback: CallbackQuery):
    kb = InlineKeyboardBuilder(); kb.button(text="🏆 Топ по монетам", callback_data="top:coins"); kb.button(text="⭐ Топ по звёздочкам", callback_data="top:stars")
    kb.button(text="⬅️ Назад", callback_data="menu:main"); kb.adjust(1); await callback.message.edit_text("Выберите рейтинг:", reply_markup=kb.as_markup())

async def show_top_list(callback: CallbackQuery, top_type: str, currency_name: str, emoji: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row; cursor = conn.cursor()
        cursor.execute(f"SELECT username, {top_type} FROM users WHERE {top_type} > 0 ORDER BY {top_type} DESC LIMIT 10")
        top_users = cursor.fetchall()
    if not top_users: return await callback.answer("Рейтинг пока пуст!", show_alert=True)
    top_text = f"🏆 **Топ-10 по {currency_name}**\n\n"
    for i, user in enumerate(top_users, 1):
        place_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**"); username = user['username'] or "Скрытный_игрок"
        top_text += f"{place_emoji} @{escape_markdown(username)} — **{user[top_type]:,}** {emoji}\n"
    await callback.message.edit_text(top_text, reply_markup=get_back_button("menu:tops"))

@main_router.callback_query(F.data == "top:coins")
async def cb_top_coins(callback: CallbackQuery): await show_top_list(callback, "coins", "монетам", "💰")

@main_router.callback_query(F.data == "top:stars")
async def cb_top_stars(callback: CallbackQuery): await show_top_list(callback, "stars", "звёздочкам", "⭐")

@main_router.callback_query(F.data == "menu:cases")
async def cb_cases_menu(callback: CallbackQuery):
    user = await get_user(callback.from_user.id); kb = InlineKeyboardBuilder()
    text = "🎁 **Магазин кейсов**\n\n"
    for case_id, info in CASES.items():
        if info.get('currency') == 'key1': continue
        cost, currency, emoji = info['cost'], info.get('currency', 'coins'), {'coins': '💰', 'stars': '⭐'}[info.get('currency', 'coins')]
        text += f"**{info['name']}**\nЦена: {cost:,} {emoji}\n\n";
        if user[currency] >= cost: kb.button(text=f"Открыть {info['name']}", callback_data=f"case:{case_id}")
    
    user_inventory = await get_user_inventory(callback.from_user.id)
    key_count = next((count for item_id, count in user_inventory if item_id == 'key1'), 0)
    if key_count > 0: kb.button(text=f"🔑 Открыть Сокровищницу ({key_count} шт.)", callback_data="case:treasure")
        
    kb.button(text="⬅️ Назад", callback_data="menu:main"); kb.adjust(1); await callback.message.edit_text(text, reply_markup=kb.as_markup())

@main_router.callback_query(F.data.startswith("case:"))
async def cb_open_case(callback: CallbackQuery):
    case_id, user_id = callback.data.split(":")[1], callback.from_user.id; case_info, user = CASES[case_id], await get_user(user_id)
    cost, cost_currency = case_info['cost'], case_info.get('currency', 'coins')

    if cost_currency == 'key1':
        user_inventory = await get_user_inventory(user_id)
        if not any(item_id == 'key1' for item_id, _ in user_inventory): return await callback.answer("У вас нет ключей!", show_alert=True)
        await remove_item_from_inventory(user_id, 'key1', 1)
    elif user[cost_currency] < cost: return await callback.answer("У вас недостаточно средств!", show_alert=True)
    else: await update_balance(user_id, coins=-cost if cost_currency == 'coins' else 0, stars=-cost if cost_currency == 'stars' else 0)
    
    await update_quest_progress(user_id, 'open_case')
    rand_val = random.randint(1, 100); cumulative_chance = 0; prize = None
    for p in case_info['prizes']:
        cumulative_chance += p['chance'];
        if rand_val <= cumulative_chance: prize = p; break
    if not prize: return await callback.message.answer("Что-то пошло не так...")
    
    prize_text = ""
    if prize['type'] == 'coins':
        amount = random.randint(prize['amount'][0], prize['amount'][1])
        await update_balance(user_id, coins=amount, earned=True); prize_text = f"🎉 Вы выиграли **{amount:,} монет** 💰!"
    elif prize['type'] == 'stars':
        amount = prize['amount'] if isinstance(prize['amount'], int) else random.randint(prize['amount'][0], prize['amount'][1])
        await update_balance(user_id, stars=amount); prize_text = f"🌟 Вы выиграли **{amount:,} звёздочек** ⭐!"
    elif prize['type'] == 'item':
        item_id = prize['item_id']; item_info = ITEMS[item_id]
        await add_item_to_inventory(user_id, item_id)
        prize_text = f"Предмет!\n\nВы получили: *{item_info['rarity']} {item_info['name']}*"

    await callback.answer(f"Открываем {case_info['name']}...", show_alert=False); await callback.message.answer(prize_text); await cb_cases_menu(callback)

@main_router.callback_query(F.data == "menu:exchange")
async def cb_exchange_menu(callback: CallbackQuery):
    kb = InlineKeyboardBuilder();
    kb.button(text=f"Продать ⭐ за 💰 ({STAR_SELL_PRICE:,})", callback_data="exchange:s2c")
    kb.button(text=f"Купить ⭐ за 💰 ({STAR_BUY_PRICE:,})", callback_data="exchange:c2s")
    kb.button(text="⬅️ Назад", callback_data="menu:main"); kb.adjust(2,1); await callback.message.edit_text("💱 **Обмен валют**", reply_markup=kb.as_markup())

@main_router.callback_query(F.data.in_({"exchange:s2c", "exchange:c2s"}))
async def cb_start_exchange(callback: CallbackQuery, state: FSMContext):
    exchange_type = callback.data.split(":")[1]; await state.update_data(type=exchange_type); await state.set_state(ExchangeStates.amount)
    prompt = f"Введите количество звёздочек.\n\n_Напишите 'отмена'._"
    await callback.message.edit_text(prompt)

@main_router.message(ExchangeStates.amount)
async def process_exchange_amount(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.reply("❌ Количество должно быть числом.")
    amount = int(message.text)
    if amount <= 0: return await message.reply("❌ Количество должно быть больше нуля.")
    data = await state.get_data(); user = await get_user(message.from_user.id); await state.clear()
    if data['type'] == 's2c':
        if user['stars'] < amount: return await message.answer("❌ У вас недостаточно звёздочек.")
        coins_get = amount * STAR_SELL_PRICE
        await update_balance(message.from_user.id, stars=-amount, coins=coins_get, earned=True)
        await message.answer(f"✅ Вы продали **{amount}** ⭐ и получили **{coins_get:,}** 💰.")
    elif data['type'] == 'c2s':
        cost = amount * STAR_BUY_PRICE
        if user['coins'] < cost: return await message.answer(f"❌ У вас недостаточно монет. Нужно **{cost:,}** 💰.")
        await update_balance(message.from_user.id, stars=amount, coins=-cost)
        await message.answer(f"✅ Вы купили **{amount}** ⭐ за **{cost:,}** 💰.")

@main_router.message()
async def any_message(message: Message):
    if ADMIN_IDS and str(message.from_user.id) not in ADMIN_IDS:
        try:
            user_info_text = (f"Сообщение от: @{message.from_user.username or 'Без_имени'}\nID: {message.from_user.id}")
            for admin_id in ADMIN_IDS:
                await bot.send_message(admin_id, user_info_text)
                await bot.forward_message(chat_id=admin_id, from_chat_id=message.chat.id, message_id=message.message_id)
        except Exception as e: logging.error(f"Не удалось переслать сообщение: {e}")

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
