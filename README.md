# WBTC Airdrop Bot

A Python bot that scans token holders and performs automated WBTC airdrops based on their token holdings percentage. The bot runs in 20-minute cycles, distributing 0.2 WBTC total per cycle.

## Features

- 🔍 **Token Holder Analysis**: Scans any Solana token contract for holders
- 💰 **Percentage-Based Distribution**: Distributes WBTC based on token holdings percentage
- ⏰ **Automated Cycles**: Runs every 20 seconds (configurable)
- 🛡️ **Whale Protection**: Excludes holders with too many tokens
- 📊 **Real-time Monitoring**: Live logging and progress tracking
- 🔒 **Secure**: No hardcoded keys or sensitive information

## Installation

### Prerequisites

- Python 3.8+
- Solana wallet with WBTC tokens
- RPC endpoint (Helius, QuickNode, or public RPC)

### Install Dependencies

```bash
pip install requests solana solders base58 python-telegram-bot
```

## Configuration

The bot requires the following configuration (no hardcoded values):

### Required Inputs
- **Token Contract**: Address of the token to analyze
- **RPC URL**: Solana RPC endpoint
- **Private Key**: Sender wallet private key (base58 or hex)
- **WBTC Amount**: Amount of WBTC to distribute per cycle (default: 0.2)
- **Cycle Interval**: Seconds between cycles (default: 20)
- **Token Thresholds**: Min/max token holdings for eligibility

### Optional Settings
- **Minimum Holdings**: Minimum tokens required to be eligible (default: 1,000)
- **Maximum Holdings**: Maximum tokens (excludes whales) (default: 10,000,000)

## Usage

### Basic Usage

```bash
python wbtc_airdrop_bot.py
```

The bot will prompt you for:
1. Solana RPC URL
2. Token contract address to analyze
3. WBTC amount per cycle
4. Cycle interval in seconds
5. Token holding thresholds
6. Sender wallet private key

### Example Session

```
🚀 WBTC Airdrop Bot - Token Holder Analysis & Distribution
================================================================================

⚙️  Configuration Setup:
Enter Solana RPC URL (or press Enter for default): 
Enter token contract address to analyze: 5r1oLG9nrCuuHGdZDarEjwEd9zBPcinzCy3wWJLbpump
Enter WBTC amount per cycle (default 0.2): 0.2
Enter cycle interval in seconds (default 20): 20
Enter minimum token holdings (default 1000): 1000
Enter maximum token holdings (default 10000000): 10000000

🔑 Sender Wallet Setup:
Enter your private key (base58 or hex format): [YOUR_PRIVATE_KEY]

📋 Bot Configuration:
Token contract: 5r1oLG9nrCuuHGdZDarEjwEd9zBPcinzCy3wWJLbpump
RPC URL: https://api.mainnet-beta.solana.com
WBTC per cycle: 0.2
Cycle interval: 20 seconds
Min token holdings: 1,000
Max token holdings: 10,000,000

Proceed with WBTC airdrop bot? (y/N): y
```

## How It Works

### 1. Token Holder Scanning
- Connects to Solana RPC to fetch all token accounts
- Aggregates balances by wallet address
- Filters holders based on token amount thresholds

### 2. Distribution Calculation
- Calculates each holder's percentage of total eligible tokens
- Distributes WBTC proportionally based on holdings
- Excludes whales and dust holders

### 3. Automated Airdrops
- Executes WBTC transfers to eligible holders
- Runs continuously in configurable cycles
- Provides real-time progress updates

### 4. Cycle Management
- Each cycle scans fresh holder data
- Distributes the configured WBTC amount
- Waits for the specified interval before next cycle

## Security Features

- ✅ **No Hardcoded Keys**: All sensitive data provided at runtime
- ✅ **Input Validation**: Validates all user inputs
- ✅ **Error Handling**: Comprehensive error handling and logging
- ✅ **Balance Checks**: Verifies sufficient WBTC balance before starting
- ✅ **Transaction Verification**: Confirms successful transactions

## Output and Logging

The bot provides detailed logging including:

```
🚀 WBTC AIRDROP CYCLE #1
⏰ Start time: 2024-01-15 14:30:25
================================================================================
📊 Step 1: Scanning token holders...
Found 1,247 unique token holders
Total token supply: 1,000,000,000
🔍 Step 2: Filtering eligible holders...
Eligible holders: 892
Excluded (too small): 203
Excluded (too large/whales): 152

💰 Step 3: Calculating WBTC distribution...

📋 WBTC Distribution Plan:
Total WBTC to distribute: 0.2
Eligible holders: 892
Token range: 1,000 - 10,000,000

Top 10 recipients:
 1. 5r1oLG9n...JLbpump: 0.000224 WBTC (0.11%)
 2. 9n4nbM75...YFeJ9E: 0.000198 WBTC (0.10%)
 3. 7xKXtg2C...WZ3xq: 0.000187 WBTC (0.09%)
...

🚀 Step 4: Executing WBTC airdrops...
Sending to recipient 1/892: 5r1oLG9n...
✅ Success: 2xKXtg2CW9WZ3xq...
Sending to recipient 2/892: 9n4nbM75...
✅ Success: 7xKXtg2CW9WZ3xq...
...

🎉 CYCLE #1 COMPLETE!
⏱️  Duration: 45.23 seconds
✅ Successful: 890/892
❌ Failed: 2/892
💰 Total WBTC sent: 0.1998
```

## Error Handling

The bot handles various error scenarios:

- **RPC Connection Issues**: Retries with exponential backoff
- **Insufficient Balance**: Checks WBTC balance before starting
- **Transaction Failures**: Logs failed transactions and continues
- **Network Issues**: Graceful handling of network timeouts
- **Invalid Inputs**: Validates all user inputs

## Stopping the Bot

- Press `Ctrl+C` to stop the bot gracefully
- The bot will complete the current cycle before stopping
- Final summary will be displayed

## Requirements

### System Requirements
- Python 3.8 or higher
- Internet connection
- Sufficient WBTC balance in sender wallet

### Wallet Requirements
- Solana wallet with WBTC tokens
- Sufficient SOL for transaction fees
- Private key in base58 or hex format

## Troubleshooting

### Common Issues

1. **"Failed to initialize sender wallet"**
   - Check private key format (base58 or hex)
   - Ensure wallet has sufficient SOL balance

2. **"No token holders found"**
   - Verify token contract address
   - Check RPC endpoint connectivity

3. **"Insufficient WBTC balance"**
   - Ensure sender wallet has enough WBTC
   - Check WBTC token mint address

4. **"RPC request failed"**
   - Verify RPC URL is correct
   - Check API key if using premium RPC
   - Try different RPC endpoint

### Performance Tips

- Use premium RPC endpoints for better performance
- Adjust batch sizes for your RPC limits
- Monitor transaction fees and adjust accordingly
- Consider rate limits when using public RPCs

## Disclaimer

⚠️ **Important Security Notes:**

- Never share your private keys
- Test with small amounts first
- Ensure you understand the risks
- This bot is for educational purposes
- Use at your own risk

## License

This project is for educational purposes. Use responsibly and at your own risk.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs for error details
3. Ensure all requirements are met
4. Verify wallet and RPC configurations
