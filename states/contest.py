from aiogram.fsm.state import State, StatesGroup


class CreateContest(StatesGroup):
    waiting_title = State()
    waiting_prize = State()
    waiting_winners_count = State()
