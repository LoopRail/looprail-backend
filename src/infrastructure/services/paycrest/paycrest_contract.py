import asyncio

from web3 import Web3
from web3.utils.abi import get_event_abi

# Connect to Ethereum (or Base) RPC
w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

USDC_ADDRESS = "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
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
usdc_contract = w3.eth.contract(
    address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI
)


async def send_to_paycrest():
    """Send USDC payout transaction to Paycrest."""

    async def _build_and_send_tx():
        amount_wei = w3.to_wei("1000000", "mwei")

        usdc_contract.encode_abi()

        print(
            get_event_abi(
                abi=USDC_ABI,
                event_name="transfer",
                argument_names=[
                    "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
                    amount_wei,
                ],
            )
        )
        # signed_tx = w3.eth.account.sign_transaction(tx, account.key)
        # tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        # return tx_hash.hex()

    return await _build_and_send_tx()


asyncio.run(main=send_to_paycrest())
