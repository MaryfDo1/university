import asyncio
import json
import os
import random
import string
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "8595080357:AAHMCIjzaLAEzBL0abnID4TndUwMFqBp4E8"
ADMIN_ID = 2109352567
DATA_FILE = "users.json"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

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

class SupportState(StatesGroup):
    waiting_text = State()

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users = load_data()

def get_hex():
    return ''.join(random.choices(string.ascii_lowercase, k=6))

def get_user(user_id):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "username": "", "balance": 50, "level": 1, "hex": get_hex(),
            "pets": {}, "support_cd": 0, "agreed": False, "zero_bonus_end": 0
        }
        save_data(users)
    return users[uid]

def handle_zero_balance(u):
    if u["balance"] > 0:
        u.pop("zero_bonus_end", None)
    elif u["balance"] <= 0 and u.get("zero_bonus_end", 0) == 0:
        u["zero_bonus_end"] = time.time() + 1800

PETS = [
    ("🐱 TexCat", 8, 1, 100), ("🐶 GoldDog", 13, 1, 150), ("🐦 SkyBird", 19, 1, 225),
    ("🐟 AquaFish", 29, 1, 338), ("🦋 LuckyButterfly", 44, 1, 507),
    ("🐉 FireDragon", 66, 5, 760), ("🦅 EagleTex", 99, 5, 1140), ("🐺 ShadowWolf", 148, 5, 1710),
    ("🐘 BigElephant", 222, 5, 2565), ("🦒 TallGiraffe", 333, 5, 3848),
    ("🦄 MagicUnicorn", 500, 10, 5772), ("🐲 GoldenDragon", 750, 10, 8658),
    ("🦁 KingLion", 1125, 10, 12987), ("🐼 PandaTex", 1688, 10, 19480), ("🐯 TigerKing", 2532, 10, 29220)
]

GAMES = {
    "game_slots":    {"title": "🎰 Слоты",     "desc": "Три одинаковых символа = победа.", "chance": 0.28, "multiplier": 4.0},
    "game_roulette": {"title": "🎡 Рулетка",   "desc": "Угадай цвет.", "chance": 0.35, "multiplier": 3.2},
    "game_bj":       {"title": "🃏 Блэкджек",  "desc": "Набери ближе к 21.", "chance": 0.42, "multiplier": 2.5},
    "game_coin":     {"title": "🪙 Монетка",   "desc": "Орёл или решка.", "chance": 0.50, "multiplier": 2.0},
    "game_dice":     {"title": "🎲 Кубики",    "desc": "Угадай сумму двух кубиков.", "chance": 0.33, "multiplier": 3.5},
    "game_highlow":  {"title": "⬆️ Выше/Ниже","desc": "Следующая карта выше или ниже?", "chance": 0.40, "multiplier": 2.8},
    "game_crash":    {"title": "💥 Crash",     "desc": "Выводи до краша.", "chance": 0.30, "multiplier": 4.5},
    "game_wheel":    {"title": "🎰 Wheel",     "desc": "Колесо фортуны.", "chance": 0.32, "multiplier": 4.0}
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
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
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

async def show_main_menu(obj):
    uid = str(obj.from_user.id)
    u = get_user(uid)
    u["username"] = obj.from_user.username or "нет"
    handle_zero_balance(u)
    sorted_users = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)
    place = next((i+1 for i,(k,v) in enumerate(sorted_users) if k == uid), 16)
    top_text = ">" if place > 15 else str(place)
    text = f"""👤 Ник: @{u['username']}
💰 Баланс: {u['balance']} TeX
🏆 Уровень: {u['level']}
📊 Уровень в топе: {top_text}
🔑 HEX: {u['hex']}"""
    kb = main_menu_kb()
    if isinstance(obj, CallbackQuery):
        await obj.message.edit_text(text, reply_markup=kb)
    else:
        await obj.answer(text, reply_markup=kb)
    save_data(users)

@dp.message(Command("start"))
async def start(msg: Message):
    u = get_user(msg.from_user.id)
    if not u["agreed"]:
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
    text = f"{g['title']}\n\n{g['desc']}\n\nСтавка: 15-250 TeX\nШанс победы: ~{int(g['chance']*100)}%"
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
    await cb.message.edit_text("💰 Введи ставку (15-250 TeX):")
    await state.set_state(BetState.waiting_bet)

@dp.message(BetState.waiting_bet)
async def process_bet(msg: Message, state: FSMContext):
    try:
        bet = int(msg.text)
        if not 15 <= bet <= 250:
            raise ValueError
    except:
        await msg.answer("❌ От 15 до 250 TeX!")
        return

    data = await state.get_data()
    game = data["game"]
    u = get_user(msg.from_user.id)
    if u["balance"] < bet:
        await msg.answer("❌ Недостаточно TeX!")
        await state.clear()
        return

    u["balance"] -= bet
    save_data(users)

    # Интерактивные игры
    if game in ["game_coin", "game_highlow", "game_bj", "game_dice"]:
        if game == "game_coin":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🪙 Орёл", callback_data="coin_orol")],
                [InlineKeyboardButton(text="🪙 Решка", callback_data="coin_reshka")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]
            ])
            await msg.answer("Выбери сторону:", reply_markup=kb)
            await state.set_state(CoinState.choosing)
            await state.update_data(bet=bet)

        elif game == "game_highlow":
            first = random.randint(2, 14)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Выше ↑", callback_data="hl_higher")],
                [InlineKeyboardButton(text="Ниже ↓", callback_data="hl_lower")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]
            ])
            await msg.answer(f"Карта: {first}\nЧто дальше?", reply_markup=kb)
            await state.set_state(HighLowState.choosing)
            await state.update_data(first=first, bet=bet)

        elif game == "game_bj":
            player = [random.randint(1,13), random.randint(1,13)]
            dealer_show = random.randint(1,13)
            psum = sum(min(10, c) for c in player)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Взять", callback_data="bj_hit")],
                [InlineKeyboardButton(text="Хватит", callback_data="bj_stand")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]
            ])
            await msg.answer(f"Ты: {player} (~{psum})\nДилер показывает: {dealer_show}", reply_markup=kb)
            await state.set_state(BlackjackState.playing)
            await state.update_data(player=player, dealer_show=dealer_show, psum=psum, bet=bet)

        elif game == "game_dice":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Меньше 7", callback_data="dice_low")],
                [InlineKeyboardButton(text="Ровно 7", callback_data="dice_seven")],
                [InlineKeyboardButton(text="Больше 7", callback_data="dice_high")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="casino")]
            ])
            await msg.answer("Угадай сумму двух кубиков:", reply_markup=kb)
            await state.set_state(DiceState.choosing_sum)
            await state.update_data(bet=bet)

    else:
        # Быстрые игры
        await msg.answer("⏳ Идет игра...")
        await asyncio.sleep(1.5)
        g = GAMES[game]
        win = random.random() < g["chance"]
        prize = int(bet * g["multiplier"]) if win else 0
        if win:
            u["balance"] += prize
            handle_zero_balance(u)
            text = f"🎉 ПОБЕДА! +{prize} TeX ({g['multiplier']}x)"
        else:
            text = "😢 Проигрыш..."
        save_data(users)
        await msg.answer(text, reply_markup=repeat_back_kb(game))
        await state.clear()

# Обработчики интерактивных игр (callback)

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
        text = f"🪙 {result}!\n🎉 ПОБЕДА! +{prize} TeX"
    else:
        text = f"🪙 {result}...\n😢 Проигрыш"
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
        text = f"{first} → {second}\n🎉 ПОБЕДА! +{prize} TeX"
    else:
        text = f"{first} → {second}\n😢 Проигрыш"
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
        u["balance"] -= data["bet"]
        handle_zero_balance(u)
        save_data(users)
        await cb.message.edit_text(f"Ты: {player} → {psum} (перебор)\n😢 Проигрыш", reply_markup=repeat_back_kb("game_bj"))
        await state.clear()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Взять ещё", callback_data="bj_hit")],
        [InlineKeyboardButton(text="Хватит", callback_data="bj_stand")],
    ])
    await cb.message.edit_text(f"Ты: {player} (~{psum})\nДилер: {data['dealer_show']} ?", reply_markup=kb)

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
        u["balance"] -= bet
        text = "Перебор! Проигрыш"
    elif dsum > 21 or player_sum > dsum:
        prize = int(bet * GAMES["game_bj"]["multiplier"])
        u["balance"] += prize - bet
        text = f"Ты ~{player_sum} | Дилер ~{dsum}\n🎉 ПОБЕДА! +{prize-bet} TeX"
    else:
        u["balance"] -= bet
        text = f"Ты ~{player_sum} | Дилер ~{dsum}\n😢 Проигрыш"
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
        text = f"🎲{d1} + 🎲{d2} = {total}\n🎉 ПОБЕДА! +{prize} TeX"
    else:
        text = f"🎲{d1} + 🎲{d2} = {total}\n😢 Проигрыш"
    handle_zero_balance(u)
    save_data(users)
    await cb.message.edit_text(text, reply_markup=repeat_back_kb("game_dice"))
    await state.clear()

# Остальной код (питомцы, поддержка, команды, уведомления) без изменений

@dp.callback_query(F.data == "pets")
async def pets_shop(cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    await cb.message.edit_text("🐾 Магазин питомцев Texarnia!\n💰 Прибыль каждые 30 мин (макс 3 часа)", reply_markup=pet_shop_kb(u))

@dp.callback_query(F.data.startswith("buy_pet_"))
async def buy_pet(cb: CallbackQuery):
    idx = int(cb.data[8:])
    name, earn, req, price = PETS[idx]
    u = get_user(cb.from_user.id)
    if name in u.get("pets", {}):
        await cb.answer("У тебя уже есть этот питомец!", show_alert=True)
        return
    if u["balance"] < price:
        await cb.answer("❌ Недостаточно TeX!", show_alert=True)
        return
    u["balance"] -= price
    handle_zero_balance(u)
    u.setdefault("pets", {})[name] = {"earn": earn, "last_collect": datetime.now().isoformat()}
    save_data(users)
    await cb.message.edit_text(f"✅ Куплен {name}!", reply_markup=pet_shop_kb(u))

@dp.callback_query(F.data == "collect")
async def collect_pets(cb: CallbackQuery):
    u = get_user(cb.from_user.id)
    total = 0
    now = datetime.now()
    for pet in u.get("pets", {}).values():
        last = datetime.fromisoformat(pet["last_collect"])
        hours = min((now - last).total_seconds() / 3600, 3.0)
        total += int(pet["earn"] * hours * 2)
        pet["last_collect"] = now.isoformat()
    u["balance"] += total
    handle_zero_balance(u)
    save_data(users)
    await cb.answer(f"💰 Собрано {total} TeX!", show_alert=True)
    await cb.message.edit_text("🐾 Магазин питомцев Texarnia!", reply_markup=pet_shop_kb(u))

@dp.callback_query(F.data == "support")
async def support_start(cb: CallbackQuery, state: FSMContext):
    u = get_user(cb.from_user.id)
    if time.time() < u.get("support_cd", 0):
        await cb.answer("⏳ Техподдержка доступна раз в час!", show_alert=True)
        return
    await cb.message.edit_text("✍️ Напиши сообщение (25-400 символов):")
    await state.set_state(SupportState.waiting_text)

@dp.message(SupportState.waiting_text)
async def support_send(msg: Message, state: FSMContext):
    if not 25 <= len(msg.text) <= 400:
        return await msg.answer("❌ Длина сообщения должна быть от 25 до 400 символов!")
    u = get_user(msg.from_user.id)
    u["support_cd"] = time.time() + 3600
    save_data(users)
    await bot.send_message(ADMIN_ID, f"📩 Пользователь: @{msg.from_user.username}\nHEX: {u['hex']}\nСообщение: {msg.text}\n\nОтветь: /reteik {u['hex']} <текст>")
    await msg.answer("✅ Спасибо! Администратор скоро ответит.")
    await state.clear()

@dp.message(Command("reteik"))
async def admin_reply(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    try:
        parts = msg.text.split(maxsplit=2)
        hex_code = parts[1]
        reply_text = parts[2]
        for uid, data in users.items():
            if data.get("hex") == hex_code:
                await bot.send_message(int(uid), f"📨 Ответ от администрации:\n{reply_text}")
                return
    except:
        pass

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
                await msg.answer(f"✅ Добавлено {amount} TeX пользователю с HEX {hex_code}")
                return
        await msg.answer("❌ HEX не найден")
    except:
        await msg.answer("❌ Использование: /bonuska <сумма> <hex>")

@dp.callback_query(F.data == "help")
async def help_cmd(cb: CallbackQuery):
    text = """📜 Команды:
1. /menu — Главное меню
2. /collect — Собрать с питомцев
3. /mypet — Твои питомцы
4. /top — Топ 15"""
    await cb.message.edit_text(text, reply_markup=back_main_kb())

@dp.callback_query(F.data == "donate")
async def donate(cb: CallbackQuery):
    await cb.message.edit_text("⭐ Донат Звёздами:\nОтправь любой подарок @maryf_do1\nВ описании укажи HEX\n1 звезда = 300 TeX", reply_markup=back_main_kb())

@dp.message(Command("collect"))
async def cmd_collect(msg: Message):
    u = get_user(msg.from_user.id)
    total = 0
    now = datetime.now()
    for pet in u.get("pets", {}).values():
        last = datetime.fromisoformat(pet["last_collect"])
        hours = min((now - last).total_seconds() / 3600, 3.0)
        total += int(pet["earn"] * hours * 2)
        pet["last_collect"] = now.isoformat()
    u["balance"] += total
    handle_zero_balance(u)
    save_data(users)
    await msg.answer(f"💰 Собрано {total} TeX!")

@dp.message(Command("mypet"))
async def mypet(msg: Message):
    u = get_user(msg.from_user.id)
    pets = "\n".join([f"{n} — {d['earn']} TeX/30мин" for n,d in u.get("pets", {}).items()]) or "Нет питомцев"
    await msg.answer(f"🐾 Твои питомцы:\n{pets}")

@dp.message(Command("top"))
async def top_cmd(msg: Message):
    sorted_users = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)[:15]
    table = "🏆 ТОП-15\n\n"
    for i, (_, u) in enumerate(sorted_users, 1):
        table += f"{i}. @{u.get('username','—')} — {u['balance']} TeX (lvl {u['level']})\n"
    my_place = next((i+1 for i,(uid,u) in enumerate(sorted(users.items(), key=lambda x:x[1]["balance"], reverse=True)) if uid==str(msg.from_user.id)), ">15")
    table += f"\nТвоё место: {my_place}"
    await msg.answer(f"<pre>{table}</pre>", parse_mode="HTML")

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

async def hourly_notify():
    while True:
        await asyncio.sleep(3600)
        for uid, u in list(users.items()):
            if u.get("pets"):
                try:
                    await bot.send_message(int(uid), "🐾 Питомцы заработали деньжат! Зайди скорее! 💰")
                except:
                    pass

async def main():
    print("Бот запущен - Можно и поесть!")
    scheduler.add_job(check_zero_bonuses, 'interval', minutes=1)
    scheduler.add_job(hourly_notify, 'interval', seconds=3600)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
