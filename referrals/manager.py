"""Referral system manager for token creation integration"""
import logging
import asyncio
import json
from decimal import Decimal, ROUND_HALF_UP
from settings import AMOUNT, REFERRAL_TOKEN_COMMISSION, REFERRAL_CUSTOM_COMMISSION
from referrals.middleware import call_referral_db_safe


def round_sol(value, decimals=6):
    """Round SOL amount to specified decimals to avoid floating point precision issues"""
    return float(Decimal(str(value)).quantize(Decimal('0.' + '0' * decimals), rounding=ROUND_HALF_UP))


async def send_referral_payment(wallet_address, total_amount_sol, payment_breakdown):
    """Send single referral payout via Node.js with breakdown details"""
    try:
        logging.info(f"Sending referral payout: {total_amount_sol:.6f} SOL -> {wallet_address}")
        logging.info(f"Payment breakdown: {payment_breakdown}")

        payment_details_json = json.dumps(payment_breakdown)

        process = await asyncio.create_subprocess_exec(
            'node', 'referrals/payment-sender.js',
            wallet_address,
            str(total_amount_sol),
            payment_details_json,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd='.'
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            try:
                stdout_text = stdout.decode().strip()
                if not stdout_text:
                    logging.error("❌ Empty response from payment script")
                    return {'success': False, 'error': 'Empty response'}

                json_start = stdout_text.find('{')
                if json_start == -1:
                    logging.error(f"❌ No JSON found in response: {stdout_text}")
                    return {'success': False, 'error': 'No JSON in response'}

                json_text = stdout_text[json_start:]
                result = json.loads(json_text)

                if result.get('success'):
                    logging.info(f"✅ Referral payout sent: {result.get('txHash')}")
                    return result
                else:
                    logging.error(f"❌ Payout error: {result.get('error')}")
                    return result

            except json.JSONDecodeError as e:
                logging.error(f"❌ Response parsing error: {stdout.decode()}")
                logging.error(f"❌ JSON error: {e}")
                return {'success': False, 'error': 'Invalid response format'}
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logging.error(f"❌ Payment script error: {error_msg}")
            return {'success': False, 'error': error_msg}

    except Exception as e:
        logging.error(f"❌ Critical error sending referral payout: {e}")
        return {'success': False, 'error': str(e)}


def calculate_referral_commission(user_data):
    """Calculate referral commission with precise rounding using configurable rates"""
    try:
        base_commission = round_sol(AMOUNT * REFERRAL_TOKEN_COMMISSION)

        custom_commission = 0
        custom_price = 0

        if user_data.get('custom_ending') and user_data.get('custom_price'):
            custom_price = user_data.get('custom_price', 0)
            custom_commission = round_sol(custom_price * REFERRAL_CUSTOM_COMMISSION)

        total_commission = round_sol(base_commission + custom_commission)

        logging.info(f"Referral commission calculation:")
        logging.info(f"  Base commission ({REFERRAL_TOKEN_COMMISSION*100}% of {AMOUNT}): {base_commission:.6f} SOL")
        logging.info(f"  Custom commission ({REFERRAL_CUSTOM_COMMISSION*100}% of {custom_price}): {custom_commission:.6f} SOL")
        logging.info(f"  Total commission: {total_commission:.6f} SOL")

        return {
            'base_commission': base_commission,
            'custom_commission': custom_commission,
            'total_commission': total_commission,
            'custom_price': custom_price
        }

    except Exception as e:
        logging.error(f"Error calculating referral commission: {e}")
        return {
            'base_commission': 0,
            'custom_commission': 0,
            'total_commission': 0,
            'custom_price': 0
        }


async def process_referral_payment(user_data, tx_info):
    """
    Process referral payout after successful memecoin creation
    Sends single payment instead of two separate ones

    Args:
        user_data (dict): User data who created the token
        tx_info (dict): Token creation transaction info

    Returns:
        dict: Processing result
    """
    try:
        user_info = user_data.get('user_info', '[unknown_user]')
        user_id = None

        if user_info and user_info.startswith('[') and ':' in user_info:
            try:
                user_id = int(user_info.split('[')[1].split(':')[0])
            except (ValueError, IndexError):
                logging.warning(f"Failed to extract user_id from user_info: {user_info}")
                return {'success': False, 'error': 'Invalid user_info format'}

        if not user_id:
            logging.warning(f"user_id not found in user_data for referral payout")
            return {'success': False, 'error': 'User ID not found'}

        logging.info(f"{user_info} checking for referrer for payout...")

        referrer_info = await call_referral_db_safe('getReferrerWithConnect', user_id)

        if not referrer_info or not isinstance(referrer_info, dict):
            logging.info(f"{user_info} no referrer found, no payout needed")
            return {'success': True, 'message': 'No referrer found'}

        referrer_id = referrer_info.get('user_id')
        referrer_wallet = referrer_info.get('wallet_address')

        if not referrer_wallet:
            logging.info(f"{user_info} referrer {referrer_id} has no payout wallet")
            return {'success': True, 'message': 'Referrer has no wallet'}

        logging.info(f"{user_info} found referrer {referrer_id} with wallet {referrer_wallet}")

        commission_data = calculate_referral_commission(user_data)
        total_commission = commission_data['total_commission']

        if total_commission <= 0:
            logging.info(f"{user_info} commission is 0, no payout needed")
            return {'success': True, 'message': 'Zero commission'}

        payment_breakdown = {
            'base_commission': commission_data['base_commission'],
            'custom_commission': commission_data['custom_commission'],
            'total_commission': total_commission,
            'token_cost': AMOUNT,
            'custom_price': commission_data['custom_price'],
            'custom_ending': user_data.get('custom_ending', ''),
            'type': 'referral_commission'
        }

        result = await send_referral_payment(
            referrer_wallet,
            total_commission,
            payment_breakdown
        )

        if result.get('success'):
            tx_hash = result.get("txHash")

            if commission_data['base_commission'] > 0:
                await call_referral_db_safe(
                    'recordPaymentWithConnect',
                    referrer_id, user_id, commission_data['base_commission'],
                    'token', tx_hash
                )
                logging.info(f"✅ Base commission recorded in DB: {commission_data['base_commission']:.6f} SOL")

            if commission_data['custom_commission'] > 0:
                await call_referral_db_safe(
                    'recordPaymentWithConnect',
                    referrer_id, user_id, commission_data['custom_commission'],
                    'custom', tx_hash
                )
                logging.info(f"✅ Custom commission recorded in DB: {commission_data['custom_commission']:.6f} SOL")

            logging.info(f"✅ {user_info} referral payout completed: {total_commission:.6f} SOL sent to referrer {referrer_id}")

            return {
                'success': True,
                'referrer_id': referrer_id,
                'referrer_wallet': referrer_wallet,
                'total_commission': total_commission,
                'tx_hash': tx_hash,
                'payment_breakdown': payment_breakdown
            }
        else:
            error_msg = result.get('error', 'Unknown error')
            logging.error(f"❌ {user_info} payout failed: {error_msg}")

            return {
                'success': False,
                'error': error_msg,
                'referrer_id': referrer_id,
                'referrer_wallet': referrer_wallet,
                'total_commission': total_commission
            }

    except Exception as e:
        logging.error(f"❌ Critical error processing referral payout: {e}")
        return {'success': False, 'error': str(e)}


async def add_or_update_user(user_id, username, referred_by=None):
    """Add or update user in referral system (safe)"""
    try:
        result = await call_referral_db_safe(
            'addOrUpdateUserWithConnect',
            user_id, username, referred_by
        )

        if result and isinstance(result, dict):
            logging.info(f"User {user_id} added/updated in referral system")
            return result
        else:
            logging.debug(f"Failed to add/update user {user_id} (DB unavailable)")
            return None

    except Exception as e:
        logging.debug(f"Error adding/updating user {user_id}: {e}")
        return None