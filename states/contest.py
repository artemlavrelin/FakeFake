from aiogram.fsm.state import State, StatesGroup


class CreateContest(StatesGroup):
    waiting_title = State(); waiting_prize_text = State()
    waiting_prize_amount = State(); waiting_winners_count = State()

class EditContest(StatesGroup):
    choosing_field = State(); waiting_value = State()

class Broadcast(StatesGroup):
    waiting_message = State(); confirm = State()

class StakeInput(StatesGroup):
    waiting_value = State()

class BinanceInput(StatesGroup):
    waiting_value = State()

class ReviewInput(StatesGroup):
    waiting_content = State()

class LootFSM(StatesGroup):
    waiting_binance_screenshot = State()
    waiting_stake_screenshot = State()
    confirm = State()

class AddBetFSM(StatesGroup):
    waiting_content = State()

class ProfileFSM(StatesGroup):
    waiting_instagram = State()
    waiting_threads = State()
    waiting_facebook = State()
    waiting_twitter = State()
    confirm = State()

class WithdrawFSM(StatesGroup):
    waiting_amount = State()
    confirm = State()

class CreateTaskFSM(StatesGroup):
    waiting_platform = State()
    waiting_link = State()
    waiting_max_users = State()
    waiting_action_type = State()
    waiting_description = State()
    waiting_reward = State()
    waiting_comments = State()
    confirm = State()

class AdminChangeFSM(StatesGroup):
    waiting_field = State()
    waiting_value = State()

class TaskUserFSM(StatesGroup):
    viewing = State()
    doing = State()
    waiting_screenshot = State()

class ReportFSM(StatesGroup):
    waiting_content = State()
