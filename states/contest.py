from aiogram.fsm.state import State, StatesGroup


class CreateContest(StatesGroup):
    waiting_title = State()         # описание конкурса
    waiting_prize_text = State()    # текст приза, e.g. "10$ USDT"
    waiting_prize_amount = State()  # числовая сумма для статистики
    waiting_winners_count = State()


class EditContest(StatesGroup):
    choosing_field = State()   # inline: what to edit
    waiting_value = State()    # text input: new value


class Broadcast(StatesGroup):
    waiting_message = State()
    confirm = State()
