"""Referral system handlers for memecoin bot"""
import logging
import hashlib
import asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.handlers import get_user_info, log_user_action
from utils.input_validators import validate_user_wallet
from referrals.middleware import call_referral_db_safe, ensure_user_cached


class ReferralStates(StatesGroup):
    waiting_wallet = State()


def generate_referral_code(user_id):
    """Generate deterministic referral code from user_id - secure version"""
    import hashlib

    secret = 'your_secret_key_here_change_in_production'
    combined = f"{secret}_{user_id}_{secret}"

    hash_object = hashlib.sha256(combined.encode())
    hash_hex = hash_object.hexdigest()

    hash_value = int(hash_hex[:12], 16)

    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    code = ""

    for _ in range(6):
        code = chars[hash_value % 36] + code
        hash_value //= 36

    return code


def parse_referral_code(code):
    """Check if referral code is valid"""
    if not code or len(code) != 6:
        return None

    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    for char in code.upper():
        if char not in chars:
            return None

    return code.upper()


def get_referral_keyboard(user_info):
    """Create referral system keyboard"""
    keyboard = []

    if user_info and isinstance(user_info, dict) and user_info.get('wallet_address'):
        keyboard.append([
            InlineKeyboardButton(text="📝 Change Wallet", callback_data="ref_change_wallet")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(text="➕ Add Payout Wallet", callback_data="ref_add_wallet")
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def cmd_referral(message: types.Message, state: FSMContext):
    """Command /referral - show referral information"""
    from settings import REFERRAL_TOKEN_COMMISSION, REFERRAL_CUSTOM_COMMISSION, AMOUNT

    user_id = message.from_user.id
    user_info_log = get_user_info(message.from_user)

    if user_id in [1234567890, 5987654321]:
        logging.warning(f"Bot {user_id} tried to access referral system")
        return

    await ensure_user_cached(message.from_user)
    log_user_action(message.from_user, "opened referral system")

    try:
        stats = await call_referral_db_safe('getUserStatsWithConnect', user_id)
        if stats:
            logging.info(f"DEBUG: User {user_id} stats: {stats}")
        else:
            logging.warning(f"DEBUG: No stats found for user {user_id}")
    except Exception as e:
        logging.error(f"DEBUG: Error getting stats for user {user_id}: {e}")

    user_info = await call_referral_db_safe('getUserInfoWithConnect', user_id)

    logging.info(f"DEBUG: Raw user_info for {user_id}: {user_info}")

    if user_info and isinstance(user_info, dict):
        total_earned_tokens = user_info.get('total_earned_tokens', 0)
        total_earned_custom = user_info.get('total_earned_custom', 0)
        total_earned = total_earned_tokens + total_earned_custom
        total_referrals = user_info.get('total_referrals', 0)
        wallet_address = user_info.get('wallet_address')

        logging.info(
            f"DEBUG: User {user_id} earnings - tokens: {total_earned_tokens}, custom: {total_earned_custom}, total: {total_earned}")

        referred_by = user_info.get('referred_by')
        if referred_by == -1:
            referral_status = ""
        elif referred_by is None:
            referral_status = ""
        else:
            referral_status = ""
    else:
        total_earned_tokens = 0
        total_earned_custom = 0
        total_earned = 0
        total_referrals = 0
        wallet_address = None
        referral_status = ""

    token_commission_percent = int(REFERRAL_TOKEN_COMMISSION * 100)
    custom_commission_percent = int(REFERRAL_CUSTOM_COMMISSION * 100)

    token_commission_amount = round(AMOUNT * REFERRAL_TOKEN_COMMISSION, 6)

    text = f"""🔗 <b>Referral System</b>

📊 <b>Statistics:</b>
👥 Invited users: <b>{total_referrals}</b>
💰 Earned from tokens ({token_commission_percent}%): <b>{total_earned_tokens:.4f} SOL</b>
🎯 Earned from custom addresses ({custom_commission_percent}%): <b>{total_earned_custom:.4f} SOL</b>
💎 <b>Total earnings: {total_earned:.4f} SOL</b>

"""

    if wallet_address:
        referral_code = generate_referral_code(user_id)
        referral_link = f"https://t.me/{(await message.bot.get_me()).username}?start={referral_code}"

        text += f"""✅ <b>Wallet connected - link is active!</b>
💳 <b>Payout wallet:</b>
<code>{wallet_address}</code>

🔗 <b>Your link:</b>
<code>{referral_link}</code>"""
    else:
        text += f"""❌ <b>Not set</b>
💳 <b>Payout wallet:</b>

⚠️ <b>Add wallet to receive payouts!</b>"""

    text += f"""

💡 <b>How it works:</b>
• Share your link with friends
• Get <b>{token_commission_percent}%</b> from each token created by your friends ({token_commission_amount:.3f} SOL)
• Get <b>{custom_commission_percent}%</b> from custom address upgrades by your friends
• Payouts are automatic after token creation"""

    if referral_status:
        text += f"\n\n<i>{referral_status}</i>"

    keyboard = get_referral_keyboard(user_info)

    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def ref_add_wallet(callback_query: types.CallbackQuery, state: FSMContext):
    """Add wallet handler"""
    await callback_query.answer()

    if callback_query.from_user.id in [1234567890, 54587654321]:
        return

    log_user_action(callback_query.from_user, "adding referral payout wallet")

    await ensure_user_cached(callback_query.from_user)

    await callback_query.message.answer(
        "💳 <b>Add Payout Wallet</b>\n\n"
        "Enter your Solana address where referral payouts will be sent:\n\n"
        "⚠️ Make sure the address is correct - payouts cannot be reversed!",
        parse_mode="HTML"
    )

    await state.set_state(ReferralStates.waiting_wallet)


async def ref_change_wallet(callback_query: types.CallbackQuery, state: FSMContext):
    """Change wallet handler"""
    await callback_query.answer()

    if callback_query.from_user.id in [1234567890, 3447654321]:
        return

    log_user_action(callback_query.from_user, "changing referral payout wallet")

    await ensure_user_cached(callback_query.from_user)

    user_info = await call_referral_db_safe('getUserInfoWithConnect', callback_query.from_user.id)

    if user_info and isinstance(user_info, dict):
        current_wallet = user_info.get('wallet_address', 'Not set')
    else:
        current_wallet = 'Not set'

    await callback_query.message.answer(
        f"💳 <b>Change Payout Wallet</b>\n\n"
        f"Current wallet: <code>{current_wallet}</code>\n\n"
        f"Enter new Solana address:",
        parse_mode="HTML"
    )

    await state.set_state(ReferralStates.waiting_wallet)


async def process_wallet_input(message: types.Message, state: FSMContext):
    """Process wallet input"""
    user_id = message.from_user.id

    if user_id in [1234567890, 4987654321]:
        return

    user_info_log = get_user_info(message.from_user)

    await ensure_user_cached(message.from_user)

    is_valid, *result = validate_user_wallet(message.text)

    if not is_valid:
        error_type = result[0]
        if error_type == "empty_text":
            await message.answer("❌ Address cannot be empty. Try again:")
        elif error_type == "invalid_length":
            await message.answer("❌ Invalid address length. Solana addresses must be 32-44 characters. Try again:")
        elif error_type == "invalid_characters":
            await message.answer("❌ Invalid characters. Use only valid base58 characters. Try again:")
        elif error_type == "short_address":
            wallet = result[1]
            await message.answer(
                f"⚠️ Warning: {len(wallet)}-character address is unusual for Solana (usually 43-44). Check correctness!")
            await save_wallet_and_finish(message, state, wallet, user_id)
        return

    wallet = result[0]
    await save_wallet_and_finish(message, state, wallet, user_id)


async def save_wallet_and_finish(message, state, wallet, user_id):
    """Save wallet and finish process"""
    from referrals.middleware import ensure_user_exists_with_retry

    user_info_log = get_user_info(message.from_user)
    log_user_action(message.from_user, f"set referral wallet: {wallet}")

    user_exists = await ensure_user_exists_with_retry(message.from_user)

    if not user_exists:
        await message.answer(
            "❌ <b>Database connection error</b>\n\n"
            "Unable to connect to referral database. Please try again later or contact support.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    success = await call_referral_db_safe('setWalletAddressWithConnect', user_id, wallet)

    if success:
        await message.answer(
            f"✅ <b>Wallet successfully connected!</b>\n\n"
            f"💳 Address: <code>{wallet}</code>\n\n"
            f"🎉 Your referral link is now active and you'll receive automatic payouts!",
            parse_mode="HTML"
        )

        await cmd_referral(message, state)
    else:
        logging.error(f"{user_info_log} failed to save wallet {wallet} - DB operation failed")

        await message.answer(
            "❌ <b>Error saving wallet</b>\n\n"
            "Database operation failed. Please try again later or contact support.",
            parse_mode="HTML"
        )

    await state.clear()


async def process_referral_code(user_id, username, referral_code):
    """Process referral code on /start - secure referral linking protection"""
    try:
        if user_id in [1234567890, 5987654321]:
            return False

        valid_code = parse_referral_code(referral_code)
        if not valid_code:
            logging.info(f"Invalid referral code: {referral_code}")
            return False

        logging.info(f"Processing referral code {valid_code} for user {user_id}")

        existing_user = await call_referral_db_safe('getUserInfoWithConnect', user_id)

        if existing_user is not None:
            if isinstance(existing_user, dict):
                referred_by = existing_user.get('referred_by')
                if referred_by is not None and referred_by != -1:
                    logging.info(f"⚠️ User {user_id} already has a referrer: {referred_by}")
                    return False
                elif referred_by == -1:
                    logging.info(f"⚠️ User {user_id} was already processed without referrer, cannot set referrer now")
                    return False
                logging.info(f"User {user_id} exists with NULL referrer (legacy), trying to set referrer")
            else:
                logging.warning(f"Unexpected user data format for {user_id}: {existing_user}")
                return False

        referrer_id = await call_referral_db_safe('findReferrerByCodeWithConnect', valid_code)

        logging.info(f"DEBUG: Searching for referrer with code {valid_code}, found: {referrer_id}")

        if not referrer_id:
            logging.info(f"⚠️ Referrer with code {valid_code} not found")
            if existing_user is None:
                await call_referral_db_safe('addOrUpdateUserWithConnect', user_id, username, None)
            return False

        if referrer_id == user_id:
            logging.info(f"⚠️ Self-referral attempt for user {user_id}")
            if existing_user is None:
                await call_referral_db_safe('addOrUpdateUserWithConnect', user_id, username, None)
            return False

        if existing_user is None:
            add_result = await call_referral_db_safe(
                'addOrUpdateUserWithConnect',
                user_id, username, referrer_id
            )
        else:
            add_result = await call_referral_db_safe(
                'addOrUpdateUserWithConnect',
                user_id, username, referrer_id
            )

        logging.info(f"DEBUG: Add/update result: {add_result}")

        if add_result and isinstance(add_result, dict):
            if add_result.get('updated') and add_result.get('referrerSet', False):
                logging.info(f"✅ Referral link established: {user_id} <- {referrer_id} (code: {valid_code})")
                return True
            elif add_result.get('updated'):
                logging.info(f"User {user_id} updated but referrer not set")
                return False
            else:
                logging.warning(f"Failed to establish referral link for {user_id}")
                return False
        else:
            logging.error(f"Failed to add/update user {user_id} to DB")
            return False

    except Exception as e:
        logging.error(f"Error processing referral code: {e}")
        return False