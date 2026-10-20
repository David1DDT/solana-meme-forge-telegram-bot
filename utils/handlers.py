"""Utility functions and main handlers for memecoin bot"""
import logging, asyncio, unicodedata, os, json, datetime
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from utils.keyboards import get_supply_keyboard, get_confirm_keyboard, get_check_payment_keyboard, get_create_again_keyboard
from settings import LANGUAGES, AMOUNT
from utils.custom_address_manager import calculate_custom_price


def get_user_info(user):
    """Get user information for logging"""
    user_id = user.id
    username = f"@{user.username}" if user.username else "no_username"
    return f"[{user_id}:{username}]"


def log_user_action(user, action):
    """Log user actions"""
    user_info = get_user_info(user)
    logging.info(f"{user_info} {action}")


def get_payment_amount(user_data):
    """Get the payment amount based on user selection with bonus support"""
    if not isinstance(user_data, dict):
        logging.warning(f"get_payment_amount: user_data should be dict, got {type(user_data)}: {user_data}")
        return AMOUNT

    base_amount = AMOUNT
    custom_ending = user_data.get('custom_ending')

    if custom_ending:
        is_bonus_used = user_data.get('is_bonus_used', False)

        if is_bonus_used and len(custom_ending) == 4:
            total_amount = base_amount
            logging.debug(f"DEBUG: Bonus used for {custom_ending}, total: {total_amount}")
        else:
            custom_price = calculate_custom_price(custom_ending)
            total_amount = base_amount + custom_price
            logging.debug(
                f"DEBUG: Regular price for {custom_ending}, custom_price: {custom_price}, total: {total_amount}")
    else:
        total_amount = base_amount
        logging.debug(f"DEBUG: No custom ending, total: {total_amount}")

    return round(total_amount, 2)


def save_memecoin_data(user_data, tx_signature):
    """Save memecoin data to JSON file"""
    memecoin_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "tx_signature": tx_signature,
        "token_name": user_data.get('token_name'),
        "token_symbol": user_data.get('token_symbol'),
        "token_supply": user_data.get('token_supply'),
        "token_logo": user_data.get('token_logo'),
        "logo_type": user_data.get('logo_type'),
        "token_description": user_data.get('token_description'),
        "user_wallet": user_data.get('user_wallet'),
        "user_info": user_data.get('user_info'),
        "custom_ending": user_data.get('custom_ending'),
        "custom_price": user_data.get('custom_price', 0),
        "is_bonus_used": user_data.get('is_bonus_used', False),
        "total_amount": get_payment_amount(user_data),
        "status": "payment_confirmed"
    }

    filename = "memecoins_data.json"

    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []

        existing_data.append(memecoin_data)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        logging.info(f"{user_data.get('user_info', '[unknown]')} memecoin data saved")
    except Exception as e:
        logging.warning(f"Error saving memecoin data: {e}")


def update_memecoin_data(tx_signature, token_info):
    """Update memecoin data after token creation"""
    filename = "memecoins_data.json"

    try:
        if not os.path.exists(filename):
            return

        with open(filename, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)

        for item in existing_data:
            if item.get('tx_signature') == tx_signature:
                item['status'] = 'token_created'
                item['token_mint'] = token_info.get('tokenMint')
                item['network'] = token_info.get('network', '')

                is_mainnet = "mainnet" in token_info.get('network', '').lower()
                cluster_param = "?cluster=mainnet-beta" if is_mainnet else "?cluster=devnet"
                item['solscan_url'] = f"https://solscan.io/token/{token_info['tokenMint']}{cluster_param}"
                break

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        logging.info(f"Memecoin data updated for transaction {tx_signature[:8]}")
    except Exception as e:
        logging.warning(f"Error updating memecoin data: {e}")


def contains_emoji(text):
    """Check for emoji presence via Unicode categories"""
    if not text:
        return False
    for char in text:
        if unicodedata.category(char) in ['So', 'Sm', 'Sc', 'Sk'] or ord(char) > 0x1F000:
            return True
    return False


def is_media_message(message, allow_photos=False):
    """Check for media content with optional photo allowance"""
    media_items = [
        message.video,
        message.animation,
        message.document,
        message.sticker,
        message.voice,
        message.video_note
    ]

    if not allow_photos:
        media_items.append(message.photo)

    return any(media_items)


async def get_text(key, user_data, action=None):
    """Get text with formatting support"""
    text = LANGUAGES[key]
    if action and '{' in text:
        if key in ['running', 'success', 'error']:
            return text.format(LANGUAGES['actions'][action])
        return text.format(action)
    return text


def get_keyboard(kb_type, user_data=None):
    """Create keyboards"""
    if kb_type == "supply":
        return get_supply_keyboard()
    return None


async def animate_checking(message, animation_symbols):
    """Transaction checking animation"""
    i = 0
    while True:
        try:
            await message.edit_text(animation_symbols[i % len(animation_symbols)])
            await asyncio.sleep(0.3)
            i += 1
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(0.3)


async def message_after_payment(message, state, user_data, tx_info):
    """Message after payment confirmation"""
    from bot import BotStates, start_token_creation

    user_info = user_data.get('user_info', '[unknown_user]')
    logging.info(f"{user_info} sending payment confirmation message")
    await message.answer(LANGUAGES['payment_confirmed_start_creation'])
    await state.set_state(BotStates.creating_token)
    await start_token_creation(message, state, user_data, tx_info)


async def cleanup_user_files(user_data):
    """Clean up temporary user files"""
    logo_path = user_data.get('token_logo', '')
    if user_data.get('logo_type') == 'file' and logo_path and os.path.exists(logo_path):
        try:
            os.remove(logo_path)
            logging.info(f"Temporary file deleted: {logo_path}")
        except Exception as e:
            logging.warning(f"Failed to delete temporary file {logo_path}: {e}")


async def cmd_help(message: types.Message, state: FSMContext):
    """Help command handler"""
    user_data = await state.get_data()
    log_user_action(message.from_user, "requested help")
    await message.answer(await get_text('help_text', user_data))


async def process_during_creation(message: types.Message, state: FSMContext):
    """Handler for messages during token creation"""
    await message.answer(LANGUAGES['please_wait'])


async def check_payment_button(message: types.Message, state: FSMContext):
    """Payment check button handler (for text messages, if any)"""
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(message.from_user))

    logging.info(f"{user_info} sent text message during payment wait")
    pass