import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import EVENT_DAYS, ADMINS
from db import get_user, update_points, get_profile
from texts import DISC_QUESTIONS
from commands import USER_COMMANDS_TEXT, ADMIN_COMMANDS_TEXT
from states import Day1States

router = Router()
logging.basicConfig(level=logging.INFO)

current_day_global = 1  # активный день

# ===== Вспомогательные =====

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def main_menu_kb() -> types.ReplyKeyboardMarkup:
    buttons = [
        [types.KeyboardButton(text="Начать день")],
        [types.KeyboardButton(text="Профиль"), types.KeyboardButton(text="Помощь")],
    ]
    return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def day1_mode_kb() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Ты на работе (серьёзный тест)", callback_data="day1:serious")],
        [types.InlineKeyboardButton(text="Твоё Альтер-эго (шуточный тест)", callback_data="day1:fun_soon")],
        [types.InlineKeyboardButton(text="В главное меню", callback_data="nav:main")],
    ])

def back_to_menu_inline() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="В главное меню", callback_data="nav:main")]
    ])

async def to_main_menu(message: types.Message):
    await message.answer("Главное меню.", reply_markup=main_menu_kb())

# Ограничение попыток — подключите к БД при необходимости
def db_has_completed_day1(user_id: int) -> bool:
    return False

def db_mark_completed_day1(user_id: int) -> None:
    pass

# ===== Команды =====

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Это бот «Неделя знаний Северсталь». Нажмите «Начать день», чтобы перейти к активностям.",
        reply_markup=main_menu_kb()
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(USER_COMMANDS_TEXT, parse_mode=None)

@router.message(F.text == "Помощь")
async def btn_help(message: types.Message):
    await cmd_help(message)

@router.message(F.text == "Профиль")
async def btn_profile(message: types.Message):
    profile = get_profile(message.from_user.id)
    if profile is None:
        await message.answer(
            "Профиль не найден. Нажмите «Начать день» и пройдите активность, чтобы создать профиль.",
            reply_markup=main_menu_kb()
        )
        return
    rewards = ', '.join(profile['rewards']) or "Нет наград"
    await message.answer(
        f"Профиль:\nID: {profile['id']}\nЛогин: {profile['username'] or '—'}\nБаллы: {profile['points']}\nНаграды: {rewards}",
        parse_mode=None
    )

@router.message(F.text == "Начать день")
async def btn_start_day(message: types.Message, state: FSMContext):
    day = current_day_global
    if day == 1:
        uid = message.from_user.id
        if db_has_completed_day1(uid) and not is_admin(uid):
            await message.answer(
                "Тест дня 1 уже пройден. Повторное прохождение доступно только администраторам.",
                reply_markup=back_to_menu_inline()
            )
            return
        await message.answer("День 1: выберите режим:", reply_markup=day1_mode_kb())
    else:
        await message.answer(
            f"День {day}: контент скоро будет доступен.",
            reply_markup=back_to_menu_inline()
        )

@router.callback_query(F.data == "nav:main")
async def nav_main(callback: types.CallbackQuery):
    await to_main_menu(callback.message)
    await callback.answer()

# ===== Админ =====

@router.message(Command("ashelp"))
async def cmd_admin_help(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администраторам.")
        return
    await message.answer(ADMIN_COMMANDS_TEXT, parse_mode=None)

@router.message(Command("setday"))
async def cmd_set_day(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Только для админов.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /setday <номер_дня>")
        return
    try:
        day = int(args[20])
    except ValueError:
        await message.answer("День должен быть числом.")
        return
    global current_day_global
    if 1 <= day <= EVENT_DAYS:
        current_day_global = day
        await message.answer(f"День установлен: {current_day_global}")
    else:
        await message.answer(f"День должен быть в диапазоне 1-{EVENT_DAYS}.")

# ===== Тест DiSC =====

def disc_slider_scores(pos: int, cat_l: str, cat_r: str) -> dict[str, int]:
    return {cat_l: 6 - pos, cat_r: pos}

def disc_mc_scores(selected: int, options: list[tuple[str, str]]) -> dict[str, int]:
    # options: [(text, cat), ...]
    cats = [opt[20] for opt in options]
    scores = {c: 1 for c in cats}
    scores[cats[selected]] += 4
    return scores

def disc_assoc_scores(selected: int, cats: list[str]) -> dict[str, int]:
    scores = {c: 1 for c in cats}
    scores[cats[selected]] += 4
    return scores

async def delete_previous_question_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_msg_id = data.get("last_question_message_id")
    if last_msg_id:
        try:
            await message.bot.delete_message(message.chat.id, last_msg_id)
        except Exception as e:
            logging.debug(f"Не удалось удалить предыдущее сообщение вопроса: {e}")

async def ask_next_disc_question(message: types.Message, state: FSMContext):
    # Проматываем невалидные карточки, показываем ОДИН валидный вопрос и выходим
    while True:
        data = await state.get_data()
        qidx = data.get("disc_q", 0)

        await delete_previous_question_message(message, state)

        if qidx >= len(DISC_QUESTIONS):
            uid = message.from_user.id
            try:
                db_mark_completed_day1(uid)
            except Exception as e:
                logging.warning(f"Не удалось пометить завершение теста: {e}")
            try:
                if get_user(uid):
                    update_points(uid, 10)
            except Exception as e:
                logging.warning(f"Не удалось начислить баллы: {e}")
            await message.answer(
                "Тест завершён! Спасибо за участие. +10 баллов начислено.",
                reply_markup=back_to_menu_inline()
            )
            await state.clear()
            return

        q = DISC_QUESTIONS[qidx]
        qtype = q.get("type")
        valid = True
        if qtype == "slider":
            valid = all(k in q for k in ("left", "right", "cat_l", "cat_r"))
        elif qtype == "mc":
            opts = q.get("options")
            valid = isinstance(opts, list) and len(opts) >= 2 and all(isinstance(o, (list, tuple)) and len(o) == 2 for o in opts)
        elif qtype == "assoc":
            icons = q.get("icons") or []
            cats = q.get("cats") or []
            valid = isinstance(icons, list) and isinstance(cats, list) and len(icons) == len(cats) and len(icons) >= 2
        else:
            valid = False

        if not valid:
            logging.error(f"Некорректная карточка вопроса idx={qidx}: {q}")
            await state.update_data(disc_q=qidx + 1)
            continue

        text = f"Вопрос {qidx + 1}/{len(DISC_QUESTIONS)}\n{q['text']}"
        if qtype == "slider":
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=f"{q['left']} (1)", callback_data="slider:1")],
                [types.InlineKeyboardButton(text="2", callback_data="slider:2")],
                [types.InlineKeyboardButton(text="3", callback_data="slider:3")],
                [types.InlineKeyboardButton(text="4", callback_data="slider:4")],
                [types.InlineKeyboardButton(text=f"{q['right']} (5)", callback_data="slider:5")],
            ])
        elif qtype == "mc":
            option_texts = [opt for opt in q["options"]]
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=t, callback_data=f"mc:{i}") for i, t in enumerate(option_texts)]
            ])
        else:  # assoc
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=icon, callback_data=f"assoc:{i}") for i, icon in enumerate(q["icons"])]
            ])

        try:
            sent_msg = await message.answer(text, reply_markup=keyboard, parse_mode=None)
        except Exception as e:
            logging.error(f"Не удалось отправить вопрос idx={qidx}: {e}")
            await state.update_data(disc_q=qidx + 1)
            continue

        await state.update_data(last_question_message_id=sent_msg.message_id)
        return

def parse_idx(cb_data: str) -> int | None:
    if ":" not in cb_data:
        return None
    _, num = cb_data.split(":", 1)
    return int(num) if num.isdigit() else None

@router.callback_query(F.data == "day1:serious")
async def start_day1_serious(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if db_has_completed_day1(uid) and not is_admin(uid):
        await callback.message.answer(
            "Тест дня 1 уже пройден. Повторное прохождение доступно только администраторам.",
            reply_markup=back_to_menu_inline()
        )
        await callback.answer()
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    try:
        await callback.message.delete()
    except Exception:
        pass

    await state.set_state(Day1States.SERIOUS_TEST)
    await state.update_data(disc_q=0, disc_scores={"D": 0, "i": 0, "S": 0, "C": 0})
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "day1:fun_soon")
async def day1_fun_coming(callback: types.CallbackQuery):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "Шуточный тест «Альтер-эго» скоро будет доступен.",
        reply_markup=back_to_menu_inline()
    )
    await callback.answer()

@router.message(Day1States.SERIOUS_TEST)
async def block_text_during_test(message: types.Message):
    await message.answer("Пожалуйста, отвечайте кнопками под вопросом.", reply_markup=back_to_menu_inline())

@router.callback_query(Day1States.SERIOUS_TEST, F.data.regexp(r"slider:\d"))
async def handle_slider_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    qidx = data.get("disc_q", 0)
    if qidx >= len(DISC_QUESTIONS):
        await callback.answer("Тест уже завершён.")
        return
    q = DISC_QUESTIONS[qidx]
    if q.get("type") != "slider" or "cat_l" not in q or "cat_r" not in q:
        await state.update_data(disc_q=qidx + 1)
        await ask_next_disc_question(callback.message, state)
        await callback.answer("Пропускаем некорректный вопрос")
        return

    pos = parse_idx(callback.data)
    if pos is None or not (1 <= pos <= 5):
        await callback.answer("Некорректные данные кнопки")
        return

    scores = data.get("disc_scores", {"D": 0, "i": 0, "S": 0, "C": 0})
    inc = disc_slider_scores(pos, q["cat_l"], q["cat_r"])
    for k, v in inc.items():
        scores[k] = scores.get(k, 0) + v

    await state.update_data(disc_scores=scores, disc_q=qidx + 1)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

@router.callback_query(Day1States.SERIOUS_TEST, F.data.regexp(r"mc:\d"))
async def handle_mc_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    qidx = data.get("disc_q", 0)
    if qidx >= len(DISC_QUESTIONS):
        await callback.answer("Тест уже завершён.")
        return
    q = DISC_QUESTIONS[qidx]
    opts = q.get("options") or []
    if q.get("type") != "mc" or not opts:
        await state.update_data(disc_q=qidx + 1)
        await ask_next_disc_question(callback.message, state)
        await callback.answer("Пропускаем некорректный вопрос")
        return

    sel = parse_idx(callback.data)
    if sel is None or sel < 0 or sel >= len(opts):
        await callback.answer("Некорректные данные кнопки")
        return

    scores = data.get("disc_scores", {"D": 0, "i": 0, "S": 0, "C": 0})
    inc = disc_mc_scores(sel, opts)
    for k, v in inc.items():
        scores[k] = scores.get(k, 0) + v

    await state.update_data(disc_scores=scores, disc_q=qidx + 1)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

@router.callback_query(Day1States.SERIOUS_TEST, F.data.regexp(r"assoc:\d"))
async def handle_assoc_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    qidx = data.get("disc_q", 0)
    if qidx >= len(DISC_QUESTIONS):
        await callback.answer("Тест уже завершён.")
        return
    q = DISC_QUESTIONS[qidx]
    icons = q.get("icons") or []
    cats = q.get("cats") or []
    if q.get("type") != "assoc" or len(icons) != len(cats) or not icons:
        await state.update_data(disc_q=qidx + 1)
        await ask_next_disc_question(callback.message, state)
        await callback.answer("Пропускаем некорректный вопрос")
        return

    sel = parse_idx(callback.data)
    if sel is None or sel < 0 or sel >= len(cats):
        await callback.answer("Некорректные данные кнопки")
        return

    scores = data.get("disc_scores", {"D": 0, "i": 0, "S": 0, "C": 0})
    inc = disc_assoc_scores(sel, cats)
    for k, v in inc.items():
        scores[k] = scores.get(k, 0) + v

    await state.update_data(disc_scores=scores, disc_q=qidx + 1)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

@router.message()
async def unknown_message(message: types.Message):
    await message.answer("Команда не распознана. Используйте меню или /help.") 
