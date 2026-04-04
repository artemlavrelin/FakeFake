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


class ATMInput(StatesGroup):
    waiting_binance = State()
    waiting_stake   = State()
    confirm         = State()


class BonusDrawFSM(StatesGroup):
    waiting_contest_id   = State()
    waiting_count        = State()
    waiting_exclude_prev = State()
    waiting_note         = State()


class AdminPayment(StatesGroup):
    waiting_telegram_id = State()
    waiting_field       = State()
    waiting_value       = State()
