# handlers.py
import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import json  # Для парсинга, если нужно

from config import EVENT_START_DATE, EVENT_DAYS, simulated_day_offset
from db import get_user, create_user, update_points, add_reward, get_profile
from states import Day1States

router = Router()

# Логирование
logging.basicConfig(level=logging.INFO)

# Вспомогательная функция для текущего дня (с симуляцией)
def get_current_day():
    today = datetime.now().date()
    start_date = datetime.strptime(EVENT_START_DATE, '%Y-%m-%d').date()
    simulated_date = start_date + timedelta(days=simulated_day_offset)
    day = (today - start_date).days + 1 + simulated_day_offset
    if 1 <= day <= EVENT_DAYS:
        return day
    return 0  # Не в период мероприятия

# /start
@router.message(Command('start'))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_user(user_id)
    if not user:
        create_user(user_id, username or f'user_{user_id}')
        await message.answer("Добро пожаловать! Аккаунт создан.")
    else:
        await message.answer("С возвращением!")
    await message.answer("Используй /profile для просмотра профиля, /day1 для старта дня 1.")

# /profile
@router.message(Command('profile'))
async def profile_handler(message: types.Message):
    user_id = message.from_user.id
    profile = get_profile(user_id)
    if profile:
        rewards_str = ', '.join(profile['rewards']) if profile['rewards'] else 'Нет наград'
        await message.answer(
            f"Профиль:\nUsername: {profile['username']}\nБаллы: {profile['points']}\nНаграды: {rewards_str}"
        )
    else:
        await message.answer("Аккаунт не найден. Попробуй /start.")

# /nextday (для теста)
@router.message(Command('nextday'))
async def nextday_handler(message: types.Message):
    global simulated_day_offset
    simulated_day_offset += 1
    await message.answer(f"Симулирован переход к следующему дню. Текущий день: {get_current_day()}")

# /day1
@router.message(Command('day1'))
async def day1_handler(message: types.Message, state: FSMContext):
    current_day = get_current_day()
    if current_day >= 1:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Карточка №1 «Ты на работе»", callback_data="card1")],
            [types.InlineKeyboardButton(text="Карточка №2 «Твоё Альтер‑эго»", callback_data="card2")]
        ])
        await message.answer("День 1: Выбери карточку!", reply_markup=keyboard)
        await state.set_state(Day1States.CHOOSE_CARD)
    else:
        await message.answer("День 1 ещё не начался.")

# Обработка выбора карточки
@router.callback_query(Day1States.CHOOSE_CARD)
async def choose_card_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
        if callback.data == "card1":
            await callback.message.answer("Начинаем серьёзный тест DiSC!")
            await state.set_state(Day1States.SERIOUS_TEST)
            await state.update_data(test_type="serious", answers=[], question_num=0)
            await ask_serious_question(callback.message, state)
        elif callback.data == "card2":
            await callback.message.answer("Начинаем шуточный тест!")
            await state.set_state(Day1States.FUN_TEST)
            await state.update_data(test_type="fun", answers=[], question_num=0)
            await ask_fun_question(callback.message, state)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in choose_card: {e}")
        await callback.message.answer("Произошла ошибка. Попробуй заново.")

# Вопросы для серьёзного теста (пример 15 вопросов, упрощённо)
serious_questions = [
    {"text": "Насколько ты доминируешь в разговорах? (1-10)", "type": "slider", "area": "D"},
    # Добавь ещё 14 вопросов аналогично, с типами: slider, multiple (список опций), association (текст)
    # Для полноты: всего 15, по 3-4 на область (D, i, S, C)
    # ... (я сократил для примера, в реальном коде расширь)
] * 15  # Placeholder: повтори для 15

async def ask_serious_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_num = data.get('question_num', 0)
    if q_num < len(serious_questions):
        q = serious_questions[q_num]
        await message.answer(q['text'])  # Для slider/multiple используй клавиатуру
        # Здесь добавь inline-кнопки для ответов (упрощённо: текстом)
    else:
        await calculate_serious_result(message, state)

async def calculate_serious_result(message: types.Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get('answers', [])
    # Логика расчёта: суммируй по областям, определи тип (например, max(score_D, i, S, C))
    # Пример упрощённый:
    profile = "iS"  # Рассчитай на основе answers
    result = f"Твой профиль — {profile}: ты вдохновляешь и поддерживаешь, но иногда медлишь с решениями. Попробуй практику “активного тайм-менеджмента”.\nСоветы: 1. ... 2. ... 3. ..."
    await message.answer(result)
    update_points(message.from_user.id, 10)
    await message.answer("+10 баллов! Теперь мини-задание.")
    await start_mini_task(message, state)

# Аналогично для fun_test (7 вопросов)
fun_questions = [
    {"text": "Какой эмодзи описывает твой день? 😎 или 🤯", "type": "choice"},
    # Добавь 6 ещё
] * 7

async def ask_fun_question(message: types.Message, state: FSMContext):
    # Аналогично serious, с callbacks или текстом

async def calculate_fun_result(message: types.Message, state: FSMContext):
    # Рассчитай забавный результат, например "Рация без батареек"
    result = "Ты — Рация без батареек! 😆 Диагноз: ..."
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Поделиться результатом", url="https://t.me/share/url?url=Мой результат...")]
    ])
    await message.answer(result, reply_markup=keyboard)
    await start_mini_task(message, state)

# Мини-задание
async def start_mini_task(message: types.Message, state: FSMContext):
    await message.answer("Мини-задание: Скажи “спасибо” коллеге, с которым обычно не общаешься — и отпиши, что почувствовал.")
    await state.set_state(Day1States.MINI_TASK)

@router.message(Day1States.MINI_TASK)
async def mini_task_handler(message: types.Message, state: FSMContext):
    try:
        # Принимаем любой текст как отчёт
        update_points(message.from_user.id, 5)
        add_reward(message.from_user.id, "Первые шаги")
        await message.answer("+5 баллов! Бейдж 'Первые шаги' добавлен.")
        await state.clear()
    except Exception as e:
        logging.error(f"Error in mini_task: {e}")
        await message.answer("Ошибка. Попробуй заново.")
