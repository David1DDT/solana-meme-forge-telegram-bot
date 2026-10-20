"""Custom address handlers for memecoin bot"""
import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from settings import LANGUAGES, AMOUNT, get_custom_address_cost_text, format_custom_address_summary
from utils.telegram_formatter import TelegramFormatter
from utils.handlers import get_user_info, log_user_action, get_payment_amount
from utils.keyboards import get_custom_address_keyboard, get_confirm_keyboard
from utils.custom_address_manager import get_available_custom_endings, calculate_custom_price


def is_user_state_valid(user_data):
    """Check if user state contains required fields"""
    required_fields = ['token_name', 'token_symbol', 'token_supply', 'user_wallet']
    return all(field in user_data for field in required_fields)


async def handle_invalid_state(callback_query: types.CallbackQuery, state: FSMContext):
    """Handle invalid user state with restart message"""
    await state.clear()
    restart_message = (
        "🔄 Bot has been updated!\n\n"
        "Your session has expired. Please start over by typing /start"

    )

    try:
        if callback_query.message.photo:
            await callback_query.message.delete()
            await callback_query.message.answer(restart_message)
        else:
            await callback_query.message.edit_text(restart_message)
    except Exception as e:
        logging.error(f"Error handling invalid state: {e}")
        await callback_query.message.answer(restart_message)


async def handle_message_update(callback_query: types.CallbackQuery, text, keyboard, parse_mode="MarkdownV2"):
    """Universal message update handler to avoid duplication"""
    try:
        if callback_query.message.photo:
            await callback_query.message.delete()
            await callback_query.message.answer(text, reply_markup=keyboard, parse_mode=parse_mode)
        else:
            await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode=parse_mode)
    except Exception as e:
        logging.error(f"Error updating message: {e}")
        await callback_query.message.answer(text, reply_markup=keyboard, parse_mode=parse_mode)


async def bonus_info(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler for bonus info button"""
    await callback_query.answer(
        "🎁 You received 3 FREE 4-character custom addresses as a welcome gift! "
        "Use them when creating tokens to get premium addresses at no extra cost.",
        show_alert=True
    )


async def buy_custom_address(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler for buying custom address button with bonus support"""
    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    # Check if user state is valid
    if not is_user_state_valid(user_data):
        logging.warning(f"{user_info} invalid state when requesting custom address")
        await handle_invalid_state(callback_query, state)
        return

    log_user_action(callback_query.from_user, "custom")

    try:
        available_endings = get_available_custom_endings()

        if not available_endings:
            back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_confirmation")
            ]])
            await handle_message_update(callback_query, LANGUAGES['no_custom_addresses'], back_keyboard, parse_mode=None)
            return

        # Get user bonus addresses
        bonus_addresses = 0
        try:
            from referrals.middleware import call_referral_db_safe
            bonus_result = await call_referral_db_safe('getBonusCustomAddressesWithConnect',
                                                       callback_query.from_user.id)
            bonus_addresses = bonus_result if bonus_result is not None else 0
            logging.info(f"DEBUG: User {callback_query.from_user.id} has {bonus_addresses} bonus addresses")
        except Exception as e:
            logging.error(f"Error getting bonus addresses: {e}")
            bonus_addresses = 0

        keyboard = get_custom_address_keyboard(available_endings, bonus_addresses)

        message_text = LANGUAGES['available_custom_addresses']
        if bonus_addresses > 0:
            message_text += f"\n\n🎁 You have {bonus_addresses} FREE 4-character addresses!"

        await handle_message_update(callback_query, TelegramFormatter.escape_text(message_text), keyboard)

        logging.info(f"{user_info} custom: {len(available_endings)}, bonus: {bonus_addresses}")

    except Exception as e:
        logging.error(f"{user_info} error: {e}")
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_confirmation")
        ]])

        error_text = f"❌ Error loading custom addresses: {str(e)}\n\nPlease try:\n1. Type /start to restart\n2. If still not working - contact @Meme_Forge_Support_bot"
        await handle_message_update(callback_query, error_text, back_keyboard, parse_mode=None)


async def select_custom_ending(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler for selecting specific custom ending with bonus support"""
    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    # Check if user state is valid
    if not is_user_state_valid(user_data):
        logging.warning(f"{user_info} invalid state when selecting custom ending")
        await handle_invalid_state(callback_query, state)
        return

    # Extract ending from callback data
    ending = callback_query.data.split(":", 1)[1]
    custom_price = calculate_custom_price(ending)

    # Check bonus availability for 4-character endings
    is_bonus_used = False
    if len(ending) == 4:
        try:
            from referrals.middleware import call_referral_db_safe
            bonus_addresses = await call_referral_db_safe('getBonusCustomAddressesWithConnect',
                                                          callback_query.from_user.id)
            logging.info(
                f"DEBUG: User {callback_query.from_user.id} selecting {ending}, bonus_addresses: {bonus_addresses}")

            if bonus_addresses and bonus_addresses > 0:
                is_bonus_used = True
                custom_price = 0
                logging.info(f"{user_info} will use bonus for 4-char ending: {ending} (not deducted yet)")
            else:
                logging.info(f"{user_info} no bonus available for 4-char ending: {ending}")
        except Exception as e:
            logging.error(f"Error checking bonus availability: {e}")

    log_user_action(callback_query.from_user,
                    f"custom: {ending} ({'WILL USE BONUS' if is_bonus_used else f'{custom_price} SOL'})")

    # Save selection state
    await state.update_data(
        custom_ending=ending,
        custom_price=custom_price,
        is_bonus_used=is_bonus_used
    )

    # Get updated user data and calculate total amount
    user_data = await state.get_data()
    total_amount = get_payment_amount(user_data)

    logging.info(
        f"DEBUG: After selection - ending: {ending}, will_use_bonus: {is_bonus_used}, custom_price: {custom_price}, total_amount: {total_amount}")

    # Show confirmation with custom address info
    inline_keyboard = get_confirm_keyboard(user_data)

    # Create updated summary
    base_summary = LANGUAGES['confirm_summary_with_description'].format(
        user_data['token_name'],
        user_data['token_symbol'],
        user_data['token_supply'],
        "📷 Photo from Telegram" if user_data.get('logo_type') == 'file' else user_data['token_logo'],
        user_data['user_wallet'],
        user_data.get('token_description', f"{user_data['token_name']} Meme Coin")
    )

    # Add custom address info
    summary = format_custom_address_summary(base_summary, ending)

    # Format cost text with bonus info
    if is_bonus_used:
        custom_cost_text = f"Creation cost: *{total_amount:.2f} SOL* ({AMOUNT:.2f} token + FREE address)"
    else:
        custom_cost_text = get_custom_address_cost_text(total_amount, custom_price)
    summary = summary.replace(f"Creation cost: {AMOUNT:.2f} SOL", custom_cost_text)

    # Display message
    if user_data.get('logo_type') == 'file' and user_data.get('photo_file_id'):
        await callback_query.message.delete()
        await callback_query.message.answer_photo(
            photo=user_data['photo_file_id'],
            caption=TelegramFormatter.escape_text(summary),
            reply_markup=inline_keyboard,
            parse_mode="MarkdownV2"
        )
    else:
        logo_display = user_data['token_logo']
        summary = summary.replace("📷 Photo from Telegram", logo_display)
        await callback_query.message.edit_text(
            TelegramFormatter.escape_text(summary),
            reply_markup=inline_keyboard,
            parse_mode="MarkdownV2"
        )

    logging.info(
        f"{user_info} custom {ending}, new: {total_amount} SOL, bonus: {is_bonus_used}")


async def back_to_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler for back to confirmation button"""
    from bot import BotStates

    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    # Check if user state is valid
    if not is_user_state_valid(user_data):
        logging.warning(f"{user_info} invalid state when going back to confirmation")
        await handle_invalid_state(callback_query, state)
        return

    log_user_action(callback_query.from_user, "back")

    # Remove custom address selection
    if 'custom_ending' in user_data:
        await state.update_data(
            custom_ending=None,
            custom_price=None,
            is_bonus_used=False
        )
        logging.info(f"{user_info} cancelled")

    # Show original confirmation screen
    user_data = await state.get_data()
    inline_keyboard = get_confirm_keyboard()

    # Create base summary
    base_summary = LANGUAGES['confirm_summary_with_description'].format(
        user_data['token_name'],
        user_data['token_symbol'],
        user_data['token_supply'],
        "📷 Photo from Telegram",
        user_data['user_wallet'],
        user_data.get('token_description', f"{user_data['token_name']} Meme Coin")
    )

    # Add default custom address text with proper formatting
    summary = format_custom_address_summary(base_summary, None)
    summary = summary.replace(f"Creation cost: {AMOUNT:.2f} SOL", f"Creation cost: *{AMOUNT:.2f} SOL*")

    if user_data.get('logo_type') == 'file' and user_data.get('photo_file_id'):
        await callback_query.message.delete()
        await callback_query.message.answer_photo(
            photo=user_data['photo_file_id'],
            caption=TelegramFormatter.escape_text(summary),
            reply_markup=inline_keyboard,
            parse_mode="MarkdownV2"
        )
        logging.info(f"{user_info} back")
    else:
        logo_display = user_data['token_logo']
        summary = summary.replace("📷 Photo from Telegram", logo_display)

        await callback_query.message.edit_text(
            TelegramFormatter.escape_text(summary),
            reply_markup=inline_keyboard,
            parse_mode="MarkdownV2"
        )
        logging.info(f"{user_info} back")

    await state.set_state(BotStates.confirm_create)


async def cancel_custom_address(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler for canceling custom address selection"""
    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    log_user_action(callback_query.from_user, "cancelled")

    # Remove custom address selection
    await state.update_data(custom_ending=None, custom_price=None)

    await callback_query.message.edit_text(LANGUAGES['custom_address_purchase_cancelled'])

    # Return to normal confirmation flow
    await back_to_confirmation(callback_query, state)


async def confirm_custom_address(message: types.Message, state: FSMContext):
    """Handler for confirming custom address purchase"""
    from bot import BotStates

    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(message.from_user))

    # Check if user state is valid
    if not is_user_state_valid(user_data):
        logging.warning(f"{user_info} invalid state when confirming custom address")
        await state.clear()
        await message.answer(
            "🔄 Bot has been updated!\n\n"
            "Your session has expired. Please start over by typing /start\n\n"
            "If you continue having issues, contact @Meme_Forge_Support_bot"
        )
        return

    custom_ending = user_data.get('custom_ending')
    if not custom_ending:
        await message.answer("❌ Custom ending not selected\n\nPlease try:\n1. Type /start to restart\n2. If still not working - contact @Meme_Forge_Support_bot")
        await state.set_state(BotStates.confirm_create)
        return

    log_user_action(message.from_user, f"confirmed: {custom_ending}")

    # Continue with normal confirmation flow but with custom address
    await state.set_state(BotStates.confirm_create)

    # Trigger normal confirmation process
    from utils.state_handlers import process_confirmation
    await process_confirmation(message, state)