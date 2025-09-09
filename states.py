# states.py
from aiogram.fsm.state import State, StatesGroup

class Day1States(StatesGroup):
    CHOOSE_CARD = State()
    SERIOUS_TEST = State()  # Для вопросов серьёзного теста
    FUN_TEST = State()      # Для вопросов шуточного теста
    MINI_TASK = State()     # Для мини-задания после теста
