const { loadEnv } = require('./env');

loadEnv();

function getBoolean(name, fallback) {
  const value = process.env[name];
  return value === undefined ? fallback : value.toLowerCase() === 'true';
}

const DEBUG_MODE = getBoolean('DEBUG_MODE', false);
const USE_MEME_MINT_DATABASE = getBoolean('USE_MEME_MINT_DATABASE', true);
const USE_PREDEFINED_MINT = getBoolean('USE_PREDEFINED_MINT', false) && !USE_MEME_MINT_DATABASE;
const TEST_MODE = getBoolean('TEST_MODE', false);
const PREDEFINED_MINT_PRIVATE_KEY = process.env.PREDEFINED_MINT_PRIVATE_KEY || '';
const TEST_PARAMS = {
  TOKEN_NAME: 'Test Token',
  TOKEN_SYMBOL: 'TEST',
  TOTAL_SUPPLY: 1000000000,
  LOGO_URL: 'https://example.com/logo.png',
  TOKEN_DESCRIPTION: 'Test Token Description',
  USER_WALLET: '11111111111111111111111111111111'
};

const USE_MAINNET = !DEBUG_MODE;
const HELIUS_API_KEY = process.env.HELIUS_API_KEY || '';
const NETWORK_URL = HELIUS_API_KEY
  ? `https://${USE_MAINNET ? 'mainnet' : 'devnet'}.helius-rpc.com/?api-key=${HELIUS_API_KEY}`
  : USE_MAINNET
    ? 'https://api.mainnet-beta.solana.com'
    : 'https://api.devnet.solana.com';

const WALLET_TYPE = 'privateKey';
const WALLET_PATH = 'wallet.json';
const DECIMALS = 9;
const REVOKE_AUTHORITIES = { MINT: true, FREEZE: true, UPDATE: true };
const TOKEN_INFO_PATH = 'token-info.json';
const PINATA_API_KEY = process.env.PINATA_API_KEY || '';
const PINATA_SECRET_KEY = process.env.PINATA_SECRET_KEY || '';

module.exports = {
  DEBUG_MODE, USE_MAINNET, NETWORK_URL, WALLET_TYPE, WALLET_PATH,
  DECIMALS, REVOKE_AUTHORITIES, TOKEN_INFO_PATH,
  PINATA_API_KEY, PINATA_SECRET_KEY, TEST_MODE, TEST_PARAMS,
  USE_PREDEFINED_MINT, USE_MEME_MINT_DATABASE, PREDEFINED_MINT_PRIVATE_KEY
};
