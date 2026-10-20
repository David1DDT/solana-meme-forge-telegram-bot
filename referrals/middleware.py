"""Middleware for automatic user addition to referral DB"""
import logging
import asyncio
import json
from utils.handlers import get_user_info

BOT_IDS = {7637247149, 7671046210}


async def call_referral_db_safe(method_name, *args):
    """Safe referral DB method call (no errors if DB unavailable)"""
    try:
        db_script = 'referrals/db-manager.js'

        js_args = []
        for arg in args:
            if arg is None:
                js_args.append('null')
            elif isinstance(arg, str):
                escaped_arg = arg.replace('"', '\\"').replace("'", "\\'")
                js_args.append(f'"{escaped_arg}"')
            elif isinstance(arg, (int, float)):
                js_args.append(str(arg))
            elif isinstance(arg, bool):
                js_args.append('true' if arg else 'false')
            else:
                escaped_arg = str(arg).replace('"', '\\"').replace("'", "\\'")
                js_args.append(f'"{escaped_arg}"')

        temp_script = f"""
const {{ referralDbManager }} = require('./{db_script}');

async function callMethod() {{
    try {{
        const result = await referralDbManager.{method_name}({', '.join(js_args)});
        
        process.stdout.write(JSON.stringify(result));
    }} catch (error) {{
        process.stderr.write('ERROR: ' + error.message);
        process.exit(1);
    }}
}}

callMethod();
"""

        process = await asyncio.create_subprocess_exec(
            'node', '-e', temp_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd='.'
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
        except asyncio.TimeoutError:
            process.kill()
            logging.warning(f"Timeout calling {method_name} in referral DB")
            return None

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logging.debug(f"Referral DB unavailable for {method_name}: {error_msg}")
            return None

        output = stdout.decode().strip()

        if output and not output.startswith('ERROR:'):
            try:
                json_start = output.find('{')
                json_end = output.rfind('}')

                if json_start != -1 and json_end != -1 and json_end > json_start:
                    json_text = output[json_start:json_end + 1]
                    parsed_result = json.loads(json_text)
                    return parsed_result
                else:
                    parsed_result = json.loads(output)
                    return parsed_result
            except json.JSONDecodeError as e:
                logging.warning(f"Failed to parse JSON response for {method_name}")
                logging.debug(f"Raw output: {output}")
                logging.debug(f"JSON error: {e}")
                return None

        return None

    except Exception as e:
        logging.debug(f"Referral DB unavailable for {method_name}: {e}")
        return None


async def ensure_user_in_referral_db(user):
    """
    Ensure user exists in referral DB
    Add if not (without referrer) with 3 bonus custom addresses
    Works without errors even if DB unavailable
    """
    try:
        from settings import BONUS_CUSTOM_ADDRESSES

        user_id = user.id
        username = user.username
        user_info_log = get_user_info(user)

        if user_id in BOT_IDS:
            logging.debug(f"{user_info_log} is a bot, skipping referral DB")
            return False

        existing_user = await call_referral_db_safe('getUserInfoWithConnect', user_id)

        if existing_user is None:
            logging.debug(f"{user_info_log} not found in referral DB, adding...")

            result = await call_referral_db_safe(
                'addOrUpdateUserWithConnect',
                user_id,
                username,
                None
            )

            if result:
                logging.info(f"{user_info_log} added to referral DB with {BONUS_CUSTOM_ADDRESSES} bonus addresses")
                return True
            else:
                logging.warning(f"{user_info_log} failed to add to referral DB (DB unavailable)")
                return False
        else:
            if username and isinstance(existing_user, dict) and existing_user.get('username') != username:
                await call_referral_db_safe(
                    'addOrUpdateUserWithConnect',
                    user_id,
                    username,
                    None
                )
                logging.debug(f"{user_info_log} updated username in referral DB")

            bonus_count = existing_user.get('bonus_custom_addresses') if isinstance(existing_user, dict) else 0
            if bonus_count is None:
                logging.info(f"{user_info_log} has NULL bonus_custom_addresses, migration needed")
            else:
                logging.debug(f"{user_info_log} has {bonus_count} bonus addresses")

            return True

    except Exception as e:
        logging.debug(f"Error ensuring user in referral DB: {e}")
        return False


_user_check_cache = set()


async def ensure_user_cached(user):
    """Cached version to avoid multiple checks"""
    user_id = user.id

    if user_id in BOT_IDS:
        return False

    if user_id in _user_check_cache:
        return True

    success = await ensure_user_in_referral_db(user)
    if success:
        _user_check_cache.add(user_id)

    return success


def clear_user_cache():
    """Clear cache (for periodic refresh)"""
    global _user_check_cache
    _user_check_cache.clear()


async def ensure_user_exists_with_retry(user):
    """
    Ensure user exists in DB with retries
    Used before critical operations (e.g., wallet saving)
    """
    user_info_log = get_user_info(user)

    if user.id in BOT_IDS:
        logging.debug(f"{user_info_log} is a bot, skipping referral DB retry")
        return False

    success = await ensure_user_cached(user)
    if success:
        return True

    if user.id in _user_check_cache:
        _user_check_cache.remove(user.id)

    logging.info(f"{user_info_log} retrying user creation in referral DB")
    success = await ensure_user_cached(user)

    if success:
        logging.info(f"{user_info_log} successfully ensured user exists in referral DB (retry)")
        return True
    else:
        logging.error(f"{user_info_log} failed to ensure user exists in referral DB after retry")
        return False