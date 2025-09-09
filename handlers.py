import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from random import choice
from config import EVENT_START_DATE, EVENT_DAYS, PODCAST_URL
from db import get_user, create_user, update_points, add_reward, get_profile
from states import Day1States
from texts import DISC_PROFILES, DISC_COMBOS, FUN_ARCHETYPES, MOTIVATIONALS

router = Router()
logging.basicConfig(level=logging.INFO)

# ====================
# ПАРАМЕТРЫ ТЕСТОВ
# ====================

DISC_QUESTIONS = [
    # Q1 - Slider
    {
        "type": "slider",
        "text": "Когда нужно принять решение в работе, ты…",
        "left": "Сначала собираю все факты и анализирую",
        "right": "Принимаю быстро и действую",
        "cat_l": "C",
        "cat_r": "D",
    },
    # Q2 - Slider
    {
        "type": "slider",
        "text": "На совещании ты чаще...",
        "left": "Внимательно слушаю и поддерживаю коллег",
        "right": "Весело вдохновляю и предлагаю идеи",
        "cat_l": "S",
        "cat_r": "i",
    },
    # Q3 - MC
    {
        "type": "mc",
        "text": "Какую роль ты чаще берёшь в проекте?",
        "options": [
            ("Лидер, который задаёт темп", "D"),
            ("Связующее звено, мотивирую команду", "i"),
            ("Гарантирую стабильность и порядок", "S"),
            ("Эксперт, проверяю качество", "C"),
        ]
    },
    # ... и далее по аналогии до 18 вопросов!
]
FUN_QUESTIONS = [
    {
        "text": "Как ты приветствуешь коллег утром?",
        "options": [
            ("Ого, всем хорошего! 😊", "always_loud"),
            ("Привет, как дела? 👋", "cat_headphones"),
            ("(смех + GIF) 🤣", "smiley_collector"),
            ("Кратко: по делам ✉️", "postman"),
        ]
    },
    # ... всего 12, добавить остальные по сценарию
]
FUN_ARCHETYP_NAMES = ["always_loud", "cat_headphones", "smiley_collector", "postman",
                      "tiktok_fast", "report_raw", "maskman", "support_colleague"]

# ==============
# ВСТУПЛЕНИЯ
# ==============

SERIOUS_INTRO = (
    "Сегодня проверим твой стиль коммуникации на работе!\n\n"
    "Это короткий тест по международной методике DiSC. "
    "Отвечай спонтанно, не обдумывай слишком долго — так результат будет яснее и полезнее.\n\n"
    "В финале тебя ждёт твой коммуникационный профиль и 3 полезных совета 💡"
)
FUN_INTRO = (
    "Пора раскрыть своё скрытое альтер-эго!\n\n"
    "Не думай слишком долго — просто выбирай то, что ближе к тебе.\n"
    "В конце теста тебя ждёт забавный архетип с коротким описанием и шутливым «диагнозом», которым можно поделиться!"
)

# ==============
# HELPER-функции
# ==============

def disc_slider_scores(pos, cat_l, cat_r):
    """pos: int [1-5], cat_l ('C'), cat_r('D'), возвращает dict для добавления"""
    res = {cat_l: 6-pos, cat_r: pos}
    return res

def disc_mc_scores(selected, options):
    """selected: индекс, options: [(текст, категория)]"""
    cats = [opt[1] for opt in options]
    scores = {c: 1 for c in cats}
    scores[cats[selected]] += 4
    return scores

def disc_assoc_scores(selected, cats):
    """selected: индекс, cats: последовательность ['i','S','D','C']"""
    scores = {c: 1 for c in cats}
    scores[cats[selected]] += 4
    return scores

def fun_test_add_score(arch_scores, chosen_idx, options):
    """arch_scores: dict, chosen_idx: int, options: [("Текст", "arch")]"""
    for i, (_, arch) in enumerate(options):
        arch_scores.setdefault(arch, 0)
        arch_scores[arch] += 5 if i == chosen_idx else 1

def disc_result_from_scores(scores):
    ordered = sorted(scores.items(), key=lambda x: -x[1])
    first, fscore = ordered[0]
    second, sscore = ordered[1]
    if fscore - sscore >= 3:
        return first
    else:
        return "".join(sorted([first, second]))

# ==============
# СТАРТ и ПРОФИЛЬ
# ==============

@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or f'user_{user_id}'
    if not get_user(user_id):
        create_user(user_id, username)
        await message.answer("Добро пожаловать! Аккаунт создан.")
    else:
        await message.answer("С возвращением!")
    await message.answer("Используй /profile для профиля или /day1 — старт дня 1!")

@router.message(Command("profile"))
async def profile_handler(message: types.Message):
    p = get_profile(message.from_user.id)
    if p:
        await message.answer(
            f"Профиль:\nUsername: {p['username']}\nБаллы: {p['points']}\nНаграды: {', '.join(p['rewards']) if p['rewards'] else 'Нет'}"
        )
    else:
        await message.answer("Сначала зарегистрируйтесь через /start.")

# ==============
# ДЕНЬ 1
# ==============

@router.message(Command('day1'))
async def day1_handler(message: types.Message, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Ты на работе", callback_data="card_serious")],
            [types.InlineKeyboardButton(text="Твоё Альтер-эго", callback_data="card_fun")]
        ]
    )
    await message.answer("🟢 День 1. Двойной тест «Коммуникатор & Альтер‑эго»\n\nВыбери с чего начнём:", reply_markup=keyboard)
    await state.set_state(Day1States.CHOOSE_CARD)

@router.callback_query(Day1States.CHOOSE_CARD, F.data == "card_serious")
async def start_serious(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(SERIOUS_INTRO)
    await state.update_data(disc_scores={"D":0, "i":0, "S":0, "C":0}, disc_q=0)
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

@router.callback_query(Day1States.CHOOSE_CARD, F.data == "card_fun")
async def start_fun(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(FUN_INTRO)
    await state.update_data(fun_scores={}, fun_q=0, answers=[])
    await ask_next_fun_question(callback.message, state)
    await callback.answer()

# ========== DISC TEST LOGIC ==========

async def ask_next_disc_question(message, state: FSMContext):
    data = await state.get_data()
    qidx = data.get("disc_q", 0)
    if qidx >= len(DISC_QUESTIONS):
        await finish_disc(message, state)
        return
    q = DISC_QUESTIONS[qidx]
    text = f"Вопрос {qidx+1}/{len(DISC_QUESTIONS)}\n{q['text']}\n"
    if q["type"] == "slider":
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=f"{q['left']} (1)", callback_data="slider:1")],
                [types.InlineKeyboardButton(text="2", callback_data="slider:2")],
                [types.InlineKeyboardButton(text="3", callback_data="slider:3")],
                [types.InlineKeyboardButton(text="4", callback_data="slider:4")],
                [types.InlineKeyboardButton(text=f"{q['right']} (5)", callback_data="slider:5")]
            ]
        )
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(Day1States.SERIOUS_TEST)
    elif q["type"] == "mc":
        opts = q["options"]
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=txt, callback_data=f"mc:{i}") for i, (txt, _) in enumerate(opts)]
            ]
        )
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(Day1States.SERIOUS_TEST)
    elif q["type"] == "assoc":
        icns = q["icons"]
        cats = q["cats"]
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=icn, callback_data=f"assoc:{i}") for i, icn in enumerate(icns)]
            ]
        )
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(Day1States.SERIOUS_TEST)

@router.callback_query(Day1States.SERIOUS_TEST, F.data.regexp(r"slider:\d"))
async def handle_slider_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score_d = data.get("disc_scores", {"D":0,"i":0,"S":0,"C":0})
    qidx = data["disc_q"]
    pos = int(callback.data.split(":")[1])
    q = DISC_QUESTIONS[qidx]
    for_k = disc_slider_scores(pos, q["cat_l"], q["cat_r"])
    for k in for_k:
        score_d[k] += for_k[k]
    await state.update_data(disc_scores=score_d, disc_q=qidx+1)
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

@router.callback_query(Day1States.SERIOUS_TEST, F.data.regexp(r"mc:\d"))
async def handle_mc_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score_d = data.get("disc_scores", {"D":0,"i":0,"S":0,"C":0})
    qidx = data["disc_q"]
    sel = int(callback.data.split(":")[1])
    q = DISC_QUESTIONS[qidx]
    cat_update = disc_mc_scores(sel, q["options"])
    for k in cat_update:
        score_d[k] += cat_update[k]
    await state.update_data(disc_scores=score_d, disc_q=qidx+1)
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

@router.callback_query(Day1States.SERIOUS_TEST, F.data.regexp(r"assoc:\d"))
async def handle_assoc_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    score_d = data.get("disc_scores", {"D":0,"i":0,"S":0,"C":0})
    qidx = data["disc_q"]
    sel = int(callback.data.split(":")[1])
    q = DISC_QUESTIONS[qidx]
    cat_update = disc_assoc_scores(sel, q["cats"])
    for k in cat_update:
        score_d[k] += cat_update[k]
    await state.update_data(disc_scores=score_d, disc_q=qidx+1)
    await ask_next_disc_question(callback.message, state)
    await callback.answer()

async def finish_disc(message, state: FSMContext):
    data = await state.get_data()
    scores = data.get("disc_scores", {"D":0,"i":0,"S":0,"C":0})
    res_type = disc_result_from_scores(scores)
    proftext = DISC_PROFILES[res_type] if res_type in DISC_PROFILES else DISC_COMBOS.get(res_type, {})
    motiv = proftext.get('motiv', choice(MOTIVATIONALS))
    tips = proftext.get("tips", ["Совет 1", "Совет 2", "Совет 3"])
    msg = f"<b>{proftext.get('title','Твой профиль')}</b>\n\n{proftext.get('desc_1','')}\n{proftext.get('desc_2','')}\n\n"
    msg += "💡<b>3 совета:</b>\n" + "\n".join([f"- {t}" for t in tips])
    # Кнопки результат/шаринг/подкаст/повтор
    share_url = f"https://t.me/share/url?url=&text={proftext.get('title','')}: {motiv}"
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Поделиться", url=share_url)],
            [types.InlineKeyboardButton(text="Пройти другой тест", callback_data="restart_test")],
            [types.InlineKeyboardButton(text="Послушать подкаст (5 мин)", url=PODCAST_URL)]
        ]
    )
    await message.answer(msg, reply_markup=keyboard)
    await message.answer(f"Мотивация дня: <i>{motiv}</i>")
    update_points(message.from_user.id, 10)
    await message.answer("+10 баллов начислено!")
    await state.set_state(Day1States.SHOW_RESULT)

@router.callback_query(Day1States.SHOW_RESULT, F.data == "restart_test")
async def restart_test(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Выбери тест:")
    await day1_handler(callback.message, state)
    await callback.answer()

# ========== FUN TEST LOGIC ==========

async def ask_next_fun_question(message, state: FSMContext):
    data = await state.get_data()
    qidx = data.get("fun_q", 0)
    if qidx >= len(FUN_QUESTIONS):
        await finish_fun_test(message, state)
        return
    q = FUN_QUESTIONS[qidx]
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=txt, callback_data=f"fun:{i}") for i, (txt, _) in enumerate(q["options"])]
        ]
    )
    await message.answer(f"Вопрос {qidx+1}/{len(FUN_QUESTIONS)}\n{q['text']}", reply_markup=keyboard)
    await state.set_state(Day1States.FUN_TEST)

@router.callback_query(Day1States.FUN_TEST, F.data.regexp(r"fun:\d"))
async def handle_fun_q(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    qidx = data.get("fun_q", 0)
    scores = data.get("fun_scores", {})
    sel_idx = int(callback.data.split(":")[1])
    fun_test_add_score(scores, sel_idx, FUN_QUESTIONS[qidx]["options"])
    await state.update_data(fun_scores=scores, fun_q=qidx+1)
    await ask_next_fun_question(callback.message, state)
    await callback.answer()

async def finish_fun_test(message, state: FSMContext):
    data = await state.get_data()
    scores = data.get("fun_scores", {})
    top = max(scores.items(), key=lambda x: x[1])[0] if scores else "always_loud"
    arch = FUN_ARCHETYPES[top]
    share_url = f"https://t.me/share/url?url=&text=Мой диагноз: {arch['title']} — {arch['share']}"
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Поделиться", url=share_url)],
            [types.InlineKeyboardButton(text="Пройти другой тест", callback_data="restart_test")],
        ]
    )
    await message.answer(f"<b>{arch['title']}</b>\n\n{arch['desc']}\n\nСовет: {arch['advice']}", reply_markup=keyboard)
    update_points(message.from_user.id, 10)
    await message.answer("+10 баллов начислено!")
    await state.set_state(Day1States.SHOW_RESULT)

# ========== Мини-задание ==========

# (добавляется по аналогии как отдельный блок после теста)

