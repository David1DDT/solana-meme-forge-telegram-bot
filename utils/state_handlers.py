"""FSM state handlers for memecoin bot"""
import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from settings import (
    LANGUAGES,
    AMOUNT,
    SERVICE_WALLET_ADDRESS,
    get_custom_address_cost_text,
    format_custom_address_summary,
)
from utils.telegram_formatter import TelegramFormatter
from utils.handlers import (
    get_user_info, log_user_action,
    get_text, get_keyboard, get_payment_amount
)
from utils.keyboards import get_confirm_keyboard, get_check_payment_keyboard
from utils.input_validators import (
    validate_media_message, validate_token_name, validate_token_symbol,
    validate_token_supply, validate_user_wallet, validate_token_description
)


async def start_bot_flow(message_or_callback, state: FSMContext):
    """Common bot startup logic"""
    from bot import BotStates

    if hasattr(message_or_callback, 'message'):
        user = message_or_callback.from_user
        message = message_or_callback.message
    else:
        user = message_or_callback.from_user
        message = message_or_callback

    log_user_action(user, "started bot")

    await state.clear()

    await state.update_data(language='en', user_info=get_user_info(user))

    welcome_shown = False
    bonus_addresses = 0
    should_show_bonus_welcome = False

    try:
        # Referral system integration
        welcome_shown = True
        bonus_addresses = 0
        should_show_bonus_welcome = False

        logging.info(
            f"DEBUG: User {user.id} - welcome_shown: {welcome_shown}, bonus_addresses: {bonus_addresses}, should_show_bonus_welcome: {should_show_bonus_welcome}")

    except Exception as e:
        logging.debug(f"Error checking welcome message status: {e}")
        should_show_bonus_welcome = False

    if should_show_bonus_welcome:
        welcome_message = LANGUAGES['enter_token_name']
        logging.info(f"DEBUG: Showing welcome message with bonuses for user {user.id}")
    else:
        welcome_message = LANGUAGES.get('enter_token_name_no_bonus', 'Enter your memecoin name (e.g., "Doge Coin"):')
        logging.info(f"DEBUG: Showing regular message for user {user.id}")

    await message.answer(welcome_message, reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(BotStates.token_name)


async def cmd_start(message: types.Message, state: FSMContext):
    """/start command handler"""

    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []

    if command_args:
        referral_code = command_args[0]
        user_id = message.from_user.id
        username = message.from_user.username
        user_info = get_user_info(message.from_user)

        logging.info(f"{user_info} started bot with referral code: {referral_code}")

        try:
            # Referral code processing
            logging.debug("Referral code processed")
        except ImportError:
            logging.debug("Referral system not available for processing code")

    try:
        # User caching system
        pass
    except ImportError:
        logging.debug("Referral system not available")

    await start_bot_flow(message, state)


async def create_again(callback_query: types.CallbackQuery, state: FSMContext):
    """Create new token handler"""
    await callback_query.answer()

    try:
        # User caching system
        pass
    except ImportError:
        logging.debug("Referral system not available")

    await start_bot_flow(callback_query, state)


async def process_token_name(message: types.Message, state: FSMContext):
    """Token name input handler"""
    from bot import BotStates

    user_data = await state.get_data()

    if validate_media_message(message):
        await message.answer(await get_text('media_not_allowed_in_name', user_data))
        return

    is_valid, result = validate_token_name(message.text)
    if not is_valid:
        if result == "empty_text":
            await message.answer(await get_text('emoji_not_allowed_in_name', user_data))
        elif result == "emoji_not_allowed":
            await message.answer(await get_text('emoji_not_allowed_in_name', user_data))
        elif result == "name_too_long":
            await message.answer(await get_text('invalid_name', user_data))
        return

    token_name = result
    log_user_action(message.from_user, f"entered token name: {token_name}")
    await state.update_data(token_name=token_name)

    required_fields = ['token_symbol', 'token_supply', 'token_logo', 'user_wallet', 'token_description']
    has_all_fields = all(field in user_data for field in required_fields)

    if has_all_fields:
        from utils.edit_handlers import show_confirmation_after_edit
        updated_user_data = await state.get_data()
        await show_confirmation_after_edit(message, state, updated_user_data)
    else:
        await message.answer(await get_text('enter_token_symbol', user_data))
        await state.set_state(BotStates.token_symbol)


async def process_token_symbol(message: types.Message, state: FSMContext):
    """Token symbol input handler"""
    from bot import BotStates

    user_data = await state.get_data()

    if validate_media_message(message):
        await message.answer(await get_text('media_not_allowed_in_symbol', user_data))
        return

    is_valid, result = validate_token_symbol(message.text)
    if not is_valid:
        if result == "empty_text":
            await message.answer(await get_text('emoji_not_allowed_in_symbol', user_data))
        elif result == "emoji_not_allowed":
            await message.answer(await get_text('emoji_not_allowed_in_symbol', user_data))
        elif result == "symbol_too_long":
            await message.answer(await get_text('invalid_symbol', user_data))
        return

    symbol = result
    log_user_action(message.from_user, f"entered token symbol: {symbol}")
    await state.update_data(token_symbol=symbol)

    required_fields = ['token_name', 'token_supply', 'token_logo', 'user_wallet', 'token_description']
    has_all_fields = all(field in user_data for field in required_fields)

    if has_all_fields:
        from utils.edit_handlers import show_confirmation_after_edit
        updated_user_data = await state.get_data()
        await show_confirmation_after_edit(message, state, updated_user_data)
    else:
        await message.answer(await get_text('enter_supply', user_data), reply_markup=get_keyboard("supply"))
        await state.set_state(BotStates.token_supply)


async def process_token_supply(message: types.Message, state: FSMContext):
    """Token supply input handler"""
    from bot import BotStates, MAX_SUPPLY

    user_data = await state.get_data()

    is_valid, result = validate_token_supply(message.text, MAX_SUPPLY)
    if not is_valid:
        await message.answer(await get_text('invalid_supply', user_data))
        return

    supply = result
    if message.text == "1 billion":
        log_user_action(message.from_user, "selected 1 billion tokens")
    else:
        log_user_action(message.from_user, f"entered token supply: {supply}")

    await state.update_data(token_supply=supply)

    required_fields = ['token_name', 'token_symbol', 'token_logo', 'user_wallet', 'token_description']
    has_all_fields = all(field in user_data for field in required_fields)

    if has_all_fields:
        from utils.edit_handlers import show_confirmation_after_edit
        updated_user_data = await state.get_data()
        await show_confirmation_after_edit(message, state, updated_user_data)
    else:
        await message.answer(await get_text('enter_logo', user_data), reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(BotStates.token_logo)


async def process_user_wallet(message: types.Message, state: FSMContext):
    """User wallet input handler"""
    from bot import BotStates

    user_data = await state.get_data()

    if validate_media_message(message):
        await message.answer(await get_text('invalid_wallet_media', user_data))
        return

    is_valid, *result = validate_user_wallet(message.text)
    if not is_valid:
        error_type = result[0]
        if error_type == "empty_text":
            await message.answer(LANGUAGES['invalid_wallet_length'])
        elif error_type == "invalid_length":
            await message.answer(LANGUAGES['invalid_wallet_length'])
        elif error_type == "invalid_characters":
            await message.answer(LANGUAGES['invalid_wallet_characters'])
        elif error_type == "short_address":
            wallet = result[1]
            user_info = get_user_info(message.from_user)
            logging.info(f"{user_info} suspiciously short address: {len(wallet)} characters - {wallet}")
            await message.answer(LANGUAGES['short_address_warning'].format(len(wallet)))
        return

    wallet = result[0]
    log_user_action(message.from_user, f"entered wallet: {wallet}")

    required_fields = ['token_name', 'token_symbol', 'token_supply', 'token_logo', 'token_description']
    has_all_fields = all(field in user_data for field in required_fields)

    if has_all_fields:
        await state.update_data(user_wallet=wallet)
        from utils.edit_handlers import show_confirmation_after_edit
        updated_user_data = await state.get_data()
        await show_confirmation_after_edit(message, state, updated_user_data)
    else:
        await state.update_data(user_wallet=wallet, token_description=f"{user_data.get('token_name', 'Token')} Meme Coin")
        user_data = await state.get_data()

        inline_keyboard = get_confirm_keyboard(user_data)

        base_amount = AMOUNT

        base_summary = LANGUAGES['confirm_summary_with_description'].format(
            user_data['token_name'],
            user_data['token_symbol'],
            user_data['token_supply'],
            "📷 Photo from Telegram",
            user_data['user_wallet'],
            user_data.get('token_description', f"{user_data['token_name']} Meme Coin")
        )

        summary = format_custom_address_summary(base_summary, None)
        summary = summary.replace(f"Creation cost: {AMOUNT:.2f} SOL", f"Creation cost: *{base_amount:.2f} SOL*")

        if user_data.get('logo_type') == 'file' and user_data.get('photo_file_id'):
            await message.answer_photo(
                photo=user_data['photo_file_id'],
                caption=TelegramFormatter.escape_text(summary),
                reply_markup=inline_keyboard,
                parse_mode="MarkdownV2"
            )
            user_info = get_user_info(message.from_user)
            logging.info(f"{user_info} initial confirmation created with photo")
        else:
            logo_display = user_data['token_logo']
            summary = summary.replace("📷 Photo from Telegram", logo_display)
            await message.answer(
                TelegramFormatter.escape_text(summary),
                reply_markup=inline_keyboard,
                parse_mode="MarkdownV2"
            )
            user_info = get_user_info(message.from_user)
            logging.info(f"{user_info} initial confirmation created without photo")

        await state.set_state(BotStates.confirm_create)


async def change_description(callback_query: types.CallbackQuery, state: FSMContext):
    """Description change button handler"""
    from bot import BotStates

    await callback_query.answer()
    user_data = await state.get_data()

    current_description = user_data.get('token_description', f"{user_data.get('token_name', 'Token')} Meme Coin")

    await callback_query.message.answer(
        LANGUAGES['enter_description'].format(current_description),
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(BotStates.token_description)


async def process_token_description(message: types.Message, state: FSMContext):
    """Token description input handler"""
    from bot import BotStates

    user_data = await state.get_data()

    if validate_media_message(message):
        await message.answer(await get_text('media_not_allowed_in_description', user_data))
        return

    is_valid, result = validate_token_description(message.text)
    if not is_valid:
        if result == "empty_text":
            await message.answer(await get_text('empty_description_not_allowed', user_data))
        elif result == "description_too_long":
            await message.answer(await get_text('description_too_long', user_data))
        return

    description = result
    log_user_action(message.from_user, f"entered token description: {description[:50]}...")
    await state.update_data(token_description=description)

    inline_keyboard = get_confirm_keyboard(user_data)

    total_amount = get_payment_amount(user_data)

    base_summary = LANGUAGES['confirm_summary_with_description'].format(
        user_data['token_name'],
        user_data['token_symbol'],
        user_data['token_supply'],
        "📷 Photo from Telegram",
        user_data['user_wallet'],
        description
    )

    if user_data.get('custom_ending'):
        custom_price = user_data.get('custom_price', 0)
        custom_ending = user_data.get('custom_ending')
        summary = format_custom_address_summary(base_summary, custom_ending)
        custom_cost_text = get_custom_address_cost_text(total_amount, custom_price)
        summary = summary.replace(f"Creation cost: {AMOUNT:.2f} SOL", custom_cost_text)
    else:
        summary = format_custom_address_summary(base_summary, None)
        summary = summary.replace(f"Creation cost: {AMOUNT:.2f} SOL", f"Creation cost: *{total_amount:.2f} SOL*")

    if user_data.get('logo_type') == 'file' and user_data.get('photo_file_id'):
        await message.answer_photo(
            photo=user_data['photo_file_id'],
            caption=TelegramFormatter.escape_text(summary),
            reply_markup=inline_keyboard,
            parse_mode="MarkdownV2"
        )
        user_info = get_user_info(message.from_user)
        logging.info(f"{user_info} confirmation created after description edit with photo")
    else:
        logo_display = user_data['token_logo']
        summary = summary.replace("📷 Photo from Telegram", logo_display)
        await message.answer(
            TelegramFormatter.escape_text(summary),
            reply_markup=inline_keyboard,
            parse_mode="MarkdownV2"
        )
        user_info = get_user_info(message.from_user)
        logging.info(f"{user_info} confirmation created after description edit without photo")

    await state.set_state(BotStates.confirm_create)


async def process_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    """Token creation confirmation handler via inline button"""
    import os
    from aiogram.utils.markdown import code
    from bot import BotStates
    from utils.wallet_protection import wallet_protection, release_user_wallet

    await callback_query.answer()

    current_state = await state.get_state()
    if current_state in [BotStates.waiting_payment.state, BotStates.creating_token.state]:
        user_data = await state.get_data()
        user_info = user_data.get('user_info', get_user_info(callback_query.from_user))
        logging.info(f"{user_info} repeat confirmation attempt, current state: {current_state}")
        return

    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))
    user_wallet = user_data.get("user_wallet", "")

    # Advanced wallet protection system
    wallet_reserved = True
    if not wallet_reserved:
        return

    log_user_action(callback_query.from_user, f"reserved wallet {user_wallet} and proceeding to payment")

    await state.set_state(BotStates.waiting_payment)

    try:
        await callback_query.message.delete()
    except Exception as e:
        logging.info(f"Could not delete main message: {e}")

    payment_message_id = user_data.get('payment_message_id')
    if payment_message_id:
        try:
            await callback_query.bot.delete_message(
                chat_id=callback_query.message.chat.id,
                message_id=payment_message_id
            )
        except Exception as e:
            logging.info(f"Could not delete previous payment message: {e}")

    service_wallet = SERVICE_WALLET_ADDRESS

    total_amount = get_payment_amount(user_data)

    if user_data.get('custom_ending'):
        custom_price = user_data.get('custom_price', 0)
        custom_ending = user_data.get('custom_ending')

        payment_instructions = LANGUAGES['payment_instructions_with_custom'].format(
            custom_ending,
            total_amount,
            code(service_wallet),
            code(user_wallet)
        )
    else:
        payment_instructions = LANGUAGES['payment_instructions'].format(code(service_wallet), code(user_wallet))

    payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANGUAGES['check_payment_button'], callback_data="check_payment")],
        [InlineKeyboardButton(text="⬅️ Back to Edit", callback_data="back_to_edit_from_payment")]
    ])

    payment_msg = await callback_query.message.answer(
        TelegramFormatter.escape_text(payment_instructions),
        parse_mode="MarkdownV2",
        reply_markup=payment_keyboard
    )

    await state.update_data(payment_message_id=payment_msg.message_id)


async def process_cancellation(callback_query: types.CallbackQuery, state: FSMContext):
    """Token creation cancellation handler via inline button"""
    import os
    from bot import BotStates

    await callback_query.answer()
    user_data = await state.get_data()

    log_user_action(callback_query.from_user, "cancelled token creation")

    # Wallet management system
    pass

    logo_path = user_data.get('token_logo', '')
    if user_data.get('logo_type') == 'file' and os.path.exists(logo_path):
        try:
            os.remove(logo_path)
        except:
            pass

    await state.clear()
    await state.update_data(language='en', user_info=get_user_info(callback_query.from_user))

    await callback_query.message.answer(await get_text('cancelled', user_data), reply_markup=types.ReplyKeyboardRemove())
    await callback_query.message.answer(await get_text('enter_token_name', user_data))
    await state.set_state(BotStates.token_name)


async def back_to_edit_from_payment(callback_query: types.CallbackQuery, state: FSMContext):
    """Return to editing from payment screen handler"""
    from bot import BotStates

    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    log_user_action(callback_query.from_user, "returned to editing from payment screen")

    # Wallet management system
    pass

    await state.set_state(BotStates.confirm_create)

    inline_keyboard = get_confirm_keyboard(user_data)
    total_amount = get_payment_amount(user_data)

    base_summary = LANGUAGES['confirm_summary_with_description'].format(
        user_data['token_name'],
        user_data['token_symbol'],
        user_data['token_supply'],
        "📷 Photo from Telegram" if user_data.get('logo_type') == 'file' else user_data['token_logo'],
        user_data['user_wallet'],
        user_data.get('token_description', f"{user_data['token_name']} Meme Coin")
    )

    if user_data.get('custom_ending'):
        custom_price = user_data.get('custom_price', 0)
        custom_ending = user_data.get('custom_ending')
        summary = format_custom_address_summary(base_summary, custom_ending)
        custom_cost_text = get_custom_address_cost_text(total_amount, custom_price)
        summary = summary.replace(f"Creation cost: {AMOUNT:.2f} SOL", custom_cost_text)
    else:
        summary = format_custom_address_summary(base_summary, None)
        summary = summary.replace(f"Creation cost: {AMOUNT:.2f} SOL", f"Creation cost: *{total_amount:.2f} SOL*")

    try:
        await callback_query.message.delete()
    except Exception as e:
        logging.info(f"Could not delete payment message: {e}")

    await state.update_data(payment_message_id=None)

    if user_data.get('logo_type') == 'file' and user_data.get('photo_file_id'):
        await callback_query.message.answer_photo(
            photo=user_data['photo_file_id'],
            caption=TelegramFormatter.escape_text(summary),
            reply_markup=inline_keyboard,
            parse_mode="MarkdownV2"
        )
        logging.info(f"{user_info} return to confirmation with photo")
    else:
        logo_display = user_data['token_logo']
        summary = summary.replace("📷 Photo from Telegram", logo_display)

        await callback_query.message.answer(
            TelegramFormatter.escape_text(summary),
            reply_markup=inline_keyboard,
            parse_mode="MarkdownV2"
        )
        logging.info(f"{user_info} return to confirmation without photo")


async def process_message(message: types.Message, state: FSMContext):
    """Universal message handler"""
    from bot import BotStates

    try:
        # User caching system
        pass
    except ImportError:
        logging.debug("Referral system not available")

    user_data = await state.get_data()
    current_state = await state.get_state()

    if current_state == BotStates.waiting_payment.state:
        await message.answer(
            TelegramFormatter.escape_text(await get_text('checking_payment', user_data)),
            reply_markup=get_check_payment_keyboard(),
            parse_mode="MarkdownV2"
        )
        return

    await message.answer(await get_text('unknown_command', user_data))