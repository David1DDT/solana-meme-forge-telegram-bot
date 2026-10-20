"""Admin commands for managing the Solana mint-wallet pool."""

import logging
import sqlite3
from pathlib import Path

from aiogram import types
from aiogram.fsm.context import FSMContext
from solders.keypair import Keypair

from settings import ADMIN_ID, DEBUG_MODE

MAX_WALLETS_PER_UPLOAD = 1000


def _wallet_database_path() -> Path:
    suffix = "_test" if DEBUG_MODE else ""
    return Path(__file__).resolve().parent.parent / "database" / f"wallets_meme{suffix}.db"


def _connect_wallet_database() -> sqlite3.Connection:
    database_path = _wallet_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.touch(mode=0o600, exist_ok=True)
    database_path.chmod(0o600)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.execute(
        """CREATE TABLE IF NOT EXISTS meme_wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            private_key TEXT NOT NULL UNIQUE,
            public_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'available'
                CHECK (status IN ('available', 'reserved')),
            created_at REAL NOT NULL DEFAULT (julianday('now')),
            updated_at REAL NOT NULL DEFAULT (julianday('now'))
        )"""
    )
    return connection


def get_wallet_database_stats() -> dict[str, int]:
    """Return counts for each wallet-pool status."""
    with _connect_wallet_database() as connection:
        rows = connection.execute(
            "SELECT status, COUNT(*) FROM meme_wallets GROUP BY status"
        ).fetchall()
    counts = {"available": 0, "reserved": 0}
    counts.update({status: count for status, count in rows})
    return counts


async def cmd_db_stats(message: types.Message) -> None:
    """Show the current wallet-pool database counts."""
    if not message.from_user or message.from_user.id != ADMIN_ID:
        await message.answer("Access denied.")
        return

    try:
        counts = get_wallet_database_stats()
    except sqlite3.Error:
        logging.exception("Could not read wallet database statistics")
        await message.answer("Could not read wallet database statistics. Check the bot logs.")
        return

    await message.answer(
        "Wallet database statistics:\n"
        f"Available: {counts['available']}\n"
        f"Reserved: {counts['reserved']}\n"
        f"Total: {sum(counts.values())}"
    )


async def cmd_upload_wallets(message: types.Message, state: FSMContext) -> None:
    """Start an admin-only upload of newline-separated hexadecimal keypairs."""
    if not message.from_user or message.from_user.id != ADMIN_ID:
        await message.answer("Access denied.")
        return

    from bot import BotStates

    await state.set_state(BotStates.uploading_wallets)
    await message.answer(
        "Send up to 1000 Solana private keys, one 128-character hexadecimal key per line. "
        "The keys are stored in the wallet database and will not be echoed."
    )

async def process_admin_message(message: types.Message, state: FSMContext) -> None:
    """Validate and add the admin's newline-separated wallet keys."""
    if not message.from_user or message.from_user.id != ADMIN_ID:
        await state.clear()
        await message.answer("Access denied.")
        return

    if not message.text:
        await message.answer("Send private keys as text, one key per line.")
        return

    private_keys = [line.strip() for line in message.text.splitlines() if line.strip()]
    if not private_keys:
        await message.answer("No private keys were provided.")
        return
    if len(private_keys) > MAX_WALLETS_PER_UPLOAD:
        await message.answer(f"Upload no more than {MAX_WALLETS_PER_UPLOAD} keys at a time.")
        return

    parsed_wallets = []
    invalid_lines = []
    for line_number, private_key in enumerate(message.text.splitlines(), start=1):
        private_key = private_key.strip()
        if not private_key:
            continue
        try:
            if len(private_key) != 128:
                raise ValueError("wrong length")
            keypair = Keypair.from_bytes(bytes.fromhex(private_key))
        except (ValueError, TypeError):
            invalid_lines.append(line_number)
            continue
        parsed_wallets.append((private_key.lower(), str(keypair.pubkey())))

    if invalid_lines:
        await message.answer(
            "Invalid private key format on line(s): "
            + ", ".join(map(str, invalid_lines))
            + ". Expected 128 hexadecimal characters per key. Nothing was imported."
        )
        return

    if len({public_key for _, public_key in parsed_wallets}) != len(parsed_wallets):
        await message.answer("The upload contains duplicate wallets. Nothing was imported.")
        return

    try:
        with _connect_wallet_database() as connection:
            cursor = connection.executemany(
                """INSERT OR IGNORE INTO meme_wallets (private_key, public_key)
                   VALUES (?, ?)""",
                parsed_wallets,
            )
            inserted = cursor.rowcount
    except sqlite3.Error:
        logging.exception("Could not save uploaded wallet keys")
        await message.answer("Could not save the wallets. Check the bot logs.")
        return

    await state.clear()
    await message.answer(
        f"Wallet upload complete. Added {inserted}; "
        f"skipped {len(parsed_wallets) - inserted} already present."
    )
