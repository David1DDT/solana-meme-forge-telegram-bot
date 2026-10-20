# Solana Memecoin Creator Bot

A comprehensive Telegram bot for creating memecoins on the Solana blockchain with advanced features like custom addresses, referral system, and automatic authority revocation.

## 🔗 Live Demo

Try the working bot: [@Meme_Forge_bot](https://t.me/Meme_Forge_bot)

## 🚀 Features

- **Token Creation**: Create SPL tokens on Solana with custom metadata
- **Custom Addresses**: Generate vanity addresses with custom endings  
- **Referral System**: Built-in referral program with automatic payouts
- **IPFS Integration**: Automatic metadata and image upload to IPFS
- **Authority Revocation**: Automatic revocation of mint, freeze, and update authorities
- **Payment Processing**: Automated Solana payment verification
- **Bonus System**: Free custom addresses for new users
- **Admin Panel**: Administrative commands and statistics

## 🏗️ Architecture

```
├── bot.py                 # Main bot entry point
├── main.py               # Application launcher
├── settings.py           # Non-secret runtime settings and bot text
├── utils/                # Utility modules
│   ├── handlers.py       # Core message handlers
│   ├── state_handlers.py # FSM state handlers
│   ├── edit_handlers.py  # Edit menu handlers
│   ├── keyboards.py      # Inline keyboards
│   ├── validators.py     # Input validation
│   └── formatters.py     # Message formatting
├── referrals/            # Referral system
│   ├── handlers.py       # Referral handlers
│   ├── manager.py        # Referral logic
│   └── middleware.py     # User management
├── scripts/              # JavaScript utilities
│   ├── solana-token.js   # Token creation
│   ├── ipfs-utils.js     # IPFS operations
│   └── revoke-*.js       # Authority revocation
└── database/             # Database management
    └── db-manager.js     # Database operations
```

## 📋 Prerequisites

- **Python 3.9+**
- **Node.js 16+**
- **SQLite3**
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- **Helius API Key** (from [helius.xyz](https://helius.dev))
- **Pinata API Keys** (from [pinata.cloud](https://pinata.cloud))

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/solanamemeforge/solana-meme-forge-telegram-bot.git
cd solana-memecoin-bot
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Node.js Dependencies

```bash
npm install @solana/web3.js @solana/spl-token @metaplex-foundation/mpl-token-metadata
npm install sqlite3 axios form-data bip39 ed25519-hd-key bs58 yargs
```

### 4. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your actual values
```

Set `MAIN_BOT_TOKEN`, `SUPPORT_BOT_TOKEN`, `ADMIN_ID`, `SERVICE_WALLET_ADDRESS`,
`HELIUS_API_KEY`, and the Pinata credentials in `.env`. Keep `.env` private and
never commit it. Runtime values are loaded from environment variables by
`settings.py` and the JavaScript scripts.

### 5. Create Wallet File

Create `wallet.json` with your Solana wallet:

```json
{
  "privateKey": "your-hex-private-key",
  "publicKey": "your-public-key"
}
```

## 🚀 Usage

### Start the Bot

```bash
python main.py
```

### Bot Commands

- `/start` - Start token creation process
- `/help` - Show help information
- `/referral` - Access referral system

### Admin Commands

- `/db_stats` - Database statistics
- `/user_stats <user_id>` - User statistics
- `/wallet_stats` - Wallet reservation stats

## 💎 Custom Addresses

The bot supports generating vanity addresses with custom endings:

- **4 characters**: 0.03 SOL (FREE for new users)
- **5 characters**: 0.10 SOL
- **6 characters**: 0.20 SOL
- **7-10 characters**: 0.35-1.00 SOL

## 🔗 Referral System

- **Token Commission**: 10% of token creation cost
- **Custom Address Commission**: 50% of custom address cost
- **Automatic Payouts**: Payments sent immediately after token creation
- **Bonus System**: 3 free custom addresses for referred users

## 🛠️ Development

### Project Structure

The project is split between Python (bot logic) and JavaScript (Solana operations):

- **Python**: Telegram bot interface, user management, payment verification
- **JavaScript**: Solana blockchain interactions, token creation, IPFS uploads

### Key Components

1. **FSM States**: User flow management through finite state machine
2. **Payment Verification**: Automated Solana transaction checking
3. **Database Management**: SQLite for user data and wallet management
4. **Security**: Input validation, wallet protection, rate limiting

### Adding Features

1. Create handlers in appropriate modules
2. Register handlers in `bot.py`
3. Add language strings to `settings.py`
4. Update database schema if needed

## 🔒 Security Features

- **Input Validation**: All user inputs are validated
- **Wallet Protection**: Prevention of wallet address conflicts
- **Transaction Verification**: Cryptographic verification of payments
- **Rate Limiting**: Protection against spam and abuse
- **Authority Revocation**: Tokens become truly decentralized

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    wallet_address TEXT,
    referred_by INTEGER,
    total_earned_tokens REAL DEFAULT 0,
    total_earned_custom REAL DEFAULT 0,
    total_referrals INTEGER DEFAULT 0,
    bonus_custom_addresses INTEGER DEFAULT 3,
    created_at REAL DEFAULT (julianday('now'))
);
```

### Payments Table
```sql
CREATE TABLE referral_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referred_user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    payment_type TEXT NOT NULL,
    tx_hash TEXT,
    created_at REAL DEFAULT (julianday('now'))
);
```

## 🌐 Network Support

- **Mainnet**: Production environment
- **Devnet**: Testing environment
- **Automatic switching** based on `DEBUG_MODE`

## 📝 Configuration Options

### Payment Settings
```python
AMOUNT = 0.09  # Base token creation cost in SOL
REFERRAL_TOKEN_COMMISSION = 0.10  # 10%
REFERRAL_CUSTOM_COMMISSION = 0.50  # 50%
```

### Custom Address Pricing
```python
CUSTOM_ADDRESS_PRICES = {
    4: 0.03,   # 4 characters
    5: 0.10,   # 5 characters
    6: 0.20,   # 6 characters
    # ... up to 10 characters
}
```

## 🐛 Troubleshooting

### Common Issues

1. **"Database not found"**
   - Ensure SQLite databases are created
   - Check file permissions

2. **"Invalid bot token"**
   - Verify bot tokens in `.env`
   - Check token format

3. **"Connection timeout"**
   - Verify network connectivity
   - Check Helius API key

4. **"Insufficient funds"**
   - Ensure wallet has enough SOL
   - Check minimum balance requirements

### Debug Mode

Set `DEBUG_MODE=true` in `.env` for:
- Detailed logging
- Devnet operations
- Test database usage

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For support and questions:
- Open an issue on GitHub
- Join our Telegram group
- Check the documentation

## ⚠️ Disclaimer

This software is provided "as is" without warranty. Users are responsible for:
- Securing their private keys
- Managing their funds
- Complying with local regulations
- Understanding Solana blockchain mechanics

**Always test on devnet before using mainnet!**

## 🔒 Security Notice

For security reasons, sensitive data has been replaced with placeholders in the public repository:
- Bot tokens are set to example values
- Service wallet addresses use placeholder strings
- API keys require your own credentials
- Database connections need proper configuration

This is standard practice for open source projects to prevent unauthorized access to production systems. Replace all placeholder values with your actual credentials before deployment.