"""Jinja methods available to print formats (no request context required)."""

import io
import re
from urllib.parse import quote

import frappe  # type: ignore[import-not-found]
import pyqrcode

from diva_guard.share import _normalize_phone

# Seed number for the store's WhatsApp (P0-07). It lives in Diva Guard Settings
# so the owner can rotate it without code; this is only a last-resort fallback.
DEFAULT_WHATSAPP = "201119595715"
MESSAGES = {
	"ar": "مرحبًا، أود الاستفسار عن منتجاتكم.",
	"en": "Hello, I would like to ask about your products.",
}


def store_whatsapp_number() -> str:
	"""The store WhatsApp number from Diva Guard Settings, normalized for wa.me."""
	try:
		value = frappe.db.get_single_value("Diva Guard Settings", "whatsapp_number")
	except Exception:  # pragma: no cover - defensive when no site/db is connected
		value = None
	return _normalize_phone(str(value or DEFAULT_WHATSAPP))


def whatsapp_link(language: str = "ar") -> str:
	"""The click-to-chat link printed as the Message-us QR (ENH-C-09)."""
	number = store_whatsapp_number()
	if not number:
		return ""
	message = MESSAGES["en" if str(language).lower().startswith("en") else "ar"]
	return f"https://wa.me/{number}?text={quote(message)}"


def qr_svg(text: str) -> str:
	"""Return an inline SVG QR code for print formats (UTF-8, no external service)."""
	code = pyqrcode.create(str(text)[:900], error="M", encoding="utf-8")
	buffer = io.BytesIO()
	code.svg(buffer, scale=3, quiet_zone=2)
	svg = buffer.getvalue().decode("utf-8")
	width_match = re.search(r'width="(\d+)"', svg)
	height_match = re.search(r'height="(\d+)"', svg)
	if width_match and height_match:
		width, height = width_match.group(1), height_match.group(1)
		svg = svg.replace(
			'class="pyqrcode">',
			f'class="pyqrcode" viewBox="0 0 {width} {height}" shape-rendering="crispEdges">',
			1,
		)
	return svg
