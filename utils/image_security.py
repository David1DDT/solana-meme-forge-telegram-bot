"""Validation helpers for user-supplied token images."""

import asyncio
import ipaddress
import io
import socket
import warnings
from urllib.parse import urljoin, urlsplit

import aiohttp
from aiohttp.abc import AbstractResolver
from aiohttp.resolver import DefaultResolver
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_SIZE = 4 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
IMAGE_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


def is_valid_image_format(url: str) -> bool:
    """Return whether a URL path has a supported raster-image extension."""
    try:
        return urlsplit(url).path.lower().endswith(tuple(IMAGE_EXTENSIONS))
    except (TypeError, ValueError):
        return False


def _validate_image_data(data: bytes) -> tuple[bool, str]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in IMAGE_FORMATS:
                    return False, "❌ Unsupported image format. Use JPG, PNG, GIF, or WEBP."
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    return False, "❌ Image dimensions are too large."
                image.verify()
        return True, "✅ Image passed security checks."
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
            Image.DecompressionBombWarning, ValueError):
        return False, "❌ The file is not a valid or safe image."


async def check_telegram_photo_security(file_path: str) -> tuple[bool, str]:
    """Check a downloaded Telegram photo's size and decoded image format."""
    try:
        with open(file_path, "rb") as image_file:
            data = image_file.read(MAX_IMAGE_SIZE + 1)
    except OSError:
        return False, "❌ Could not read the uploaded image."

    if len(data) > MAX_IMAGE_SIZE:
        return False, "❌ Image exceeds the 4 MB limit."
    return _validate_image_data(data)


def _parse_http_url(url: str):
    if not isinstance(url, str):
        return None, "❌ Enter a valid HTTP or HTTPS image URL."

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return None, "❌ Enter a valid HTTP or HTTPS image URL."

    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 80, 443}
    ):
        return None, "❌ Only public HTTP or HTTPS image URLs are allowed."

    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None

    if address is not None and not address.is_global:
        return None, "❌ URLs to private or local network addresses are not allowed."

    return parsed, None


async def _resolve_public_host(host: str, port: int) -> None:
    try:
        results = await asyncio.get_running_loop().getaddrinfo(
            host, port, type=socket.SOCK_STREAM
        )
    except OSError as error:
        raise ValueError("❌ Could not verify the image URL host.") from error

    if not results or any(
        not ipaddress.ip_address(result[4][0]).is_global for result in results
    ):
        raise ValueError("❌ URLs to private or local network addresses are not allowed.")


async def check_url_image_security(url: str) -> tuple[bool, str]:
    """Validate URL syntax and ensure its host resolves only to public addresses."""
    parsed, error = _parse_http_url(url)
    if error:
        return False, error

    try:
        await _resolve_public_host(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except ValueError as validation_error:
        return False, str(validation_error)

    return True, url


class _PublicResolver(AbstractResolver):
    """Prevent HTTP requests, including redirects, from resolving to private IPs."""

    def __init__(self):
        self._resolver = DefaultResolver()

    async def resolve(self, host, port=0, family=socket.AF_INET):
        results = await self._resolver.resolve(host, port, family)
        if not results or any(
            not ipaddress.ip_address(result["host"]).is_global for result in results
        ):
            raise OSError("Image URL resolves to a private or local address")
        return results

    async def close(self):
        await self._resolver.close()


async def verify_image_url(url: str) -> bool | None:
    """Download and validate a remote image; return None for network failures."""
    parsed, error = _parse_http_url(url)
    if error:
        return False

    try:
        await _resolve_public_host(
            parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
        )
        resolver = _PublicResolver()
        connector = aiohttp.TCPConnector(resolver=resolver, use_dns_cache=False)
        async with aiohttp.ClientSession(
            connector=connector, timeout=REQUEST_TIMEOUT
        ) as session:
            async with session.get(url, allow_redirects=True, max_redirects=5) as response:
                if response.status < 200 or response.status >= 300:
                    return False
                if not response.headers.get("Content-Type", "").lower().startswith("image/"):
                    return False
                if int(response.headers.get("Content-Length", 0) or 0) > MAX_IMAGE_SIZE:
                    return False

                data = bytearray()
                async for chunk in response.content.iter_chunked(64 * 1024):
                    data.extend(chunk)
                    if len(data) > MAX_IMAGE_SIZE:
                        return False

        is_valid, _ = _validate_image_data(bytes(data))
        return is_valid
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError):
        return None
