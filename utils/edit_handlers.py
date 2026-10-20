"""Token parameter editing handlers"""
import logging
import asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext
from settings import LANGUAGES, AMOUNT, get_custom_address_cost_text, format_custom_address_summary
from utils.telegram_formatter import TelegramFormatter
from utils.handlers import get_user_info, log_user_action, get_payment_amount
from utils.keyboards import get_edit_data_keyboard, get_confirm_keyboard


async def edit_data(callback_query: types.CallbackQuery, state: FSMContext):
    """Show data editing menu"""
    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    log_user_action(callback_query.from_user, "opened editing menu")

    keyboard = get_edit_data_keyboard()

    if callback_query.message.photo:
        try:
            await callback_query.message.delete()
            await callback_query.message.answer(
                LANGUAGES['edit_data_menu'],
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Error handling photo message in edit_data: {e}")
            await callback_query.message.answer(
                LANGUAGES['edit_data_menu'],
                reply_markup=keyboard
            )
    else:
        try:
            await callback_query.message.edit_text(
                LANGUAGES['edit_data_menu'],
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Error editing text message in edit_data: {e}")
            await callback_query.message.answer(
                LANGUAGES['edit_data_menu'],
                reply_markup=keyboard
            )


async def change_name(callback_query: types.CallbackQuery, state: FSMContext):
    """Change token name"""
    from bot import BotStates

    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    log_user_action(callback_query.from_user, "changing token name")

    current_name = user_data.get('token_name', '')
    edit_msg = await callback_query.message.answer(
        f"Current name: `{current_name}`\n\nEnter new token name:",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="MarkdownV2"
    )
    await state.update_data(edit_message_id=edit_msg.message_id)
    await state.set_state(BotStates.token_name)


async def change_symbol(callback_query: types.CallbackQuery, state: FSMContext):
    """Change token symbol"""
    from bot import BotStates

    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    log_user_action(callback_query.from_user, "changing token symbol")

    current_symbol = user_data.get('token_symbol', '')
    edit_msg = await callback_query.message.answer(
        f"Current symbol: `{current_symbol}`\n\nEnter new token symbol:",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="MarkdownV2"
    )
    await state.update_data(edit_message_id=edit_msg.message_id)
    await state.set_state(BotStates.token_symbol)


async def change_supply(callback_query: types.CallbackQuery, state: FSMContext):
    """Change token supply"""
    from bot import BotStates
    from utils.keyboards import get_supply_keyboard

    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    log_user_action(callback_query.from_user, "changing token supply")

    current_supply = user_data.get('token_supply', '')
    edit_msg = await callback_query.message.answer(
        f"Current supply: `{current_supply}`\n\nEnter new token supply:",
        reply_markup=get_supply_keyboard(),
        parse_mode="MarkdownV2"
    )
    await state.update_data(edit_message_id=edit_msg.message_id)
    await state.set_state(BotStates.token_supply)


async def change_logo(callback_query: types.CallbackQuery, state: FSMContext):
    """Change token logo"""
    from bot import BotStates

    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    log_user_action(callback_query.from_user, "changing token logo")

    current_logo = user_data.get('token_logo', '')
    if user_data.get('logo_type') == 'file':
        logo_text = "📷 Uploaded photo"
    else:
        logo_text = current_logo

    edit_msg = await callback_query.message.answer(
        f"Current logo: {logo_text}\n\nSend new photo or enter image URL:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.update_data(edit_message_id=edit_msg.message_id)
    await state.set_state(BotStates.token_logo)


async def change_wallet(callback_query: types.CallbackQuery, state: FSMContext):
    """Change user wallet"""
    from bot import BotStates

    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    log_user_action(callback_query.from_user, "changing wallet")

    current_wallet = user_data.get('user_wallet', '')
    edit_msg = await callback_query.message.answer(
        f"Current wallet: `{current_wallet}`\n\nEnter new Solana wallet address:",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="MarkdownV2"
    )
    await state.update_data(edit_message_id=edit_msg.message_id)
    await state.set_state(BotStates.user_wallet)


async def change_description(callback_query: types.CallbackQuery, state: FSMContext):
    """Change token description"""
    from bot import BotStates

    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    log_user_action(callback_query.from_user, "changing token description")

    current_description = user_data.get('token_description', f"{user_data.get('token_name', 'Token')} Meme Coin")
    edit_msg = await callback_query.message.answer(
        LANGUAGES['enter_description'].format(current_description),
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.update_data(edit_message_id=edit_msg.message_id)
    await state.set_state(BotStates.token_description)


async def back_to_confirmation_from_edit(callback_query: types.CallbackQuery, state: FSMContext):
    """Handler for back to confirmation button from edit menu (preserves custom address)"""
    from bot import BotStates

    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    log_user_action(callback_query.from_user, "returned to confirmation from edit menu")

    inline_keyboard = get_confirm_keyboard()

    total_amount = get_payment_amount(user_data)

    base_summary = LANGUAGES['confirm_summary_with_description'].format(
        user_data['token_name'],
        user_data['token_symbol'],
        user_data['token_supply'],
        "📷 Photo from Telegram",
        user_data['user_wallet'],
        user_data.get('token_description', f"{user_data['token_name']} Meme Coin")
    )

    if user_data.get('custom_ending'):
        custom_price = user_data.get('custom_price', 0)
        custom_ending = user_data.get('custom_ending')
        is_bonus_used = user_data.get('is_bonus_used', False)

        summary = format_custom_address_summary(base_summary, custom_ending)

        if is_bonus_used and len(custom_ending) == 4:
            custom_cost_text = f"Creation cost: *{total_amount:.2f} SOL* ({AMOUNT:.2f} token + FREE address)"
        else:
            custom_cost_text = get_custom_address_cost_text(total_amount, custom_price)
        summary = summary.replace(f"Creation cost: {AMOUNT:.2f} SOL", custom_cost_text)
    else:
        summary = format_custom_address_summary(base_summary, None)
        summary = summary.replace(f"Creation cost: {AMOUNT:.2f} SOL", f"Creation cost: *{total_amount:.2f} SOL*")

    try:
        if user_data.get('logo_type') == 'file' and user_data.get('photo_file_id'):
            await callback_query.message.delete()
            await callback_query.message.answer_photo(
                photo=user_data['photo_file_id'],
                caption=TelegramFormatter.escape_text(summary),
                reply_markup=inline_keyboard,
                parse_mode="MarkdownV2"
            )
            logging.info(f"{user_info} returned to confirmation with photo (custom preserved)")
        else:
            logo_display = user_data['token_logo']
            summary = summary.replace("📷 Photo from Telegram", logo_display)

            try:
                await callback_query.message.edit_text(
                    TelegramFormatter.escape_text(summary),
                    reply_markup=inline_keyboard,
                    parse_mode="MarkdownV2"
                )
            except Exception:
                await callback_query.message.delete()
                await callback_query.message.answer(
                    TelegramFormatter.escape_text(summary),
                    reply_markup=inline_keyboard,
                    parse_mode="MarkdownV2"
                )
            logging.info(f"{user_info} returned to confirmation without photo (custom preserved)")

    except Exception as e:
        logging.error(f"Error returning to confirmation: {e}")
        if user_data.get('logo_type') == 'file' and user_data.get('photo_file_id'):
            await callback_query.message.answer_photo(
                photo=user_data['photo_file_id'],
                caption=TelegramFormatter.escape_text(summary),
                reply_markup=inline_keyboard,
                parse_mode="MarkdownV2"
            )
        else:
            logo_display = user_data['token_logo']
            summary = summary.replace("📷 Photo from Telegram", logo_display)
            await callback_query.message.answer(
                TelegramFormatter.escape_text(summary),
                reply_markup=inline_keyboard,
                parse_mode="MarkdownV2"
            )

    await state.set_state(BotStates.confirm_create)


async def show_confirmation_after_edit(message, state, user_data):
    """Show confirmation after editing parameter"""
    from bot import BotStates

    inline_keyboard = get_confirm_keyboard()

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
        is_bonus_used = user_data.get('is_bonus_used', False)

        summary = format_custom_address_summary(base_summary, custom_ending)

        if is_bonus_used and len(custom_ending) == 4:
            custom_cost_text = f"Creation cost: *{total_amount:.2f} SOL* ({AMOUNT:.2f} token + FREE address)"
        else:
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
        user_info = user_data.get('user_info', '[unknown]')
        logging.info(f"{user_info} confirmation created after edit with photo")
    else:
        await message.answer(
            TelegramFormatter.escape_text(summary),
            reply_markup=inline_keyboard,
            parse_mode="MarkdownV2"
        )
        user_info = user_data.get('user_info', '[unknown]')
        logging.info(f"{user_info} confirmation created after edit without photo")

    await state.set_state(BotStates.confirm_create)