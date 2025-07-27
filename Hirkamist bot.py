
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

API_TOKEN = "8404970833:AAHfW_08cWb4oFEw1_haY3aXtAR6MusOnXo"    # Replace with your actual bot token
ADMIN_ID = 206394562 # Replace with your actual admin ID

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

conn = sqlite3.connect("database.db")
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    house TEXT,
    family TEXT,
    account_number TEXT,
    balance INTEGER
)""")
conn.commit()

class Register(StatesGroup):
    full_name = State()
    family = State()
    house = State()

class Transfer(StatesGroup):
    receiver_id = State()
    amount = State()

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if cur.fetchone():
        await message.answer("شما قبلاً ثبت‌نام کرده‌اید.\n/transfer برای انتقال گالیون\n/balance برای موجودی")
    else:
        await message.answer("به بانک هیرکامیست خوش آمدید!\nلطفاً نام کامل جادویی‌تان را بنویسید:")
        await Register.full_name.set()

@dp.message_handler(state=Register.full_name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("نام خاندان‌تان را بنویسید:")
    await Register.family.set()

@dp.message_handler(state=Register.family)
async def reg_family(message: types.Message, state: FSMContext):
    await state.update_data(family=message.text)
    await message.answer("گروهتان را وارد کنید (اسلیترین، ریونکلاو...):")
    await Register.house.set()

@dp.message_handler(state=Register.house)
async def reg_house(message: types.Message, state: FSMContext):
    data = await state.get_data()
    full_name = data['full_name']
    family = data['family']
    house = message.text
    user_id = message.from_user.id
    account_number = f"HRK-{user_id}"
    balance = 50

    cur.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, full_name, house, family, account_number, balance))
    conn.commit()

    await message.answer(f"ثبت‌نام کامل شد!\nشماره حساب شما: {account_number}\nموجودی: {balance} گالیون")
    await state.finish()

@dp.message_handler(commands=['balance'])
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row:
        await message.answer(f"موجودی شما: {row[0]} گالیون")
    else:
        await message.answer("شما هنوز ثبت‌نام نکرده‌اید. از /start استفاده کنید.")

@dp.message_handler(commands=['transfer'])
async def transfer_start(message: types.Message):
    cur.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,))
    if not cur.fetchone():
        await message.answer("لطفاً اول ثبت‌نام کنید با /start")
        return
    await message.answer("آیدی عددی گیرنده را وارد کنید:")
    await Transfer.receiver_id.set()

@dp.message_handler(state=Transfer.receiver_id)
async def get_receiver_id(message: types.Message, state: FSMContext):
    try:
        receiver_id = int(message.text)
        if receiver_id == message.from_user.id:
            await message.answer("نمی‌توانید به خودتان انتقال دهید.")
            return

        cur.execute("SELECT * FROM users WHERE user_id=?", (receiver_id,))
        if not cur.fetchone():
            await message.answer("گیرنده هنوز ثبت‌نام نکرده است.")
            return

        await state.update_data(receiver_id=receiver_id)
        await message.answer("مقدار گالیون مورد نظر را وارد کنید:")
        await Transfer.amount.set()
    except:
        await message.answer("آیدی عددی معتبر وارد کنید.")

@dp.message_handler(state=Transfer.amount)
async def transfer_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer("مقدار نامعتبر است.")
            return

        data = await state.get_data()
        sender_id = message.from_user.id
        receiver_id = data['receiver_id']

        cur.execute("SELECT balance FROM users WHERE user_id=?", (sender_id,))
        sender_balance = cur.fetchone()[0]
        if sender_balance < amount:
            await message.answer("موجودی کافی ندارید.")
            return

        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, sender_id))
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, receiver_id))
        conn.commit()

        await message.answer(f"{amount} گالیون به کاربر {receiver_id} منتقل شد.")
        await state.finish()
    except:
        await message.answer("عدد معتبر وارد کنید.")

@dp.message_handler(commands=['user_info'])
async def user_info(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("دستور صحیح: /user_info <user_id>")
        return

    uid = int(parts[1])
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()
    if row:
        msg = f"اطلاعات:\nنام: {row[1]}\nخاندان: {row[3]}\nگروه: {row[2]}\nحساب: {row[4]}\nموجودی: {row[5]} گالیون"
        await message.answer(msg)
    else:
        await message.answer("کاربر یافت نشد.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
