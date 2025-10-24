
from eth_account import Account
from web3 import Web3

from src.infrastructure.settings import (USDC_ABI, USDC_ADDRESS,
                                         block_rader_config)

# Connect to Ethereum (or Base) RPC
w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

# Load account
account = Account.from_key(block_rader_config.evm_master_wallet)


usdc_contract = w3.eth.contract(
    address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI
)


async def send_to_paycrest(order):
    """Send USDC payout transaction to Paycrest."""

    async def _build_and_send_tx():
        amount_wei = w3.to_wei(order["amount"], "mwei")

        tx = usdc_contract.functions.transfer(
            order["receiveAddress"], amount_wei
        ).build_transaction(
            {
                "from": account.address,
                "gas": 100000,
                "gasPrice": w3.eth.gas_price,
                "nonce": w3.eth.get_transaction_count(account.address),
            }
        )

        signed_tx = w3.eth.account.sign_transaction(tx, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()

    return await _build_and_send_tx()
