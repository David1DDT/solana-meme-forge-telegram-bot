"""Keyboards for memecoin bot"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from settings import LANGUAGES, CUSTOM_ADDRESS_PRICES, CUSTOM_ADDRESS_EMOJIS


def get_supply_keyboard():
    """Token supply selection keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="1 billion")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_confirm_keyboard(user_data=None):
    """Confirmation keyboard with inline buttons: Buy custom address, Edit Data, Create Token"""

    inline_buttons = [
        [InlineKeyboardButton(text="⚙️ Edit Data", callback_data="edit_data")],
        [InlineKeyboardButton(text=LANGUAGES['buy_custom_address'], callback_data="buy_custom_address")],
        [InlineKeyboardButton(text="🚀 Launch Token", callback_data="confirm_creation")]
    ]

    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=inline_buttons)

    return inline_keyboard


def get_edit_data_keyboard():
    """Token data editing keyboard (2x3)"""
    inline_buttons = [
        [
            InlineKeyboardButton(text="Name", callback_data="change_name"),
            InlineKeyboardButton(text="Symbol", callback_data="change_symbol")
        ],
        [
            InlineKeyboardButton(text="Supply", callback_data="change_supply"),
            InlineKeyboardButton(text="Logo", callback_data="change_logo")
        ],
        [
            InlineKeyboardButton(text="Wallet", callback_data="change_wallet"),
            InlineKeyboardButton(text="Description", callback_data="change_description")
        ],
        [
            InlineKeyboardButton(text="⬅️ Back", callback_data="back_from_edit")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=inline_buttons)


def get_custom_address_keyboard(available_endings, bonus_addresses=0):
    """Keyboard with available custom endings (2 per row) with bonus support"""
    keyboard = []
    current_row = []

    for ending_data in available_endings:
        ending = ending_data['ending']
        length = ending_data['length']
        count = ending_data['count']

        price = CUSTOM_ADDRESS_PRICES.get(length, 0)
        emoji = CUSTOM_ADDRESS_EMOJIS.get(length, "💎")

        if price > 0:
            if length == 4 and bonus_addresses > 0:
                button_text = f"{ending} (FREE) {emoji}"
            else:
                button_text = f"{ending} ({price:.2f} SOL) {emoji}"

            callback_data = f"custom_ending:{ending}"
            current_row.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

            if len(current_row) == 2:
                keyboard.append(current_row)
                current_row = []

    if current_row:
        keyboard.append(current_row)

    if bonus_addresses > 0:
        bonus_text = f"🎁 Free 4-char addresses: {bonus_addresses} remaining"
        keyboard.append([InlineKeyboardButton(text=bonus_text, callback_data="bonus_info")])

    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_confirmation")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_check_payment_keyboard(user_data=None):
    """Payment check keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=LANGUAGES['check_payment_button'], callback_data="check_payment")
    ]])


def get_create_again_keyboard():
    """Create new token keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=LANGUAGES['create_again_button'], callback_data="create_again")
    ]])