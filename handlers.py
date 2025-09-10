import logging
import sqlite3
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import EVENT_DAYS, TOKEN, PODCAST_URL
from db import get_user, create_user, update_points, add_reward, get_profile, DB_FILE
from states import Day1States
from texts import DISC_PROFILES, DISC_COMBOS, FUN_ARCHETYPES, MOTIVATIONALS, SERIOUS_INTRO, FUN_INTRO

router = Router()
logging.basicConfig(level=logging.INFO)

# Админские Telegram ID — замени на свои
ADMINS = {11927166}

# Текущий день, для тестирования (по реальной дате можно сделать расширение)
current_day = 1

# === Вопросы серьёзного теста DiSC (пример, добавь все свои) ===
DISC_QUESTIONS = [
    {"type": "slider", "text": "Когда нужно принять решение в работе, ты…", "left": "сначала собираю все факты и анализирую",
     "right": "принимаю быстро и действую", "cat_l": "C", "cat_r": "D"},
    {"type": "slider", "text": "На совещании ты чаще...", "left": "внимательно слушаю и поддерживаю коллег",
     "right": "весело вдохновляю и предлагаю идеи", "cat_l": "S", "cat_r": "i"},
    # Добавь остальные вопросы...
]

# === Помощь — подсчёт очков ===
def disc_slider_scores(pos, cat_l, cat_r):
    return {cat_l: 6 - pos, cat_r: pos}

def disc_mc_scores(selected, options):
    cats = [opt[1] for opt in options]
    scores = {c: 1 for c in cats}
    scores[cats[selected]] += 4
    return scores

def disc_assoc_scores(selected, cats):
    scores = {c: 1 for c in cats}
    scores[cats[selected]] += 4
    return scores

# === Вспомогательная функция проверки админа ===
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

# === Отправка следующего вопроса с удалением предыдующего ===
async def ask_next_disc_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    qidx = data.get("disc_q", 0)
    chat_id = message.chat.id

    # Удаляем предыдущее сообщение вопроса
    last_msg_id = data.get("last_question_message_id")
    if last_msg_id:
        try:
            await message.bot.delete_message(chat_id, last_msg_id)
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение: {e}")

    if qidx >= len(DISC_QUESTIONS):
        await message.answer("Тест завершён!")
        await state.clear()
        return

    q = DISC_QUESTIONS[qidx]
    text = f"Вопрос {qidx + 1}/{len(DISC_QUESTIONS)}\n{q['text']}"

    if q["type"] == "slider":
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=f"{q['left']} (1)", callback_data="slider:1")],
                [types.InlineKeyboardButton(text="2", callback_data="slider:2")],
                [types.InlineKeyboardButton(text="3", callback_data="slider:3")],
                [types.InlineKeyboardButton(text="4", callback_data="slider:4")],
                [types.InlineKeyboardButton(text=f"{q['right']} (5)", callback_data="slider:5")],
            ]
        )
    elif q["type"] == "mc":
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=opt[0], callback_data=f"mc:{i}") for i, opt in enumerate(q["options"])]
            ]
        )
    elif q["type"] == "assoc":
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=icon, callback_data=f"assoc:{i}") for i, icon in enumerate(q["icons"])]
            ]
        )
    else:
        keyboard = None

    sent_msg = await message.answer(text, reply_markup=keyboard)
    await state.update_data(last_question_message_id=sent_msg.message_id)

# === Обработчики ответов на слайдер ===
@router.callback_query(Day1States.SERIOUS_TEST, F.data.regexp(r"slider:\d"))
async def handle_slider_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    qidx = data.get("disc_q", 0)
    if qidx >= len(DISC_QUESTIONS):
        await callback.answer("Тест завершён.")
        return
    q = DISC_QUESTIONS[qidx]

    if q["type"] != "slider":
        await callback.answer("Некорректный тип вопроса")
        return

    pos = int(callback.data.split(":")[1])
    scores = data.get("disc_scores", {"D": 0, "i": 0, "S": 0, "C": 0})

    for k, v in disc_slider_scores(pos, q["cat_l"], q["cat_r"]).items():
        scores[k] = scores.get(k, 0) + v

    await state.update_data(disc_scores=scores, disc_q=qidx + 1)
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

# === Обработчики ответов для множественного выбора ===
@router.callback_query(Day1States.SERIOUS_TEST, F.data.regexp(r"mc:\d"))
async def handle_mc_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    qidx = data.get("disc_q", 0)
    if qidx >= len(DISC_QUESTIONS):
        await callback.answer("Тест завершён.")
        return
    q = DISC_QUESTIONS[qidx]

    if q["type"] != "mc":
        await callback.answer("Некорректный тип вопроса")
        return

    sel = int(callback.data.split(":")[1])
    scores = data.get("disc_scores", {"D": 0, "i": 0, "S": 0, "C": 0})

    cat_update = disc_mc_scores(sel, q["options"])
    for k, v in cat_update.items():
        scores[k] = scores.get(k, 0) + v

    await state.update_data(disc_scores=scores, disc_q=qidx + 1)
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

# === Обработчики ответов для ассоциаций ===
@router.callback_query(Day1States.SERIOUS_TEST, F.data.regexp(r"assoc:\d"))
async def handle_assoc_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    qidx = data.get("disc_q", 0)
    if qidx >= len(DISC_QUESTIONS):
        await callback.answer("Тест завершён.")
        return
    q = DISC_QUESTIONS[qidx]

    if q["type"] != "assoc":
        await callback.answer("Некорректный тип вопроса")
        return

    sel = int(callback.data.split(":")[1])
    scores = data.get("disc_scores", {"D": 0, "i": 0, "S": 0, "C": 0})

    cat_update = disc_assoc_scores(sel, q["cats"])
    for k, v in cat_update.items():
        scores[k] = scores.get(k, 0) + v

    await state.update_data(disc_scores=scores, disc_q=qidx + 1)
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

# === Админ команды ===

@router.message(Command("addpoints"))
async def cmd_add_points(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Только для админов.")
        return
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Использование: /addpoints <user_id> <points>")
        return
    try:
        user_id = int(args[1])
        points = int(args[2])
    except ValueError:
        await message.answer("Неверные аргументы.")
        return
    if not get_user(user_id):
        await message.answer("Пользователь не найден.")
        return
    update_points(user_id, points)
    await message.answer(f"Начислено {points} баллов пользователю {user_id}.")

@router.message(Command("skipday"))
async def cmd_skip_day(message: types.Message):
    global current_day
    if not is_admin(message.from_user.id):
        await message.answer("Только для админов.")
        return
    if current_day < EVENT_DAYS:
        current_day +=1
        await message.answer(f"Переход на следующий день: День {current_day}")
    else:
        await message.answer("Максимальный день достигнут.")

@router.message(Command("setday"))
async def cmd_set_day(message: types.Message):
    global current_day
    if not is_admin(message.from_user.id):
        await message.answer("Только для админов.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /setday <номер_дня>")
        return
    try:
        day = int(args[1])
    except ValueError:
        await message.answer("День должен быть числом.")
        return
    if 1 <= day <= EVENT_DAYS:
        current_day = day
        await message.answer(f"День установлен: {current_day}")
    else:
        await message.answer(f"День должен быть в диапазоне 1-{EVENT_DAYS}.")

@router.message(Command("resetdb"))
async def cmd_reset_db(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Только для админов.")
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    await message.answer("База пользователей очищена.")

@router.message(Command("userstats"))
async def cmd_user_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Только для админов.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /userstats <user_id>")
        return
    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    profile = get_profile(user_id)
    if profile is None:
        await message.answer("Пользователь не найден.")
        return
    rewards = ', '.join(profile['rewards']) or "Нет наград"
    await message.answer(f"Профиль {user_id}:\nБаллы: {profile['points']}\nНаграды: {rewards}")

# Помощь
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS
