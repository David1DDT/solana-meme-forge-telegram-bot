"""Solana payment verification and transaction-use tracking."""

import asyncio
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp
from dotenv import load_dotenv
from solders.pubkey import Pubkey

from settings import SERVICE_WALLET_ADDRESS, SOLANA_NETWORK

load_dotenv()

PAYMENT_MAX_AGE_SECONDS = 30 * 60
LAMPORTS_PER_SOL = 1_000_000_000
_database_lock = threading.Lock()


def get_payment_amount(user_data):
    """Calculate the expected total using the same rules as the payment UI."""
    from utils.handlers import get_payment_amount as calculate_payment_amount

    return calculate_payment_amount(user_data)


def _rpc_url() -> str:
    network = SOLANA_NETWORK
    if network == "mainnet-beta":
        cluster = "mainnet"
        fallback = "https://api.mainnet-beta.solana.com"
    elif network == "devnet":
        cluster = "devnet"
        fallback = "https://api.devnet.solana.com"
    else:
        raise RuntimeError(f"Unsupported Solana network: {network}")

    api_key = os.getenv("HELIUS_API_KEY", "").strip()
    if api_key:
        return f"https://{cluster}.helius-rpc.com/?api-key={api_key}"
    return fallback


def _database_path() -> Path:
    db_path = Path(__file__).resolve().parent.parent / "database" / "payment-transactions.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def _connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path(), timeout=10)
    connection.execute(
        """CREATE TABLE IF NOT EXISTS payment_transactions (
            signature TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )"""
    )
    return connection


def mark_transaction_in_process(signature: str) -> None:
    """Persist that a verified payment is being used to create a token."""
    if not signature:
        raise ValueError("Transaction signature is required")

    with _database_lock, _connect_database() as connection:
        connection.execute(
            """INSERT INTO payment_transactions (signature, status, updated_at)
               VALUES (?, 'in_process', ?)
               ON CONFLICT(signature) DO UPDATE SET
                   status = 'in_process', updated_at = excluded.updated_at""",
            (signature, int(time.time())),
        )


def _get_transaction_status(signature: str) -> Optional[str]:
    with _database_lock, _connect_database() as connection:
        row = connection.execute(
            "SELECT status FROM payment_transactions WHERE signature = ?",
            (signature,),
        ).fetchone()
    return row[0] if row else None


async def _rpc_call(session: aiohttp.ClientSession, method: str, params: list):
    async with session.post(
        _rpc_url(),
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    ) as response:
        response.raise_for_status()
        payload = await response.json()

    if "error" in payload:
        raise RuntimeError(f"Solana RPC {method} failed: {payload['error']}")
    return payload.get("result")


def _extract_matching_transfer(transaction, sender: str, receiver: str) -> int:
    """Sum native SOL transfers from sender to receiver in a parsed transaction."""
    meta = transaction.get("meta") or {}
    if meta.get("err") is not None:
        return 0

    message = (transaction.get("transaction") or {}).get("message") or {}
    lamports = 0
    instructions = list(message.get("instructions") or [])
    for inner_group in meta.get("innerInstructions") or []:
        instructions.extend(inner_group.get("instructions") or [])

    for instruction in instructions:
        parsed = instruction.get("parsed")
        if instruction.get("program") != "system" or not isinstance(parsed, dict):
            continue
        if parsed.get("type") != "transfer":
            continue

        info = parsed.get("info") or {}
        if info.get("source") == sender and info.get("destination") == receiver:
            try:
                lamports += int(info["lamports"])
            except (KeyError, TypeError, ValueError):
                continue

    return lamports


def _format_timestamp(block_time: int) -> str:
    return datetime.fromtimestamp(block_time).strftime("%Y-%m-%d %H:%M:%S")


async def check_payments(
    service_wallet: str,
    sender_wallet: str,
    user_data: dict,
    limit: int = 5,
    user_info: str = "",
):
    """Find a recent confirmed SOL payment matching sender, recipient, and amount."""
    if not service_wallet:
        raise RuntimeError("SERVICE_WALLET_ADDRESS is missing from the environment")
    if not sender_wallet:
        raise ValueError("Sender wallet is missing")

    try:
        Pubkey.from_string(service_wallet)
        Pubkey.from_string(sender_wallet)
    except ValueError as error:
        raise ValueError("Payment sender or recipient is not a valid Solana address") from error

    expected_lamports = int(round(get_payment_amount(user_data) * LAMPORTS_PER_SOL))
    if expected_lamports <= 0:
        raise ValueError("Expected payment amount must be greater than zero")

    request_limit = max(1, min(int(limit), 100))
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        signatures = await _rpc_call(
            session,
            "getSignaturesForAddress",
            [service_wallet, {"limit": request_limit, "commitment": "confirmed"}],
        )
        if not isinstance(signatures, list):
            raise RuntimeError("Solana RPC returned an invalid signature list")

        for signature_entry in signatures:
            signature = signature_entry.get("signature")
            block_time = signature_entry.get("blockTime")
            if (
                not signature
                or signature_entry.get("err") is not None
                or not isinstance(block_time, (int, float))
                or time.time() - block_time > PAYMENT_MAX_AGE_SECONDS
                or time.time() < block_time
            ):
                continue

            transaction = await _rpc_call(
                session,
                "getTransaction",
                [
                    signature,
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed",
                        "maxSupportedTransactionVersion": 0,
                    },
                ],
            )
            if not isinstance(transaction, dict):
                continue

            paid_lamports = _extract_matching_transfer(
                transaction, sender_wallet, service_wallet
            )
            if paid_lamports < expected_lamports:
                continue

            status = _get_transaction_status(signature)
            tx_info = {
                "signature": signature,
                "amount": paid_lamports / LAMPORTS_PER_SOL,
                "time": _format_timestamp(int(block_time)),
                "sender": sender_wallet,
                "receiver": service_wallet,
                "token_created": status == "token_created",
                "in_process": status == "in_process",
            }
            existing_matches = int(status is not None)
            new_matches = int(status is None)
            logging.info("%s matching confirmed payment found", user_info or "Payment checker")
            return new_matches, existing_matches, tx_info

    return 0, 0, None


async def close_session() -> None:
    """Retained for compatibility with application shutdown."""
