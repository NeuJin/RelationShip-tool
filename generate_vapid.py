"""Generate a VAPID key pair for Web Push.

Usage:  python generate_vapid.py

Copy the printed values into your environment (or host dashboard):
    VAPID_PUBLIC_KEY   -> used by the browser (applicationServerKey)
    VAPID_PRIVATE_KEY  -> kept secret on the server
"""
import base64
from py_vapid import Vapid01
from cryptography.hazmat.primitives import serialization


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip('=')


def main():
    v = Vapid01()
    v.generate_keys()
    pub = v.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    priv = v.private_key.private_numbers().private_value.to_bytes(32, 'big')
    print('VAPID_PUBLIC_KEY=' + b64u(pub))
    print('VAPID_PRIVATE_KEY=' + b64u(priv))


if __name__ == '__main__':
    main()
