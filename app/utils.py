#Login and security utils
from passlib.context import CryptContext
pwd_context = CryptContext(schemes="bcrypt", deprecated="auto")

def hash(password: str):
    return pwd_context.hash(password)

def verify(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


#blockradar utils
def get_wallet_type_from_blockchain(blockchain_slug: str) -> str:
    mapping = {
        "bitcoin": "BTC",
        "ethereum": "ETH",
    }
    return mapping.get(blockchain_slug, "UNKNOWN")
