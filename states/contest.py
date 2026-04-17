from aiogram.fsm.state import State, StatesGroup


class CreateContest(StatesGroup):
    waiting_title         = State()
    waiting_prize_text    = State()
    waiting_prize_amount  = State()
    waiting_winners_count = State()


class EditContest(StatesGroup):
    choosing_field = State()
    waiting_value  = State()


class Broadcast(StatesGroup):
    waiting_message = State()
    confirm         = State()


class StakeInput(StatesGroup):
    waiting_value = State()


class BinanceInput(StatesGroup):
    waiting_value = State()


class ReviewInput(StatesGroup):
    waiting_content = State()
