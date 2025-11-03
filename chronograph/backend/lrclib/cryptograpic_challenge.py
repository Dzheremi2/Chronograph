import hashlib
from binascii import unhexlify


def solve_challenge(prefix: str, target_hex: str) -> str:
  """Solves a cryptographic challenge required for LRClib publishing

  Parameters
  ----------
  prefix : str
    Prefix from `/api/request-challenge`
  target_hex : str
    Target from `/api/requst-challenge`

  Returns
  -------
  str
    Nonce, that in combination with prefix will be an X-Publish-Token
  """
  def verify_nonce(result: int, target: int) -> bool:
    if len(result) != len(target):
      return False

    for index, res in enumerate(result):
      if res > target[index]:
        return False
      if res < target[index]:
        break

    return True

  target = unhexlify(target_hex.upper())
  nonce = 0

  while True:
    input_data = f"{prefix}{nonce}".encode()
    hashed = hashlib.sha256(input_data).digest()

    if verify_nonce(hashed, target):
      break
    nonce += 1

  return str(nonce)
