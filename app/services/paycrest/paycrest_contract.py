import asyncio
from web3 import Web3
from eth_account import Account
from ...settings import settings

# Connect to Ethereum (or Base) RPC
w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

# Load account
account = Account.from_key(settings.blockradar_ethereum_wallet_api_key)

# USDC contract on Base
usdc_address = "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
usdc_abi = [{
    "name": "transfer",
    "type": "function",
    "inputs": [
        {"name": "to", "type": "address"},
        {"name": "amount", "type": "uint256"}
    ],
    "outputs": [{"name": "", "type": "bool"}],
    "stateMutability": "nonpayable"
}]
usdc_contract = w3.eth.contract(address=usdc_address, abi=usdc_abi)


async def send_to_paycrest(order):
    """Send USDC payout transaction to Paycrest."""

    def _build_and_send_tx():
        amount_wei = w3.to_wei(order["amount"], "mwei")

        tx = usdc_contract.functions.transfer(
            order["receiveAddress"],
            amount_wei
        ).build_transaction({
            "from": account.address,
            "gas": 100000,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(account.address)
        })

        signed_tx = w3.eth.account.sign_transaction(tx, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()

    # Offload blocking work to a thread
    return await asyncio.to_thread(_build_and_send_tx)
