"""Pembatas frekuensi permintaan per IP (slowapi).

Hanya satu instance Limiter untuk seluruh aplikasi — dipasang ke app.state di main.py
dan dipakai dekorator di router agar penghitungan batas konsisten.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

pembatas_per_ip = Limiter(key_func=get_remote_address)
