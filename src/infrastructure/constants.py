USDC_ADDRESS = "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
ONBOARDING_TOKEN_EXP_MINS = 10
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
