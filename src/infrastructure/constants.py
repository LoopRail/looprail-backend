USDC_ADDRESS = "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
ONBOARDING_TOKEN_EXP_MINS = 10
ACCESS_TOKEN_EXP_MINS = 15
REFRESH_TOKEN_EXP_DAYS = 30  # days
MAX_FAILED_OTP_ATTEMPTS = 3
ACCOUNT_LOCKOUT_DURATION_MINUTES = 15
USDC_ABI = [
    {
        "name": "transfer",
        "type": "function",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
    }
]

# Argon2 constants
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32
ARGON2_SALT_LEN = 16

# Blnk ledgers
CUSTOMER_WALLET_LEDGER = "customer_wallet_ledger"

# Blockrader wallets
MASTER_BASE_WALLET = "master_base_wallet"


# DOAMINS

STAGING_DOMAIN = "staging.looprail.xyz"
PRODUCTION_DOMAIN = "looprail.xyz"
