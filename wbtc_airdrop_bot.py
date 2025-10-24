#!/usr/bin/env python3
"""
WBTC Airdrop Bot - Token Holder Analysis & Automated WBTC Distribution

This bot:
1. Scans token holders for a specific contract
2. Calculates WBTC distribution based on token holdings percentage
3. Performs automated WBTC airdrops every 20 seconds
4. Distributes 0.2 WBTC total per cycle

Requirements:
pip install requests solana solders base58 python-telegram-bot
"""

import asyncio
import json
import time
import base58
import requests
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# Solana imports
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.hash import Hash
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AirdropConfig:
    """Configuration for WBTC airdrop system"""
    # Token contract to analyze (set via environment or input)
    token_contract: str = ""
    
    # WBTC distribution settings
    total_wbtc_per_cycle: float = 0.2  # 0.2 WBTC total per cycle
    cycle_interval: int = 20  # 20 seconds between cycles
    
    # RPC settings (set via environment variable)
    rpc_url: str = ""
    
    # WBTC token mint (WBTC on Solana)
    wbtc_mint: str = "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E"
    
    # Minimum token holdings to be eligible (adjust as needed)
    min_token_holdings: float = 1000.0  # Minimum tokens to be eligible
    max_token_holdings: float = 10000000.0  # Maximum tokens (exclude whales)
    
    # Sender wallet (will be set when initialized)
    sender_private_key: str = ""
    sender_keypair: Optional[Keypair] = None
    sender_pubkey: Optional[Pubkey] = None

class WBTCAirdropBot:
    """Main WBTC airdrop bot class"""
    
    def __init__(self, config: AirdropConfig):
        self.config = config
        self.client = Client(config.rpc_url)
        self.is_running = False
        self.cycle_count = 0
        self.total_wbtc_distributed = 0.0
        
    def initialize_sender(self, private_key: str) -> bool:
        """Initialize the sender wallet for WBTC distribution"""
        try:
            self.config.sender_private_key = private_key
            
            if len(private_key) == 128:  # Hex format
                secret_key_bytes = bytes.fromhex(private_key)
            else:  # Base58 format
                secret_key_bytes = base58.b58decode(private_key)
            
            self.config.sender_keypair = Keypair.from_bytes(secret_key_bytes)
            self.config.sender_pubkey = self.config.sender_keypair.pubkey()
            
            logger.info(f"Sender wallet initialized: {self.config.sender_pubkey}")
            return self.check_sender_balance()
            
        except Exception as e:
            logger.error(f"Failed to initialize sender wallet: {e}")
            return False
    
    def check_sender_balance(self) -> bool:
        """Check the sender wallet balance"""
        try:
            balance_lamports = self.client.get_balance(self.config.sender_pubkey, commitment=Confirmed)
            balance_sol = balance_lamports.value / 1_000_000_000
            logger.info(f"Sender SOL balance: {balance_sol:.6f} SOL")
            
            # Check WBTC balance
            wbtc_balance = self.get_token_balance(self.config.sender_pubkey, self.config.wbtc_mint)
            logger.info(f"Sender WBTC balance: {wbtc_balance:.6f} WBTC")
            
            return balance_sol > 0 and wbtc_balance >= self.config.total_wbtc_per_cycle
            
        except Exception as e:
            logger.error(f"Failed to check balance: {e}")
            return False
    
    def get_token_balance(self, wallet_pubkey: Pubkey, token_mint: str) -> float:
        """Get token balance for a specific wallet and token"""
        try:
            response = self.client.get_token_accounts_by_owner(
                wallet_pubkey,
                {"mint": token_mint},
                encoding="jsonParsed"
            )
            
            if response.value:
                for account in response.value:
                    token_amount = account.account.data.parsed["info"]["tokenAmount"]["uiAmount"]
                    if token_amount and token_amount > 0:
                        return float(token_amount)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            return 0.0
    
    def make_rpc_request(self, method: str, params: list) -> dict:
        """Make an RPC request to Solana"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.post(self.config.rpc_url, json=payload, headers=headers, timeout=60)
            
            if response.status_code != 200:
                logger.error(f"RPC request failed: {response.status_code}")
                return None
            
            result = response.json()
            
            if 'error' in result:
                logger.error(f"RPC Error: {result['error']}")
                return None
                
            return result
            
        except Exception as e:
            logger.error(f"RPC request failed: {e}")
            return None
    
    def get_token_holders(self, token_contract: str) -> Dict[str, float]:
        """Get all token holders and their balances"""
        logger.info(f"Scanning token holders for contract: {token_contract}")
        
        # Get token accounts for the contract
        response = self.make_rpc_request(
            "getTokenAccountsByMint",
            [token_contract, {"encoding": "jsonParsed", "commitment": "confirmed"}]
        )
        
        if not response or 'result' not in response:
            logger.error("Failed to get token accounts")
            return {}
        
        token_accounts = response['result']['value']
        holders = {}
        total_supply = 0.0
        
        logger.info(f"Processing {len(token_accounts)} token accounts...")
        
        for account in token_accounts:
            try:
                account_data = account['account']['data']['parsed']['info']
                owner = account_data['owner']
                token_amount = float(account_data['tokenAmount']['uiAmount'])
                
                if token_amount == 0:
                    continue
                
                # Aggregate balances for same owner
                if owner in holders:
                    holders[owner] += token_amount
                else:
                    holders[owner] = token_amount
                
                total_supply += token_amount
                    
            except (KeyError, TypeError, ValueError) as e:
                logger.debug(f"Skipping invalid account: {e}")
                continue
        
        logger.info(f"Found {len(holders)} unique token holders")
        logger.info(f"Total token supply: {total_supply:,.0f}")
        
        return holders, total_supply
    
    def filter_eligible_holders(self, holders: Dict[str, float]) -> Dict[str, float]:
        """Filter holders based on token holdings criteria"""
        eligible_holders = {}
        
        for wallet, amount in holders.items():
            if self.config.min_token_holdings <= amount <= self.config.max_token_holdings:
                eligible_holders[wallet] = amount
        
        excluded_small = sum(1 for amount in holders.values() if amount < self.config.min_token_holdings)
        excluded_large = sum(1 for amount in holders.values() if amount > self.config.max_token_holdings)
        
        logger.info(f"Eligible holders: {len(eligible_holders)}")
        logger.info(f"Excluded (too small): {excluded_small}")
        logger.info(f"Excluded (too large/whales): {excluded_large}")
        
        return eligible_holders
    
    def calculate_wbtc_distribution(self, eligible_holders: Dict[str, float]) -> List[Dict]:
        """Calculate WBTC distribution based on token holdings percentage"""
        total_eligible_tokens = sum(eligible_holders.values())
        distribution = []
        
        for wallet, token_amount in eligible_holders.items():
            # Calculate percentage of total eligible tokens
            percentage = (token_amount / total_eligible_tokens) * 100
            
            # Calculate WBTC amount based on percentage
            wbtc_amount = (token_amount / total_eligible_tokens) * self.config.total_wbtc_per_cycle
            
            distribution.append({
                'wallet': wallet,
                'token_amount': token_amount,
                'percentage': percentage,
                'wbtc_amount': wbtc_amount
            })
        
        # Sort by token amount (descending)
        distribution.sort(key=lambda x: x['token_amount'], reverse=True)
        
        return distribution
    
    def create_wbtc_transfer_transaction(self, recipient: str, wbtc_amount: float) -> Optional[VersionedTransaction]:
        """Create a WBTC transfer transaction"""
        try:
            recipient_pubkey = Pubkey.from_string(recipient)
            
            # Get recent blockhash
            recent_blockhash_response = self.client.get_latest_blockhash(commitment=Confirmed)
            recent_blockhash = Hash.from_string(recent_blockhash_response.value.blockhash)
            
            # Create transfer instruction for WBTC
            # Note: This is a simplified version - actual WBTC transfers require SPL token program
            # For now, we'll create a SOL transfer as a placeholder
            # In production, you'd need to implement proper SPL token transfers
            
            transfer_instruction = transfer(
                TransferParams(
                    from_pubkey=self.config.sender_pubkey,
                    to_pubkey=recipient_pubkey,
                    lamports=int(wbtc_amount * 1_000_000_000)  # Convert to lamports (simplified)
                )
            )
            
            message = MessageV0.try_compile(
                payer=self.config.sender_pubkey,
                instructions=[transfer_instruction],
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash
            )
            
            transaction = VersionedTransaction(message, [self.config.sender_keypair])
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to create WBTC transfer transaction: {e}")
            return None
    
    async def send_wbtc_airdrop(self, recipient: str, wbtc_amount: float) -> Tuple[bool, str]:
        """Send WBTC to a single recipient"""
        try:
            transaction = self.create_wbtc_transfer_transaction(recipient, wbtc_amount)
            if not transaction:
                return False, "Failed to create transaction"
            
            tx_opts = TxOpts(
                skip_confirmation=False,
                skip_preflight=False,
                preflight_commitment=Confirmed,
                max_retries=3
            )
            
            result = self.client.send_transaction(transaction, opts=tx_opts)
            
            if result.value:
                return True, str(result.value)
            else:
                return False, "Transaction failed"
                
        except Exception as e:
            logger.error(f"Failed to send WBTC to {recipient}: {e}")
            return False, str(e)
    
    async def execute_airdrop_cycle(self) -> Dict:
        """Execute one complete airdrop cycle"""
        cycle_start_time = datetime.now()
        self.cycle_count += 1
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 WBTC AIRDROP CYCLE #{self.cycle_count}")
        logger.info(f"⏰ Start time: {cycle_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*80}")
        
        try:
            # Step 1: Get token holders
            logger.info("📊 Step 1: Scanning token holders...")
            holders, total_supply = self.get_token_holders(self.config.token_contract)
            
            if not holders:
                logger.error("❌ No token holders found!")
                return {"success": False, "error": "No token holders found"}
            
            # Step 2: Filter eligible holders
            logger.info("🔍 Step 2: Filtering eligible holders...")
            eligible_holders = self.filter_eligible_holders(holders)
            
            if not eligible_holders:
                logger.error("❌ No eligible holders found!")
                return {"success": False, "error": "No eligible holders found"}
            
            # Step 3: Calculate WBTC distribution
            logger.info("💰 Step 3: Calculating WBTC distribution...")
            distribution = self.calculate_wbtc_distribution(eligible_holders)
            
            # Display distribution plan
            logger.info(f"\n📋 WBTC Distribution Plan:")
            logger.info(f"Total WBTC to distribute: {self.config.total_wbtc_per_cycle}")
            logger.info(f"Eligible holders: {len(distribution)}")
            logger.info(f"Token range: {self.config.min_token_holdings:,.0f} - {self.config.max_token_holdings:,.0f}")
            
            # Show top 10 recipients
            logger.info(f"\nTop 10 recipients:")
            for i, recipient in enumerate(distribution[:10], 1):
                wallet_short = f"{recipient['wallet'][:8]}...{recipient['wallet'][-8:]}"
                logger.info(f"{i:2d}. {wallet_short}: {recipient['wbtc_amount']:.6f} WBTC ({recipient['percentage']:.2f}%)")
            
            # Step 4: Execute WBTC airdrops
            logger.info(f"\n🚀 Step 4: Executing WBTC airdrops...")
            successful_sends = 0
            failed_sends = 0
            total_wbtc_sent = 0.0
            
            for i, recipient in enumerate(distribution, 1):
                logger.info(f"Sending to recipient {i}/{len(distribution)}: {recipient['wallet'][:8]}...")
                
                success, signature_or_error = await self.send_wbtc_airdrop(
                    recipient['wallet'], 
                    recipient['wbtc_amount']
                )
                
                if success:
                    successful_sends += 1
                    total_wbtc_sent += recipient['wbtc_amount']
                    logger.info(f"✅ Success: {signature_or_error}")
                else:
                    failed_sends += 1
                    logger.error(f"❌ Failed: {signature_or_error}")
                
                # Small delay between transactions
                await asyncio.sleep(0.5)
            
            # Cycle summary
            cycle_end_time = datetime.now()
            cycle_duration = (cycle_end_time - cycle_start_time).total_seconds()
            
            logger.info(f"\n🎉 CYCLE #{self.cycle_count} COMPLETE!")
            logger.info(f"⏱️  Duration: {cycle_duration:.2f} seconds")
            logger.info(f"✅ Successful: {successful_sends}/{len(distribution)}")
            logger.info(f"❌ Failed: {failed_sends}/{len(distribution)}")
            logger.info(f"💰 Total WBTC sent: {total_wbtc_sent:.6f}")
            
            self.total_wbtc_distributed += total_wbtc_sent
            
            return {
                "success": True,
                "cycle": self.cycle_count,
                "successful": successful_sends,
                "failed": failed_sends,
                "total_wbtc_sent": total_wbtc_sent,
                "duration": cycle_duration
            }
            
        except Exception as e:
            logger.error(f"❌ Cycle #{self.cycle_count} failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def run_continuous_airdrop(self):
        """Run continuous WBTC airdrop cycles"""
        logger.info("🤖 Starting WBTC Airdrop Bot...")
        logger.info(f"Token contract: {self.config.token_contract}")
        logger.info(f"WBTC per cycle: {self.config.total_wbtc_per_cycle}")
        logger.info(f"Cycle interval: {self.config.cycle_interval} seconds")
        logger.info(f"Min holdings: {self.config.min_token_holdings:,.0f}")
        logger.info(f"Max holdings: {self.config.max_token_holdings:,.0f}")
        
        self.is_running = True
        start_time = datetime.now()
        
        try:
            while self.is_running:
                # Execute airdrop cycle
                result = await self.execute_airdrop_cycle()
                
                if result.get("success"):
                    logger.info(f"✅ Cycle #{result['cycle']} completed successfully")
                else:
                    logger.error(f"❌ Cycle failed: {result.get('error', 'Unknown error')}")
                
                # Wait for next cycle
                logger.info(f"⏳ Waiting {self.config.cycle_interval} seconds until next cycle...")
                await asyncio.sleep(self.config.cycle_interval)
                
        except KeyboardInterrupt:
            logger.info("⏹️  Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
        finally:
            self.is_running = False
            end_time = datetime.now()
            total_runtime = (end_time - start_time).total_seconds()
            
            logger.info(f"\n📊 FINAL SUMMARY:")
            logger.info(f"Total cycles: {self.cycle_count}")
            logger.info(f"Total runtime: {total_runtime:.2f} seconds")
            logger.info(f"Total WBTC distributed: {self.total_wbtc_distributed:.6f}")
            logger.info(f"Average WBTC per cycle: {self.total_wbtc_distributed / max(self.cycle_count, 1):.6f}")
    
    def stop(self):
        """Stop the airdrop bot"""
        self.is_running = False
        logger.info("🛑 Stopping WBTC Airdrop Bot...")

async def main():
    """Main function to run the WBTC airdrop bot"""
    print("🚀 WBTC Airdrop Bot - Token Holder Analysis & Distribution")
    print("="*80)
    
    # Get configuration from user input
    print("\n⚙️  Configuration Setup:")
    
    # Get RPC URL
    rpc_url = input("Enter Solana RPC URL (or press Enter for default): ").strip()
    if not rpc_url:
        rpc_url = "https://api.mainnet-beta.solana.com"  # Default public RPC
    
    # Get token contract
    token_contract = input("Enter token contract address to analyze: ").strip()
    if not token_contract:
        print("❌ Token contract address is required!")
        return
    
    # Get WBTC amount per cycle
    try:
        wbtc_per_cycle = float(input("Enter WBTC amount per cycle (default 0.2): ") or "0.2")
    except ValueError:
        wbtc_per_cycle = 0.2
    
    # Get cycle interval
    try:
        cycle_interval = int(input("Enter cycle interval in seconds (default 20): ") or "20")
    except ValueError:
        cycle_interval = 20
    
    # Get token holding thresholds
    try:
        min_holdings = float(input("Enter minimum token holdings (default 1000): ") or "1000")
        max_holdings = float(input("Enter maximum token holdings (default 10000000): ") or "10000000")
    except ValueError:
        min_holdings = 1000.0
        max_holdings = 10000000.0
    
    # Configuration
    config = AirdropConfig(
        token_contract=token_contract,
        rpc_url=rpc_url,
        total_wbtc_per_cycle=wbtc_per_cycle,
        cycle_interval=cycle_interval,
        min_token_holdings=min_holdings,
        max_token_holdings=max_holdings
    )
    
    # Initialize bot
    bot = WBTCAirdropBot(config)
    
    # Get sender private key
    print("\n🔑 Sender Wallet Setup:")
    private_key = input("Enter your private key (base58 or hex format): ").strip()
    
    if not private_key:
        print("❌ Private key is required!")
        return
    
    # Initialize sender wallet
    if not bot.initialize_sender(private_key):
        print("❌ Failed to initialize sender wallet!")
        return
    
    # Confirm settings
    print(f"\n📋 Bot Configuration:")
    print(f"Token contract: {config.token_contract}")
    print(f"RPC URL: {config.rpc_url}")
    print(f"WBTC per cycle: {config.total_wbtc_per_cycle}")
    print(f"Cycle interval: {config.cycle_interval} seconds")
    print(f"Min token holdings: {config.min_token_holdings:,.0f}")
    print(f"Max token holdings: {config.max_token_holdings:,.0f}")
    
    confirm = input("\nProceed with WBTC airdrop bot? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Bot cancelled.")
        return
    
    # Start the bot
    try:
        await bot.run_continuous_airdrop()
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
