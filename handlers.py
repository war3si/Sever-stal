import logging
from aiogram import Router, types, F
from texts import FUN_INTRO, SERIOUS_INTRO, DISC_PROFILES, DISC_COMBOS, FUN_ARCHETYPES, MOTIVATIONALS
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

# handlers.py (фрагмент)
# --- Полный рабочий раздел вопросов ---

DISC_QUESTIONS = [
    # Q1
    {
        "type": "slider",
        "text": "Когда нужно принять решение в работе, ты…",
        "left": "сначала собираю все факты и анализирую",
        "right": "принимаю быстро и действую",
        "cat_l": "C",
        "cat_r": "D"
    },
    # Q2
    {
        "type": "slider",
        "text": "На совещании ты чаще...",
        "left": "внимательно слушаю и поддерживаю коллег",
        "right": "весело вдохновляю и предлагаю идеи",
        "cat_l": "S",
        "cat_r": "i"
    },
    # Q3
    {
        "type": "mc",
        "text": "Какую роль ты чаще берёшь в проекте?",
        "options": [
            ("Лидер, который задаёт темп и принимает решения", "D"),
            ("Связующее звено, мотивирую команду", "i"),
            ("Тот, кто гарантирует стабильность и порядок", "S"),
            ("Эксперт, проверяю качество и детали", "C")
        ]
    },
    # Q4
    {
        "type": "slider",
        "text": "Как ты относишься к изменениям в процессе работы?",
        "left": "предпочитаю предсказуемость и ясный план",
        "right": "вижу возможность, быстро включаюсь",
        "cat_l": "S",
        "cat_r": "D"
    },
    # Q5
    {
        "type": "slider",
        "text": "Когда тебе нужно убедить коллег, ты…",
        "left": "подбираю факты и аргументы",
        "right": "готов рассказать историю и воодушевить",
        "cat_l": "C",
        "cat_r": "i"
    },
    # Q6
    {
        "type": "mc",
        "text": "Твой идеальный рабочий формат",
        "options": [
            ("Чёткие KPI и свобода исполнения", "D"),
            ("Открытое общение, мозговые штурмы", "i"),
            ("Стабильный график и командная поддержка", "S"),
            ("Проверенные регламенты и чек-листы", "C")
        ]
    },
    # Q7
    {
        "type": "slider",
        "text": "При конфликте ты обычно…",
        "left": "ищу консенсус и стабильность",
        "right": "открыто отстаиваю позицию и закрываю тему",
        "cat_l": "S",
        "cat_r": "D"
    },
    # Q8
    {
        "type": "assoc",
        "text": "Выбери картинку, которая ближе по духу",
        "icons": ["📢 Мегафон", "🛡️ Рука помощи", "⏱️ Таймер", "🔎 Чек-лист"],
        "cats": ["i", "S", "D", "C"]
    },
    # Q9
    {
        "type": "mc",
        "text": "Как ты готовишься к важной презентации?",
        "options": [
            ("Составляю чёткий план и репетирую", "C"),
            ("Создаю эмоциональную историю и примеры", "i"),
            ("Определяю ключевые решения и акценты", "D"),
            ("Готовлю резервные варианты и поддержу команду", "S")
        ]
    },
    # Q10
    {
        "type": "slider",
        "text": "Твой рабочий темп —",
        "left": "равномерный, без бросков и паники",
        "right": "интенсивный, люблю высокий темп",
        "cat_l": "S",
        "cat_r": "D"
    },
    # Q11
    {
        "type": "mc",
        "text": "Что для тебя важнее в коммуникации?",
        "options": [
            ("Результат и решение проблемы", "D"),
            ("Эмоциональная связь и вовлечение", "i"),
            ("Надёжность и поддержка команды", "S"),
            ("Точность, корректность и документы", "C")
        ]
    },
    # Q12
    {
        "type": "slider",
        "text": "Как ты реагируешь на критику?",
        "left": "принимаю спокойно и анализирую",
        "right": "воспринимаю как вызов и действую",
        "cat_l": "C",
        "cat_r": "D"
    },
    # Q13
    {
        "type": "slider",
        "text": "В неформальном общении ты…",
        "left": "скорее сдержан/спокойный",
        "right": "общительный и заводной",
        "cat_l": "S",
        "cat_r": "i"
    },
    # Q14
    {
        "type": "mc",
        "text": "Какую обратную связь ты предпочитаешь получать?",
        "options": [
            ("Кратко и по делу: что и когда исправить", "D"),
            ("В тёплой форме, с примерами сильных сторон", "i"),
            ("Сделать это стабильно и без сюрпризов", "S"),
            ("Со ссылками на источники и детали", "C")
        ]
    },
    # Q15
    {
        "type": "assoc",
        "text": "Какой рабочий предмет ближе тебе?",
        "icons": ["📢 Планшет/мегафон", "⏰ Горячий график/часы", "☕ Тёплый плед/чашка", "👓 Очки/лупа"],
        "cats": ["i", "D", "S", "C"]
    },
    # Q16
    {
        "type": "slider",
        "text": "Перед большим дедлайном ты…",
        "left": "расставляю приоритеты и распределяю задачи",
        "right": "взялся бы за самое сложное и ускорился",
        "cat_l": "C",
        "cat_r": "D"
    },
    # Q17
    {
        "type": "mc",
        "text": "Как ты мотивируешь коллег?",
        "options": [
            ("Показываю чёткие цели и последствия", "D"),
            ("Вдохновляю примерами и энергией", "i"),
            ("Поддерживаю стабильностью и заботой", "S"),
            ("Даю шаблоны и инструкции", "C")
        ]
    },
    # Q18
    {
        "type": "slider",
        "text": "Твой идеал команды —",
        "left": "спокойная, надёжная, взаимопомогающая",
        "right": "динамичная, амбициозная, целеустремлённая",
        "cat_l": "S",
        "cat_r": "D"
    }
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
    {
        "text": "Твой способ реагировать на внезапные просьбы коллег:",
        "options": [
            ("Сразу включаюсь и решаю задачу 🔥", "always_loud"),
            ("Сначала обдумываю, потом действую спокойно 😼", "cat_headphones"),
            ("Добавляю креативный штрих или шутку 🤣", "smiley_collector"),
            ("Чётко фиксирую задачу 📋", "postman"),
        ]
    },
    {
        "text": "Если дают слово на 1 минуту на собрании — ты:",
        "options": [
            ("Взрываешь зал эмоциями 🔥", "always_loud"),
            ("Шутничаешь, но по делу 🎭", "maskman"),
            ("5 фактов, без воды 📊", "postman"),
            ("Сделал мем — и ушёл 🐱‍👤", "smiley_collector"),
        ]
    },
    {
        "text": "На фидбеке ты чаще:",
        "options": [
            ("Сначала шутка, потом правда 😄", "smiley_collector"),
            ("Прямо и быстро ⚡", "report_raw"),
            ("Спокойно, выслушаю ☕", "cat_headphones"),
            ("Подстраиваюсь под слушателя 🎭", "maskman"),
        ]
    },
    {
        "text": "Твой идеальный аватар в чате:",
        "options": [
            ("GIF танцующего кота 🐱", "smiley_collector"),
            ("Фото твоего стола 📸", "postman"),
            ("Яркий мем 😂", "always_loud"),
            ("Неброская иконка 🔵", "cat_headphones"),
        ]
    },
    {
        "text": "Как ты реагируешь на споры?",
        "options": [
            ("Включаю громкость и пытаюсь убедить 📣", "always_loud"),
            ("Находишь шутку 😅", "smiley_collector"),
            ("Говорю прямо и завершаю тему 🔪", "report_raw"),
            ("Отступаю и наблюдаю 👀", "cat_headphones"),
        ]
    },
    {
        "text": "При внезапном совещании ты:",
        "options": [
            ("Врываешься с идеями 💡", "always_loud"),
            ("Проверяешь факты — говоришь главное ✅", "postman"),
            ("Делаешь короткое видео/стикер 📹", "smiley_collector"),
            ("Даю сигнал присутствия — слушаю 🔇", "cat_headphones"),
        ]
    },
    {
        "text": "Твой любимый формат общения:",
        "options": [
            ("Короткие ролики/сторис 🎬", "tiktok_fast"),
            ("Громкие реплики в зале 🎙", "always_loud"),
            ("Личные сообщения, тихо ✉️", "cat_headphones"),
            ("Чёткие письма/чек-листы 📄", "postman"),
        ]
    },
    {
        "text": "Если нужно слово сказать о коллеге:",
        "options": [
            ("Сделаю яркое видео/коллаж 🎨", "tiktok_fast"),
            ("Скажу прямо, без обиняков 🗡", "report_raw"),
            ("Похвалю тёпло, дам поддержку 🤝", "maskman"),
            ("Отправлю короткое письмо ✉️", "postman"),
        ]
    },
    {
        "text": "Ты в лайве/стриме — кто ты?",
        "options": [
            ("Взрываю чат эмоциями 🔥", "always_loud"),
            ("Фон: спокойствие и уют 🛋", "cat_headphones"),
            ("Маски, роли, перевоплощения 🎭", "maskman"),
            ("Точность и структура контента 📋", "postman"),
        ]
    },
    {
        "text": "Как ты заканчиваешь рабочую переписку?",
        "options": [
            ("Стикером 🎭", "smiley_collector"),
            ("Коротко: сделаем завтра 🗓", "postman"),
            ("Огромное «Спасибо всем!» 🎉", "always_loud"),
            ("… (ничего)", "cat_headphones"),
        ]
    },
    {
        "text": "Твоя суперспособность в команде:",
        "options": [
            ("Заводить людей и давать энергию ⚡", "always_loud"),
            ("Доставлять сообщения точно ✉️", "postman"),
            ("Никогда не паниковать 😼", "cat_headphones"),
            ("Мгновенно адаптироваться к аудитории 🎭", "maskman"),
        ]
    }
]




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

from aiogram.filters import CommandObject

# Список ID админов — замени на свои
ADMINS = {1995633871}  # <== сюда свои Telegram ID

def is_admin(user_id: int):
    return user_id in ADMINS

# Хранение текущего дня в памяти (для теста)
current_day = 1

@router.message(Command("addpoints"))
async def cmd_add_points(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Команда доступна только администраторам.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("Использование: /addpoints <user_id> <points>")
        return
    try:
        user_id = int(args[1])
        points = int(args[2])
    except ValueError:
        await message.answer("Неверный формат аргументов. Должны быть числа.")
        return

    user = get_user(user_id)
    if not user:
        await message.answer("Пользователь не найден.")
        return

    update_points(user_id, points)
    await message.answer(f"{points} баллов начислено пользователю {user_id}.")

@router.message(Command("skipday"))
async def cmd_skip_day(message: types.Message):
    global current_day
    if not is_admin(message.from_user.id):
        await message.answer("Команда доступна только администраторам.")
        return
    if current_day < EVENT_DAYS:
        current_day += 1
        await message.answer(f"Переход на следующий день: День {current_day}")
    else:
        await message.answer("Максимальный день уже достигнут.")

@router.message(Command("setday"))
async def cmd_set_day(message: types.Message):
    global current_day
    if not is_admin(message.from_user.id):
        await message.answer("Команда доступна только администраторам.")
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
        await message.answer(f"Текущий день установлен на {current_day}.")
    else:
        await message.answer(f"День должен быть в диапазоне от 1 до {EVENT_DAYS}.")

@router.message(Command("resetdb"))
async def cmd_reset_db(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Команда доступна только администра")
