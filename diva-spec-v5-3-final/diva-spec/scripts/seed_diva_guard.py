#!/usr/bin/env python3
"""Seed Diva Guard settings and product rules on the dev site (TASK-E-14a).

The manager PIN is read from ``DIVA_MANAGER_PIN`` and stored only as a salted
PBKDF2-HMAC-SHA256 hash. Never commit the PIN. Synthetic data only:
  ERPNEXT_URL=... ERPNEXT_USER=... ERPNEXT_PASSWORD=... DIVA_MANAGER_PIN=... \
    python3 scripts/seed_diva_guard.py
"""

import hashlib
import os
import secrets
import sys

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
USER = os.environ.get("ERPNEXT_USER", "")
PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
PIN = os.environ.get("DIVA_MANAGER_PIN", "")
if not (BASE and USER and PASSWORD and PIN):
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER, ERPNEXT_PASSWORD and DIVA_MANAGER_PIN")

ITERATIONS = 260000
COMPANY = "Diva Dev"

http = httpx.Client(base_url=BASE, timeout=30)
http.post("/api/method/login", data={"usr": USER, "pwd": PASSWORD}).raise_for_status()

salt = secrets.token_hex(16)
pin_hash = hashlib.pbkdf2_hmac("sha256", PIN.encode(), bytes.fromhex(salt), ITERATIONS).hex()

settings = {
    "enabled": 1,
    "manager_pin_hash": pin_hash,
    "manager_pin_salt": salt,
    "manager_pin_iterations": ITERATIONS,
    "discount_cashier_limit_pct": 5,
    "discount_manager_limit_pct": 15,
    "enforce_moq": 1,
    "enforce_price_list": 1,
    "block_counter_credit": 1,
    "enforce_reserved_stock": 1,
}
response = http.put("/api/resource/Diva Guard Settings/Diva Guard Settings", json=settings)
response.raise_for_status()
print("diva guard settings updated")

items = [f"BULK-ACC-{index:02d}" for index in range(1, 7)] + [
    f"BULK-COS-{index:02d}" for index in range(1, 7)
]
for code in items:
    if http.get(f"/api/resource/Diva Product Rule/{code}").status_code == 200:
        continue
    payload = {
        "item": code,
        "name_en": code.replace("-", " ").title(),
        "publish_status": "Published",
        "is_active": 1,
        "moq_dozen": 2 if code == "BULK-ACC-01" else 0,
        "step_dozen": 1 if code == "BULK-ACC-01" else 0,
        "max_discount_pct": 15,
        "description_ar": "منتج تجريبي",
        "description_en": "Synthetic dev product",
    }
    created = http.post("/api/resource/Diva Product Rule", json=payload)
    created.raise_for_status()
    print("product rule created:", code)

print("product rules:", len(items))
