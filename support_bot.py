"""Support bot: user-to-admin messaging system with direct dialog support"""
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from settings import TOKENS, ADMIN_ID

support_bot = Bot(token=TOKENS['support_bot'])
support_dp = Dispatcher(storage=MemoryStorage())

user_messages = {}
last_user_id = None

@support_dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        await message.answer("Admin mode: Send messages directly to respond to the last active user")
    else:
        await message.answer("Send your message to support. Admin will reply soon.")

@support_dp.message(Command("list"))
async def cmd_list(message: types.Message):
    user_id = message.from_user.id

    if user_id != ADMIN_ID:
        return

    unique_users = set(user_messages.values())

    if not unique_users:
        await message.answer("No active users found")
        return

    users_text = "Recent users:\n"
    for uid in unique_users:
        if uid != ADMIN_ID:
            users_text += f"- User ID: {uid}\n"

    if last_user_id:
        users_text += f"\nCurrent active user: {last_user_id}"

    await message.answer(users_text)

@support_dp.message(Command("to"))
async def cmd_to(message: types.Message):
    user_id = message.from_user.id

    if user_id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /to USER_ID")
        return

    try:
        target_id = int(parts[1])
        global last_user_id
        last_user_id = target_id
        await message.answer(f"Now talking to user {target_id}")
    except:
        await message.answer("Invalid user ID. Use /list to see available users.")

@support_dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id

    if user_id != ADMIN_ID:
        user_name = message.from_user.first_name

        global last_user_id
        last_user_id = user_id

        user_messages[message.message_id] = user_id

        try:
            with open('user_data.json', 'w') as f:
                data = {
                    'messages': user_messages,
                    'last_user': last_user_id
                }
                json.dump(data, f)
        except:
            pass

        forwarded = await support_bot.send_message(
            chat_id=ADMIN_ID,
            text=f"From {user_name} (ID: {user_id}):\n\n{message.text}"
        )

        user_messages[forwarded.message_id] = user_id

        await message.answer("Your message has been sent to support")

    elif user_id == ADMIN_ID:
        if message.reply_to_message:
            reply_msg_id = message.reply_to_message.message_id

            if reply_msg_id in user_messages:
                recipient_id = user_messages[reply_msg_id]
                last_user_id = recipient_id

                await support_bot.send_message(
                    chat_id=recipient_id,
                    text=f"Support response: {message.text}"
                )

                await message.answer(f"Response sent to user {recipient_id}")
            else:
                await message.answer("Cannot determine which user to respond to")

        elif last_user_id:
            await support_bot.send_message(
                chat_id=last_user_id,
                text=f"Support response: {message.text}"
            )

            await message.answer(f"Message sent to last active user (ID: {last_user_id})")
        else:
            await message.answer("No active user found. Wait for a user message or use /list and /to commands.")

async def startup_support_bot():
    global user_messages, last_user_id
    try:
        with open('user_data.json', 'r') as f:
            data = json.load(f)
            user_messages = data.get('messages', {})
            last_user_id = data.get('last_user')

            user_messages = {int(k): v for k, v in user_messages.items()}
    except:
        user_messages = {}
        last_user_id = None