import asyncio
import json
import os
import random
import string
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "8595080357:AAEhqULh8o8jSIynYgoOzDjlkdY9cCWUoZo"
ADMIN_ID = 2109352567
DATA_FILE = "users.json"
TOP_FILE = "toper.json"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

active_crashes = {}
pending_reteik = {}
pending_support = {}
pending_broad = {}

class BetState(StatesGroup):
    waiting_bet = State()
class CoinState(StatesGroup):
    choosing = State()
class HighLowState(StatesGroup):
    choosing = State()
class BlackjackState(StatesGroup):
    playing = State()
class DiceState(StatesGroup):
    choosing_sum = State()

KEY_MAP = {"balance": "b", "level": "l", "hex": "h", "pets": "p", "support_cd": "sc", "agreed": "a", "zero_bonus_end": "z", "last_collect_time": "lc", "notify_sent": "n", "rehex_count": "rc", "rehex_cost": "rx"}
REVERSE_MAP = {v: k for k, v in KEY_MAP.items()}

def shorten(data):
    if isinstance(data, dict):
        return {KEY_MAP.get(k, k): shorten(v) for k, v in data.items()}
    return data

def restore(data):
    if isinstance(data, dict):
        return {REVERSE_MAP.get(k, k): restore(v) for k, v in data.items()}
    return data

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            return {uid: restore(user) for uid, user in raw.items()}
    return {}

def save_data(data):
    short = {uid: shorten(user) for uid, user in data.items()}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(short, f, ensure_ascii=False, separators=(',', ':'))

users = load_data()
top_cache = {"money": [], "level": []}

def rebuild_top():
    global top_cache
    sorted_money = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)
    money_list = [{"username": f"@{u.get('username', '—')}", "balance": u["balance"], "level": u.get("level", 1), "place": i + 1} for i, (_, u) in enumerate(sorted_money[:15])]
    sorted_level = sorted(users.items(), key=lambda x: x[1].get("level", 1), reverse=True)
    level_list = [{"username": f"@{u.get('username', '—')}", "balance": u["balance"], "level": u.get("level", 1), "place": i + 1} for i, (_, u) in enumerate(sorted_level[:15])]
    top_cache = {"money": money_list, "level": level_list}
    with open(TOP_FILE, "w", encoding="utf-8") as f:
        json.dump(top_cache, f, ensure_ascii=False, indent=2)

rebuild_top()

def get_hex():
    return ''.join(random.choices(string.ascii_lowercase, k=6))

def get_user(user_id):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"balance": 50, "level": 1, "hex": get_hex(), "pets": {}, "support_cd": 0, "agreed": False, "zero_bonus_end": 0, "last_collect_time": datetime.now().isoformat(), "notify_sent": False, "rehex_count": 0, "rehex_cost": 10000}
        save_data(users)
    else:
        u = users[uid]
        if "last_collect_time" not in u: u["last_collect_time"] = datetime.now().isoformat(); u["notify_sent"] = False
        if "pets" not in u: u["pets"] = {}
        if "rehex_count" not in u: u["rehex_count"] = 0; u["rehex_cost"] = 10000
    return users[uid]

def handle_zero_balance(u):
    if u["balance"] > 0:
        u.pop("zero_bonus_end", None)
    elif u["balance"] <= 0 and u.get("zero_bonus_end", 0) == 0:
        u["zero_bonus_end"] = time.time() + 3600

PETS = [
    ("🐱 TexCat", 8, 1, 100), ("🐶 GoldDog", 13, 1, 150), ("🐦 SkyBird", 19, 1, 225),
    ("🐟 AquaFish", 29, 1, 338), ("🦋 LuckyButterfly", 44, 1, 507),
    ("🐉 FireDragon", 66, 5, 760), ("🦅 EagleTex", 99, 5, 1140), ("🐺 ShadowWolf", 148, 5, 1710),
    ("🐘 BigElephant", 222, 5, 2565), ("🦒 TallGiraffe", 333, 5, 3848),
    ("🦄 MagicUnicorn", 500, 10, 5772), ("🐲 GoldenDragon", 750, 10, 8658),
    ("🦁 KingLion", 1125, 10, 12987), ("🐼 PandaTex", 1688, 10, 19480), ("🐯 TigerKing", 2532, 10, 29220)
]

GAMES = {
    "game_slots": {"title": "🎰 Слоты", "desc": "Три одинаковых символа = победа.", "chance": 0.30, "multiplier": 4.0},
    "game_roulette": {"title": "🎡 Рулетка", "desc": "Угадай цвет.", "chance": 0.28, "multiplier": 2.8},
    "game_bj": {"title": "🃏 Блэкджек", "desc": "Набери ближе к 21.", "chance": 0.37, "multiplier": 2.1},
    "game_coin": {"title": "🪙 Монетка", "desc": "Орёл или решка.", "chance": 0.48, "multiplier": 1.85},
    "game_dice": {"title": "🎲 Кубики", "desc": "Угадай сумму двух кубиков.", "chance": 0.27, "multiplier": 3.0},
    "game_highlow": {"title": "⬆️ Выше/Ниже","desc": "Следующая карта выше или ниже?", "chance": 0.34, "multiplier": 2.3},
    "game_crash": {"title": "💥 Crash", "desc": "Выводи до краша.", "chance": 0.25, "multiplier": 4.0},
    "game_wheel": {"title": "🎰 Wheel", "desc": "Колесо фортуны.", "chance": 0.26, "multiplier": 3.3}
}

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Сыграть в Casino", callback_data="casino")],
        [InlineKeyboardButton(text="🐾 Магазин питомцев", callback_data="pets")],
        [InlineKeyboardButton(text="🛠 Тех. Поддержка", callback_data="support")],
        [InlineKeyboardButton(text="❓ Помощь по командам", callback_data="help")],
        [InlineKeyboardButton(text="⭐ Донат (Звёзды)", callback_data="donate")]
    ])

def casino_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=GAMES[g]["title"], callback_data=g)] for g in GAMES])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return kb

def back_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]])

def repeat_back_kb(game_cb):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Повторить", callback_data=game_cb)],
        [InlineKeyboardButton(text="⬅️ Назад в список игр", callback_data="casino")]
    ])

def pet_shop_kb(user):
    kb = []
    for i, (name, earn, req, price) in enumerate(PETS):
        owned = name in user.get("pets", {})
        txt = f"{name} ✅" if owned else f"Купить {name} — {price:,} TeX" if user["level"] >= req else f"{name} 🔒 (lvl {req})"
        cd = "pet_owned" if owned else f"buy_pet_{i}" if user["level"] >= req else "locked"
        kb.append([InlineKeyboardButton(text=txt, callback_data=cd)])
    kb.append([InlineKeyboardButton(text="💰 Собрать монеты", callback_data="collect")])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_next_level_cost(level: int) -> int:
    if level < 20: return int(100 * (1.3 ** (level - 1)))
    elif level < 35: return int(100 * (1.3 ** 19) * (1.2 ** (level - 20)))
    elif level < 50: return int(100 * (1.3 ** 19) * (1.2 ** 15) * (1.1 ** (level - 35)))
    else: return int(100 * (1.3 ** 19) * (1.2 ** 15) * (1.1 ** 15) * (1.05 ** (level - 50)))

def get_pet_multiplier(level: int) -> float:
    mult = 1.0
    if level >= 20: mult += 0.10
    if level >= 35: mult += 0.25
    if level >= 50: mult += 0.30
    if level >= 100: mult += 1.00
    return mult

def get_bet_limits(level: int):
    if level >= 100: return 500, 1500000
    if level >= 75: return 300, 1000000
    if level >= 65: return 200, 500000
    if level >= 50: return 150, 150000
    if level >= 35: return 100, 15000
    if level >= 20: return 25, 1500
    return 5, 250

def get_level_badge(level: int) -> str:
    if level >= 200: return "🌟 УЛЬТИМАТНЫЙ"
    if level >= 100: return "🔥 ЛЕГЕНДАРНЫЙ"
    if level >= 50: return "⭐ МАСТЕР"
    if level >= 20: return "🏆 МАКСИМАЛЬНЫЙ"
    return ""

def level_menu_kb(user):
    cost = get_next_level_cost(user["level"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🚀 Прокачать уровень — {cost:,} TeX", callback_data="upgrade_level")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

async def show_main_menu(obj):
    uid = str(obj.from_user.id)
    u = get_user(uid)
    u["username"] = obj.from_user.username or "нет"
    handle_zero_balance(u)
    sorted_users = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)
    place = next((i+1 for i,(k,v) in enumerate(sorted_users) if k == uid), 16)
    top_text = ">" if place > 15 else str(place)
    badge = get_level_badge(u["level"])
    level_text = f"{u['level']} {badge}" if badge else str(u['level'])
    text = f"""👤 Ник: @{u['username']}
💰 Баланс: {u['balance']} TeX
🏆 Уровень: {level_text}
📊 Место в топе: {top_text}
🔑 HEX: {u['hex']}"""
    kb = main_menu_kb()
    if isinstance(obj, CallbackQuery):
        await obj.message.edit_text(text, reply_markup=kb)
    else:
        await obj.answer(text, reply_markup=kb)
    save_data(users)

async def show_level_menu(obj):
    uid = str(obj.from_user.id)
    u = get_user(uid)
    u["username"] = obj.from_user.username or "нет"
    level = u["level"]
    cost = get_next_level_cost(level)
    sorted_level = sorted(users.items(), key=lambda x: x[1].get("level", 1), reverse=True)
    place = next((i+1 for i,(k,v) in enumerate(sorted_level) if k == uid), 16)
    top_text = ">" if place > 15 else str(place)
    badge = get_level_badge(level)
    min_bet, max_bet = get_bet_limits(level)
    extra = "\n✅ У тебя есть все питомцы — можно качнуть до 20!" if level == 19 and len(u.get("pets", {})) == len(PETS) else ""
    text = f"""🏆 Ваш уровень: {level} {badge}
💰 Стоимость следующего: {cost:,} TeX
📊 Топ по уровням: {top_text} место
🎰 Лимиты ставок: {min_bet} — {max_bet} TeX{extra}"""
    kb = level_menu_kb(u)
    if isinstance(obj, CallbackQuery):
        await obj.message.edit_text(text, reply_markup=kb)
    else:
        await obj.answer(text, reply_markup=kb)
    save_data(users)

@dp.message(Command("start"))
async def start(msg: Message):
    u = get_user(msg.from_user.id)
    if not u.get("agreed", False):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Согласиться и продолжить", callback_data="agree")]])
        await msg.answer("👋 В боте только выдуманная валюта TeX!\nНет реальных покупок.\nНажми кнопку ниже:", reply_markup=kb)
    else:
        await show_main_menu(msg)

@dp.callback_query(F.data == "agree")
async def agree(cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    u["agreed"] = True
    save_data(users)
    await cb.message.edit_text("✅ Соглашение принято!\nНапиши /menu")
    await show_main_menu(cb)

@dp.message(Command("menu"))
async def cmd_menu(msg: Message):
    await show_main_menu(msg)

@dp.message(Command("level"))
async def cmd_level(msg: Message):
    await show_level_menu(msg)

@dp.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery):
    await show_main_menu(cb)

@dp.callback_query(F.data == "casino")
async def casino(cb: CallbackQuery):
    await cb.message.edit_text("🎰 Выбери игру:", reply_markup=casino_kb())

@dp.callback_query(F.data.in_(GAMES.keys()))
async def game_info(cb: CallbackQuery, state: FSMContext):
    game = cb.data
    g = GAMES[game]
    u = get_user(cb.from_user.id)
    min_bet, max_bet = get_bet_limits(u["level"])
    text = f"{g['title']}\n\n{g['desc']}\n\nСтавка: {min_bet} — {max_bet} TeX\nШанс победы: ~{int(g['chance']*100)}%"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Поставить ставку", callback_data=f"bet_{game}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]
    ])
    await cb.message.edit_text(text, reply_markup=kb)
    await state.update_data(game=game)

@dp.callback_query(F.data.startswith("bet_"))
async def ask_bet(cb: CallbackQuery, state: FSMContext):
    game = cb.data[4:]
    await state.update_data(game=game)
    u = get_user(cb.from_user.id)
    min_bet, max_bet = get_bet_limits(u["level"])
    await cb.message.edit_text(f"💰 Введи ставку ({min_bet} — {max_bet} TeX):")
    await state.set_state(BetState.waiting_bet)

@dp.message(BetState.waiting_bet)
async def process_bet(msg: Message, state: FSMContext):
    data = await state.get_data()
    game = data["game"]
    u = get_user(msg.from_user.id)
    min_bet, max_bet = get_bet_limits(u["level"])
    try:
        bet = int(msg.text)
        if not min_bet <= bet <= max_bet: raise ValueError
    except:
        await msg.answer(f"❌ От {min_bet} до {max_bet} TeX!")
        return
    if u["balance"] < bet:
        await msg.answer("❌ Недостаточно TeX!")
        await state.clear()
        return
    u["balance"] -= bet
    save_data(users)
    uid = str(msg.from_user.id)
    if game in ["game_coin", "game_highlow", "game_bj", "game_dice", "game_roulette", "game_wheel"]:
        if game == "game_coin":
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🪙 Орёл", callback_data="coin_orol")],[InlineKeyboardButton(text="🪙 Решка", callback_data="coin_reshka")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]])
            await msg.answer("🪙 Выбери сторону:", reply_markup=kb)
            await state.set_state(CoinState.choosing)
            await state.update_data(bet=bet)
        elif game == "game_highlow":
            first = random.randint(2, 14)
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬆️ Выше", callback_data="hl_higher")],[InlineKeyboardButton(text="⬇️ Ниже", callback_data="hl_lower")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]])
            await msg.answer(f"🃏 Первая карта: {first}\nЧто будет следующая?", reply_markup=kb)
            await state.set_state(HighLowState.choosing)
            await state.update_data(first=first, bet=bet)
        elif game == "game_bj":
            player = [random.randint(1,13), random.randint(1,13)]
            dealer_show = random.randint(1,13)
            psum = sum(min(10, c) for c in player)
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🃏 Взять карту", callback_data="bj_hit")],[InlineKeyboardButton(text="✅ Хватит", callback_data="bj_stand")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]])
            await msg.answer(f"🃏 Твои карты: {player} (сумма ≈ {psum})\nДилер показывает: {dealer_show}", reply_markup=kb)
            await state.set_state(BlackjackState.playing)
            await state.update_data(player=player, dealer_show=dealer_show, psum=psum, bet=bet)
        elif game == "game_dice":
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬇️ Меньше 7", callback_data="dice_low")],[InlineKeyboardButton(text="🎯 Ровно 7", callback_data="dice_seven")],[InlineKeyboardButton(text="⬆️ Больше 7", callback_data="dice_high")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]])
            await msg.answer("🎲 Угадай сумму двух кубиков:", reply_markup=kb)
            await state.set_state(DiceState.choosing_sum)
            await state.update_data(bet=bet)
        elif game == "game_roulette":
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔴 Красный", callback_data="roulette_red")],[InlineKeyboardButton(text="⚫ Чёрный", callback_data="roulette_black")],[InlineKeyboardButton(text="🟢 Зелёный", callback_data="roulette_green")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]])
            await msg.answer("🎡 Выбери цвет:", reply_markup=kb)
            await state.update_data(bet=bet)
        elif game == "game_wheel":
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎡 Запустить колесо", callback_data="wheel_spin")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]])
            await msg.answer("🎰 Колесо фортуны\nНажми кнопку ниже!", reply_markup=kb)
            await state.update_data(bet=bet)
    elif game == "game_crash":
        crash_point = round(random.expovariate(0.32) + 0.55, 2)
        if crash_point < 0.51: crash_point = 0.51
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💰 Вывести сейчас", callback_data="crash_cashout")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]])
        game_msg = await msg.answer("💥 CRASH\n\nМножитель: 0.50x\n\nНажимай «Вывести» до краша!", reply_markup=kb)
        active_crashes[uid] = {"bet": bet, "crash_point": crash_point, "current": 0.50, "message": game_msg, "cashed": False}
        asyncio.create_task(run_crash(uid))
        await state.clear()
    else:
        slot_msg = await msg.answer("🎰 <b>Крутим слоты...</b> 🍒", parse_mode="HTML")
        animation_frames = ["🍒 🍋 💎", "7️⃣ 🔔 ⭐", "💰 🔥 🍒", "⭐ 🍒 7️⃣", "💎 🔔 🍋", "🍒 7️⃣ 💰", "🔥 ⭐ 💎", "🔔 🍋 7️⃣"]
        for i, frame in enumerate(animation_frames):
            await asyncio.sleep(0.45)
            prefix = "🎰 Крутим..." if i % 2 == 0 else "🎰 Вращаем..."
            await slot_msg.edit_text(f"{prefix} <b>{frame}</b>", parse_mode="HTML")
        g = GAMES[game]
        win = random.random() < g["chance"]
        prize = int(bet * g["multiplier"]) if win else 0
        slot_symbols = ["🍒", "7️⃣", "💎", "🔔", "⭐"]
        if win:
            sym = random.choice(slot_symbols)
            final_frame = f"{sym} {sym} {sym}"
            u["balance"] += prize
            handle_zero_balance(u)
            result_text = f"🎰 <b>ДЖЕКПОТ!</b>\n{final_frame}\n🎉 +{prize} TeX ({g['multiplier']}x)"
        else:
            while True:
                s1, s2, s3 = random.choices(slot_symbols, k=3)
                if not (s1 == s2 == s3): break
            final_frame = f"{s1} {s2} {s3}"
            result_text = f"🎰 <b>Не повезло...</b>\n{final_frame}\n😢 Ставка проиграна"
        save_data(users)
        await slot_msg.edit_text(result_text, parse_mode="HTML", reply_markup=repeat_back_kb(game))
        await state.clear()

@dp.callback_query(F.data.in_(["coin_orol", "coin_reshka"]))
async def coin_play(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data["bet"]
    choice = "ОРЁЛ" if cb.data == "coin_orol" else "РЕШКА"
    result = random.choice(["ОРЁЛ", "РЕШКА"])
    win = choice == result
    u = get_user(cb.from_user.id)
    if win:
        prize = int(bet * GAMES["game_coin"]["multiplier"])
        u["balance"] += prize
        text = f"🪙 {result}\n🎉 ПОБЕДА! +{prize} TeX ({GAMES['game_coin']['multiplier']}x)"
    else:
        text = f"🪙 {result}\n😢 Проигрыш"
    handle_zero_balance(u)
    save_data(users)
    await cb.message.edit_text(text, reply_markup=repeat_back_kb("game_coin"))
    await state.clear()

@dp.callback_query(F.data.in_(["hl_higher", "hl_lower"]))
async def highlow_play(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    first = data["first"]
    bet = data["bet"]
    second = random.randint(2, 14)
    higher = cb.data == "hl_higher"
    win = (second > first) == higher
    u = get_user(cb.from_user.id)
    if win:
        prize = int(bet * GAMES["game_highlow"]["multiplier"])
        u["balance"] += prize
        text = f"🃏 {first} → {second}\n🎉 ПОБЕДА! +{prize} TeX ({GAMES['game_highlow']['multiplier']}x)"
    else:
        text = f"🃏 {first} → {second}\n😢 Проигрыш"
    handle_zero_balance(u)
    save_data(users)
    await cb.message.edit_text(text, reply_markup=repeat_back_kb("game_highlow"))
    await state.clear()

@dp.callback_query(F.data == "bj_hit")
async def bj_hit(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data["player"]
    player.append(random.randint(1,13))
    psum = sum(min(10, c) for c in player)
    data["player"] = player
    data["psum"] = psum
    await state.set_data(data)
    if psum > 21:
        u = get_user(cb.from_user.id)
        handle_zero_balance(u)
        save_data(users)
        await cb.message.edit_text(f"🃏 Перебор!\nТвои карты: {player} (сумма {psum})\n😢 Проигрыш", reply_markup=repeat_back_kb("game_bj"))
        await state.clear()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🃏 Взять ещё", callback_data="bj_hit")],[InlineKeyboardButton(text="✅ Хватит", callback_data="bj_stand")]])
    await cb.message.edit_text(f"🃏 Ты: {player} (сумма ≈ {psum})\nДилер показывает: {data['dealer_show']}", reply_markup=kb)

@dp.callback_query(F.data == "bj_stand")
async def bj_stand(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player_sum = data["psum"]
    dealer_show = data["dealer_show"]
    dealer = [dealer_show]
    dsum = min(10, dealer_show)
    while dsum < 17:
        card = random.randint(1,13)
        dealer.append(card)
        dsum += min(10, card)
    u = get_user(cb.from_user.id)
    bet = data["bet"]
    if player_sum > 21:
        text = "🃏 Перебор! Проигрыш"
    elif dsum > 21 or player_sum > dsum:
        prize = int(bet * GAMES["game_bj"]["multiplier"])
        u["balance"] += prize
        text = f"🃏 Ты: {player_sum} | Дилер: {dsum}\n🎉 ПОБЕДА! +{prize} TeX ({GAMES['game_bj']['multiplier']}x)"
    else:
        text = f"🃏 Ты: {player_sum} | Дилер: {dsum}\n😢 Проигрыш"
    handle_zero_balance(u)
    save_data(users)
    await cb.message.edit_text(text, reply_markup=repeat_back_kb("game_bj"))
    await state.clear()

@dp.callback_query(F.data.in_(["dice_low", "dice_seven", "dice_high"]))
async def dice_play(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data["bet"]
    d1 = random.randint(1,6)
    d2 = random.randint(1,6)
    total = d1 + d2
    choice = cb.data
    win = False
    if choice == "dice_low" and total < 7: win = True
    elif choice == "dice_seven" and total == 7: win = True
    elif choice == "dice_high" and total > 7: win = True
    u = get_user(cb.from_user.id)
    if win:
        prize = int(bet * GAMES["game_dice"]["multiplier"])
        u["balance"] += prize
        text = f"🎲 {d1} + {d2} = {total}\n🎉 ПОБЕДА! +{prize} TeX ({GAMES['game_dice']['multiplier']}x)"
    else:
        text = f"🎲 {d1} + {d2} = {total}\n😢 Проигрыш"
    handle_zero_balance(u)
    save_data(users)
    await cb.message.edit_text(text, reply_markup=repeat_back_kb("game_dice"))
    await state.clear()

@dp.callback_query(F.data.startswith("roulette_"))
async def roulette_play(cb: CallbackQuery, state: FSMContext):
    color_map = {"roulette_red": "🔴 Красный", "roulette_black": "⚫ Чёрный", "roulette_green": "🟢 Зелёный"}
    choice_name = color_map[cb.data]
    data = await state.get_data()
    bet = data.get("bet", 0)
    await cb.message.edit_text("🎡 Крутим рулетку...")
    await asyncio.sleep(1.8)
    result_name = random.choice(["Красный", "Чёрный", "Зелёный"])
    win = choice_name == result_name
    u = get_user(cb.from_user.id)
    if win:
        prize = int(bet * GAMES["game_roulette"]["multiplier"])
        u["balance"] += prize
        result_text = f"""🎡 Рулетка
Ставка на: {choice_name}
Выигрышный цвет: {result_name}
Результат: 🎉 ПОБЕДА! +{prize} TeX ({GAMES["game_roulette"]["multiplier"]}x)"""
    else:
        result_text = f"""🎡 Рулетка
Ставка на: {choice_name}
Выигрышный цвет: {result_name}
Результат: 😢 Проигрыш"""
    handle_zero_balance(u)
    save_data(users)
    await cb.message.edit_text(result_text, reply_markup=repeat_back_kb("game_roulette"))
    await state.clear()

@dp.callback_query(F.data == "wheel_spin")
async def wheel_play(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get("bet", 0)
    await cb.message.edit_text("🎡 Вращаем колесо...")
    for _ in range(4):
        await asyncio.sleep(0.7)
        await cb.message.edit_text(f"🎡 Вращаем колесо{'.' * ((_ + 1) % 4)}")
    win = random.random() < GAMES["game_wheel"]["chance"]
    u = get_user(cb.from_user.id)
    if win:
        prize = int(bet * GAMES["game_wheel"]["multiplier"])
        u["balance"] += prize
        text = f"🎰 Колесо остановилось!\n🎉 ПОБЕДА! +{prize} TeX ({GAMES['game_wheel']['multiplier']}x)"
    else:
        text = f"🎰 Колесо остановилось!\n😢 Проигрыш"
    handle_zero_balance(u)
    save_data(users)
    await cb.message.edit_text(text, reply_markup=repeat_back_kb("game_wheel"))
    await state.clear()

async def run_crash(uid: str):
    if uid not in active_crashes: return
    data = active_crashes[uid]
    try:
        while not data.get("cashed", False) and data["current"] < data["crash_point"]:
            await asyncio.sleep(0.25)
            increment = round(random.uniform(0.02, 0.11), 2)
            data["current"] = round(data["current"] + increment, 2)
            if data.get("cashed", False): return
            if data["current"] >= data["crash_point"]: break
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"💰 Вывести ({data['current']:.2f}x)", callback_data="crash_cashout")],[InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]])
            try:
                await data["message"].edit_text(f"💥 CRASH\n\nМножитель: {data['current']:.2f}x\n\nВыводи до краша!", reply_markup=kb)
            except: return
        if data.get("cashed", False): return
        u = get_user(int(uid))
        text = f"💥 КРАШ на {data['crash_point']:.2f}x!\n😢 Проигрыш {data['bet']} TeX"
        try:
            await data["message"].edit_text(text, reply_markup=repeat_back_kb("game_crash"))
        except: pass
    finally:
        active_crashes.pop(uid, None)

@dp.callback_query(F.data == "crash_cashout")
async def crash_cashout(cb: CallbackQuery):
    uid = str(cb.from_user.id)
    if uid not in active_crashes: return
    data = active_crashes[uid]
    if data.get("cashed", False): return
    data["cashed"] = True
    current = data["current"]
    prize = int(data["bet"] * current)
    u = get_user(cb.from_user.id)
    u["balance"] += prize
    handle_zero_balance(u)
    save_data(users)
    text = f"✅ ВЫВЕДЕНО на {current:.2f}x\n🎉 +{prize} TeX ({current:.2f}x)"
    try:
        await cb.message.edit_text(text, reply_markup=repeat_back_kb("game_crash"))
    except: pass
    active_crashes.pop(uid, None)

@dp.callback_query(F.data == "pets")
async def pets_shop(cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    await cb.message.edit_text("🐾 Магазин питомцев Texarnia!\n💰 Прибыль каждые 30 минут", reply_markup=pet_shop_kb(u))

@dp.callback_query(F.data.startswith("buy_pet_"))
async def buy_pet(cb: CallbackQuery):
    idx = int(cb.data[8:])
    name, earn, req, price = PETS[idx]
    u = get_user(cb.from_user.id)
    if u["level"] < req: await cb.answer("❌ Уровень слишком маленький!", show_alert=True); return
    if name in u.get("pets", {}): await cb.answer("У тебя уже есть этот питомец!", show_alert=True); return
    if u["balance"] < price: await cb.answer("❌ Недостаточно TeX!", show_alert=True); return
    u["balance"] -= price
    handle_zero_balance(u)
    now = datetime.now()
    minutes = now.minute
    if minutes < 30:
        rounded = now.replace(minute=0, second=0, microsecond=0)
    else:
        rounded = now.replace(minute=30, second=0, microsecond=0)
    u.setdefault("pets", {})[name] = {"earn": earn, "last_collect_time": rounded.isoformat()}
    u["last_collect_time"] = now.isoformat()
    u["notify_sent"] = False
    save_data(users)
    await cb.message.edit_text(f"✅ Куплен {name}!", reply_markup=pet_shop_kb(u))

def perform_collect(u):
    total = 0
    now = datetime.now()
    mult = get_pet_multiplier(u["level"])
    for pet in u.get("pets", {}).values():
        last = datetime.fromisoformat(pet.get("last_collect_time", now.isoformat()))
        minutes_passed = (now - last).total_seconds() / 60
        intervals = int(minutes_passed // 30)
        if intervals > 0:
            total += int(pet["earn"] * mult * intervals)
            pet["last_collect_time"] = (last + timedelta(minutes=30 * intervals)).isoformat()
    return total

@dp.callback_query(F.data == "collect")
async def collect_pets(cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    total = perform_collect(u)
    u["balance"] += total
    handle_zero_balance(u)
    u["last_collect_time"] = datetime.now().isoformat()
    u["notify_sent"] = False
    save_data(users)
    await cb.answer(f"💰 Собрано {total} TeX!", show_alert=True)
    await cb.message.edit_text("🐾 Магазин питомцев Texarnia!", reply_markup=pet_shop_kb(u))

@dp.message(Command("collect"))
async def collect_cmd(msg: Message):
    u = get_user(msg.from_user.id)
    total = perform_collect(u)
    u["balance"] += total
    handle_zero_balance(u)
    u["last_collect_time"] = datetime.now().isoformat()
    u["notify_sent"] = False
    save_data(users)
    await msg.answer(f"💰 Собрано {total} TeX!")

@dp.message(Command("mypet"))
async def mypet(msg: Message):
    u = get_user(msg.from_user.id)
    mult = get_pet_multiplier(u["level"])
    buff_pct = int((mult - 1) * 100)
    lines = [f"• {n} — {int(d['earn'] * mult)} TeX/30мин" for n, d in u.get("pets", {}).items()]
    pets_text = "\n".join(lines) or "• Нет питомцев"
    extra = f"\n📈 Бафф от уровня: +{buff_pct}% к прибыли всех питомцев" if buff_pct > 0 else ""
    await msg.answer(f"🐾 **Твои питомцы:**\n{pets_text}{extra}")

@dp.message(Command("rehex"))
async def rehex_cmd(msg: Message):
    u = get_user(msg.from_user.id)
    current_cost = u.get("rehex_cost", 10000)
    if u["balance"] < current_cost:
        await msg.answer(f"❌ Нужно {current_cost} TeX для смены HEX!")
        return
    existing = {data["hex"] for data in users.values()}
    new_hex = ''.join(random.choices(string.ascii_lowercase, k=6))
    while new_hex in existing:
        new_hex = ''.join(random.choices(string.ascii_lowercase, k=6))
    u["balance"] -= current_cost
    old_hex = u["hex"]
    u["hex"] = new_hex
    u["rehex_count"] = u.get("rehex_count", 0) + 1
    if u["rehex_count"] % 3 == 0:
        u["rehex_cost"] = current_cost + 1000
    handle_zero_balance(u)
    save_data(users)
    await msg.answer(f"✅ HEX обновлён!\nСтарый: {old_hex}\nНовый: {new_hex}\nСписано: {current_cost} TeX\nСледующая смена будет стоить: {u['rehex_cost']} TeX")

@dp.message(Command("top"))
async def top_cmd(msg: Message):
    await msg.answer("Загрузка топа...")
    rebuild_top()
    args = msg.text.lower().split()
    if len(args) > 1 and args[1] == "lt":
        table = "🏆 ТОП-15 ПО УРОВНЯМ\n\n"
        for entry in top_cache["level"]:
            table += f"{entry['place']}. {entry['username']} — lvl {entry['level']} (баланс {entry['balance']})\n"
    else:
        table = "🏆 ТОП-15 ПО ДЕНЬГАМ\n\n"
        for entry in top_cache["money"]:
            table += f"{entry['place']}. {entry['username']} — {entry['balance']} TeX (lvl {entry['level']})\n"
    uid = str(msg.from_user.id)
    my_place = next((i+1 for i,(k,v) in enumerate(sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)) if k == uid), ">15")
    table += f"\nТвоё место: {my_place}\n\n💡 Используй:\n/top — топ по деньгам\n/top lt — топ по уровням"
    await msg.answer(f"<pre>{table}</pre>", parse_mode="HTML")

@dp.message(Command("bonuska"))
async def bonuska_cmd(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    try:
        _, amount_str, hex_code = msg.text.split(maxsplit=2)
        amount = int(amount_str)
        for uid, data in users.items():
            if data.get("hex") == hex_code:
                data["balance"] += amount
                handle_zero_balance(data)
                save_data(users)
                await msg.answer(f"✅ Добавлено {amount} TeX пользователю с HEX {hex_code}\nНовый баланс: {data['balance']}")
                return
        await msg.answer("❌ HEX не найден")
    except:
        await msg.answer("❌ Использование: /bonuska <сумма> <hex>")

@dp.message(Command("bonuska-"))
async def bonuska_minus_cmd(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    try:
        _, amount_str, hex_code = msg.text.split(maxsplit=2)
        amount = int(amount_str)
        for uid, data in users.items():
            if data.get("hex") == hex_code:
                data["balance"] -= amount
                handle_zero_balance(data)
                save_data(users)
                await msg.answer(f"✅ Отобрано {amount} TeX у HEX {hex_code}\nНовый баланс: {data['balance']}")
                return
        await msg.answer("❌ HEX не найден")
    except:
        await msg.answer("❌ Использование: /bonuska- <сумма> <hex>")

@dp.message(Command("reteik"))
async def reteik_start(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    try:
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            await msg.answer("❌ Использование: /reteik <hex>")
            return
        hex_code = parts[1].strip()
        pending_reteik[msg.from_user.id] = hex_code
        await msg.answer(f"✅ HEX принят.\nТеперь отправь сообщение (текст/фото/видео/стикер) — оно сразу будет переслано пользователю.")
    except:
        await msg.answer("❌ Ошибка команды")

@dp.message(Command("broad"))
async def broad_start(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    pending_broad[msg.from_user.id] = True
    await msg.answer("📢 Напишите сообщение для рассылки (текст, фото, видео, файл, стикер):")

@dp.callback_query(F.data == "support")
async def support_start(cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    if time.time() < u.get("support_cd", 0):
        await cb.answer("⏳ Техподдержка доступна раз в час!", show_alert=True)
        return
    pending_support[cb.from_user.id] = True
    await cb.message.edit_text("✍️ Напиши сообщение (25-400 символов):")

@dp.message()
async def pending_handler(msg: Message):
    uid = msg.from_user.id
    if uid in pending_support:
        del pending_support[uid]
        if not 25 <= len(msg.text) <= 400:
            await msg.answer("❌ Длина сообщения должна быть от 25 до 400 символов!")
            pending_support[uid] = True
            return
        u = get_user(uid)
        u["support_cd"] = time.time() + 3600
        save_data(users)
        await bot.send_message(ADMIN_ID, f"📩 Пользователь: @{msg.from_user.username or 'нет'}\nHEX: {u['hex']}\nСообщение: {msg.text}\n\nОтветь: /reteik {u['hex']}")
        await msg.answer("✅ Спасибо! Администратор скоро ответит.")
        return
    if uid in pending_broad:
        del pending_broad[uid]
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Принять и разослать", callback_data="broad_accept")],[InlineKeyboardButton(text="❌ Отклонить", callback_data="broad_reject")]])
        await bot.copy_message(chat_id=uid, from_chat_id=msg.chat.id, message_id=msg.message_id, reply_markup=kb)
        await msg.answer("👆 Это как увидят пользователи.\nВыбери действие на кнопках выше.")
        return
    if uid == ADMIN_ID and uid in pending_reteik:
        hex_code = pending_reteik.pop(uid)
        sent = False
        for user_id, data in users.items():
            if data.get("hex") == hex_code:
                try:
                    await bot.copy_message(chat_id=int(user_id), from_chat_id=msg.chat.id, message_id=msg.message_id)
                    await msg.answer("✅ Сообщение успешно отправлено пользователю!")
                    sent = True
                except Exception as e:
                    await msg.answer(f"❌ Не удалось отправить: {str(e)}")
                break
        if not sent:
            await msg.answer("❌ HEX не найден")
        return

@dp.callback_query(F.data == "broad_accept")
async def broad_accept(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    orig_chat = cb.message.chat.id
    orig_msg = cb.message.message_id
    count = 0
    for user_id in list(users.keys()):
        try:
            await bot.copy_message(chat_id=int(user_id), from_chat_id=orig_chat, message_id=orig_msg)
            count += 1
        except:
            pass
    await cb.message.edit_text(f"✅ Рассылка завершена!\nОтправлено {count} пользователям.")

@dp.callback_query(F.data == "broad_reject")
async def broad_reject(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    await cb.message.edit_text("❌ Рассылка отменена.")

@dp.callback_query(F.data == "help")
async def help_cmd(cb: CallbackQuery):
    text = """📜 Команды:
1. /menu — Главное меню
2. /level — Меню прокачки
3. /collect — Собрать с питомцев
4. /mypet — Твои питомцы
5. /top — Топ 15
6. /rehex — Сменить HEX"""
    await cb.message.edit_text(text, reply_markup=back_main_kb())

@dp.callback_query(F.data == "donate")
async def donate(cb: CallbackQuery):
    await cb.message.edit_text("⭐ Донат Звёздами:\nОтправь любой подарок @maryf_do1\nВ описании укажи HEX\n1 звезда = 300 TeX", reply_markup=back_main_kb())

@dp.callback_query(F.data == "upgrade_level")
async def upgrade_level(cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    cost = get_next_level_cost(u["level"])
    if u["balance"] < cost:
        await cb.answer("❌ Недостаточно TeX!", show_alert=True)
        return
    u["balance"] -= cost
    u["level"] += 1
    handle_zero_balance(u)
    save_data(users)
    await cb.answer(f"✅ Уровень повышен до {u['level']}!", show_alert=True)
    await show_level_menu(cb)

@dp.message(F.text.startswith("/"))
async def unknown_command(msg: Message):
    await msg.answer("❌ Неизвестная команда!\n\nИспользуй /menu")

async def check_zero_bonuses():
    changed = False
    for uid, u in list(users.items()):
        old = u.get("zero_bonus_end", 0)
        handle_zero_balance(u)
        if old and time.time() >= old and u["balance"] <= 0 and not u.get("zero_bonus_end"):
            u["balance"] += 100
            handle_zero_balance(u)
            changed = True
            try:
                await bot.send_message(int(uid), "💰 Ты получил +100 TeX за нулевой баланс!")
            except:
                pass
    if changed:
        save_data(users)

async def pet_notify_job():
    now = datetime.now()
    changed = False
    for uid_str, u in list(users.items()):
        if not u.get("pets"): continue
        last_str = u.get("last_collect_time")
        if not last_str: continue
        last_c = datetime.fromisoformat(last_str)
        if (now - last_c).total_seconds() >= 1800 and not u.get("notify_sent", False):
            try:
                await bot.send_message(int(uid_str), "🐾 Питомцы заработали!\nЗабери скорее /collect")
                u["notify_sent"] = True
                changed = True
            except:
                pass
    if changed:
        save_data(users)

async def main():
    print("Бот запущен")
    scheduler.add_job(check_zero_bonuses, 'interval', minutes=1)
    scheduler.add_job(pet_notify_job, 'interval', minutes=5)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
