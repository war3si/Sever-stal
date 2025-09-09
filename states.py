from aiogram.fsm.state import State, StatesGroup

class Day1States(StatesGroup):
    CHOOSE_CARD = State()
    SERIOUS_TEST = State()
    FUN_TEST = State()
    SHOW_RESULT = State()
    MINI_TASK = State()