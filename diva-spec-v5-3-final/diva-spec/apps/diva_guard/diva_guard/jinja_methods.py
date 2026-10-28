"""Jinja methods available to print formats (no request context required)."""

import io
import re

import pyqrcode


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
