"""Payment handler for memecoin bot"""
import logging, asyncio
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import code
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from settings import LANGUAGES, AMOUNT, SERVICE_WALLET_ADDRESS
from utils.telegram_formatter import TelegramFormatter
from utils.payment_checker import get_payment_amount


async def check_payment(callback_query: types.CallbackQuery, state: FSMContext):
    """Payment check handler"""
    from bot import BotStates
    from utils.handlers import get_user_info, animate_checking, message_after_payment

    await callback_query.answer()
    user_data = await state.get_data()
    user_info = user_data.get('user_info', get_user_info(callback_query.from_user))

    current_state = await state.get_state()
    if current_state == BotStates.creating_token.state:
        payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGES['check_payment_button'], callback_data="check_payment")],
            [InlineKeyboardButton(text="⬅️ Back to Edit", callback_data="back_to_edit_from_payment")]
        ])

        try:
            await callback_query.message.edit_text(
                LANGUAGES['please_wait'],
                reply_markup=payment_keyboard
            )
        except Exception as e:
            logging.info(f"Could not edit message: {e}")

        logging.info(f"{user_info} payment check attempt during token creation")
        return

    if user_data.get('payment_check_in_progress'):
        logging.info(f"{user_info} payment check already in progress, ignoring duplicate request")
        return

    await state.update_data(payment_check_in_progress=True)

    try:
        sender_wallet = user_data.get("user_wallet")
        service_wallet = SERVICE_WALLET_ADDRESS
        if not service_wallet:
            raise RuntimeError("SERVICE_WALLET_ADDRESS is missing from the environment")

        expected_amount = get_payment_amount(user_data)

        logging.info(f"{user_info} checking payment, expected amount: {expected_amount} SOL")
        logging.info(f"DEBUG payment_handler: user_data for amount calculation: {user_data}")

        custom_info = ""
        if user_data.get('custom_ending'):
            custom_price = user_data.get('custom_price', 0)
            is_bonus_used = user_data.get('is_bonus_used', False)
            if is_bonus_used:
                custom_info = f" (with free custom address ...{user_data['custom_ending']})"
            else:
                custom_info = f" (with custom address ...{user_data['custom_ending']} for {custom_price} SOL)"

        animation_symbols = LANGUAGES['animation_symbols']
        animation_task = asyncio.create_task(
            animate_checking(callback_query.message, animation_symbols)
        )

        try:
            from utils.payment_checker import check_payments, mark_transaction_in_process

            logging.info(f"{user_info} calling check_payments with parameters:")
            logging.info(f"  service_wallet: {service_wallet}")
            logging.info(f"  sender_wallet: {sender_wallet}")
            logging.info(f"  expected_amount: {expected_amount} SOL")
            logging.info(f"  user_data: {user_data}")

            new_matches, existing_matches, tx_info = await check_payments(
                service_wallet, sender_wallet, user_data, 5, user_info
            )

            animation_task.cancel()
            try:
                await animation_task
            except asyncio.CancelledError:
                pass

            is_valid = new_matches > 0 or existing_matches > 0
            logging.info(
                f"{user_info} check result{custom_info}: valid={is_valid}, new={new_matches}, existing={existing_matches}")

            payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=LANGUAGES['check_payment_button'], callback_data="check_payment")],
                [InlineKeyboardButton(text="⬅️ Back to Edit", callback_data="back_to_edit_from_payment")]
            ])

            if is_valid and tx_info:
                tx_signature = tx_info.get('signature', '')
                logging.info(f"{user_info} payment found: {tx_signature[:8]}...")
                logging.info(f"{user_info} token created: {tx_info.get('token_created', False)}")
                logging.info(f"{user_info} in process: {tx_info.get('in_process', False)}")

                if tx_info.get("token_created", False):
                    logging.info(f"{user_info} repeat transaction usage attempt")
                    text = LANGUAGES['transaction_already_used'].format(
                        tx_info['amount'], tx_info['time'],
                        code(tx_info['sender']), code(tx_info['receiver']),
                        code(tx_info['signature'])
                    )
                    try:
                        await callback_query.message.edit_text(
                            TelegramFormatter.escape_text(text),
                            reply_markup=payment_keyboard,
                            parse_mode="MarkdownV2"
                        )
                    except Exception as edit_error:
                        if "message is not modified" in str(edit_error):
                            logging.info(f"{user_info} message unchanged, skipping update")
                        else:
                            raise edit_error
                    return

                if tx_info.get("in_process", False):
                    logging.info(f"{user_info} transaction already in token creation process")
                    text = LANGUAGES['transaction_in_process'].format(
                        tx_info['amount'], tx_info['time'],
                        code(tx_info['sender']), code(tx_info['receiver']),
                        code(tx_info['signature'])
                    )
                    await callback_query.message.edit_text(
                        TelegramFormatter.escape_text(text),
                        parse_mode="MarkdownV2"
                    )
                    return

                logging.info(f"{user_info} transaction valid and token not created - starting creation")

                transaction_text = LANGUAGES['new_transaction_found'].format(
                    tx_info['amount'], tx_info['time'],
                    code(tx_info['sender']), code(tx_info['receiver']),
                    code(tx_info['signature'])
                )

                try:
                    await callback_query.message.edit_text(
                        TelegramFormatter.escape_text(transaction_text),
                        reply_markup=payment_keyboard,
                        parse_mode="MarkdownV2"
                    )
                except Exception as edit_error:
                    if "message is not modified" in str(edit_error):
                        logging.info(f"{user_info} message unchanged, skipping update")
                    else:
                        raise edit_error

                mark_transaction_in_process(tx_signature)
                await state.update_data(processing_tx_signature=tx_signature)
                await message_after_payment(callback_query.message, state, user_data, tx_info)

            else:
                logging.info(f"{user_info} payment not found{custom_info}")

                if user_data.get('custom_ending'):
                    custom_price = user_data.get('custom_price', 0)
                    custom_ending = user_data.get('custom_ending')
                    is_bonus_used = user_data.get('is_bonus_used', False)

                    if is_bonus_used:
                        text = LANGUAGES['transaction_not_found'].format(
                            code(service_wallet),
                            code(sender_wallet)
                        )
                        text = text.replace("Make sure you sent 0.09 SOL",
                                          f"Make sure you sent {expected_amount:.2f} SOL (FREE custom address ...{custom_ending})")
                    else:
                        text = LANGUAGES['transaction_not_found_with_custom'].format(
                            expected_amount, AMOUNT, custom_price, custom_ending,
                            expected_amount, code(service_wallet), code(sender_wallet)
                        )
                else:
                    text = LANGUAGES['transaction_not_found'].format(
                        code(service_wallet),
                        code(sender_wallet)
                    )

                try:
                    await callback_query.message.edit_text(
                        TelegramFormatter.escape_text(text),
                        reply_markup=payment_keyboard,
                        parse_mode="MarkdownV2"
                    )
                except Exception as edit_error:
                    if "message is not modified" in str(edit_error):
                        logging.info(f"{user_info} message unchanged, skipping update")
                    else:
                        raise edit_error

        except Exception as e:
            animation_task.cancel()
            try:
                await animation_task
            except asyncio.CancelledError:
                pass

            logging.info(f"{user_info} payment check error: {e}")
            error_text = LANGUAGES['payment_check_error'].format(str(e))

            payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=LANGUAGES['check_payment_button'], callback_data="check_payment")],
                [InlineKeyboardButton(text="⬅️ Back to Edit", callback_data="back_to_edit_from_payment")]
            ])

            await callback_query.message.edit_text(
                error_text,
                reply_markup=payment_keyboard
            )

    finally:
        await state.update_data(payment_check_in_progress=False)