#!/usr/bin/env node
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');
const { loadEnv } = require('../scripts/env');

loadEnv();

function getDebugModeFromEnv() {
    return (process.env.DEBUG_MODE || 'false').toLowerCase() === 'true';
}

function getDbPaths(debugMode) {
    const dbDir = __dirname;

    if (debugMode) {
        return {
            meme: path.join(dbDir, 'wallets_meme_test.db'),
            other: path.join(dbDir, 'wallets_other_test.db')
        };
    } else {
        return {
            meme: path.join(dbDir, 'wallets_meme.db'),
            other: path.join(dbDir, 'wallets_other.db')
        };
    }
}

const DEBUG_MODE = getDebugModeFromEnv();
const dbPaths = getDbPaths(DEBUG_MODE);
const DB_PATH = dbPaths.meme;

class WalletManager {
    constructor(dbFile) {
        this.dbFile = dbFile;
        this.db = null;
    }

    async _upgradeTable() {
        return new Promise((resolve, reject) => {
            this.db.run(`
                CREATE TABLE IF NOT EXISTS meme_wallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    private_key TEXT NOT NULL UNIQUE,
                    public_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'available'
                        CHECK (status IN ('available', 'reserved')),
                    created_at REAL NOT NULL DEFAULT (julianday('now')),
                    updated_at REAL NOT NULL DEFAULT (julianday('now'))
                )
            `, (error) => {
                if (error) {
                    reject(new Error(`Wallet table initialization failed: ${error.message}`));
                } else {
                    resolve();
                }
            });
        });
    }

    connect() {
        return new Promise(async (resolve, reject) => {
            this.db = new sqlite3.Database(this.dbFile, async (err) => {
                if (err) {
                    reject(new Error(`Database connection error: ${err.message}`));
                } else {
                    fs.chmod(this.dbFile, 0o600, async (chmodError) => {
                        if (chmodError) {
                            reject(new Error(`Could not restrict wallet database permissions: ${chmodError.message}`));
                            return;
                        }
                        try {
                            await this._upgradeTable();
                            resolve();
                        } catch (upgradeErr) {
                            reject(upgradeErr);
                        }
                    });
                }
            });
        });
    }

    close() {
        return new Promise((resolve) => {
            if (this.db) {
                this.db.close((err) => {
                    resolve();
                });
            } else {
                resolve();
            }
        });
    }

    getRandomMemeKey() {
        return new Promise((resolve, reject) => {
            this.db.serialize(() => {
                this.db.run('BEGIN IMMEDIATE', (beginError) => {
                    if (beginError) {
                        reject(new Error(`Could not reserve a wallet: ${beginError.message}`));
                        return;
                    }

                    this.db.get(
                        "SELECT id, private_key, public_key FROM meme_wallets WHERE status = 'available' ORDER BY RANDOM() LIMIT 1",
                        (selectError, wallet) => {
                            if (selectError) {
                                this.db.run('ROLLBACK');
                                reject(new Error(`Could not select a wallet: ${selectError.message}`));
                                return;
                            }

                            if (!wallet) {
                                this.db.run('COMMIT', (commitError) => {
                                    if (commitError) {
                                        reject(new Error(`Could not finish wallet lookup: ${commitError.message}`));
                                    } else {
                                        resolve(null);
                                    }
                                });
                                return;
                            }

                            this.db.run(
                                "UPDATE meme_wallets SET status = 'reserved', updated_at = julianday('now') WHERE id = ? AND status = 'available'",
                                [wallet.id],
                                (updateError) => {
                                    if (updateError) {
                                        this.db.run('ROLLBACK');
                                        reject(new Error(`Could not reserve a wallet: ${updateError.message}`));
                                        return;
                                    }
                                    this.db.run('COMMIT', (commitError) => {
                                        if (commitError) {
                                            reject(new Error(`Could not finish wallet reservation: ${commitError.message}`));
                                        } else {
                                            resolve({
                                                privateKey: wallet.private_key,
                                                publicKey: wallet.public_key
                                            });
                                        }
                                    });
                                }
                            );
                        }
                    );
                });
            });
        });
    }

    deleteMemeKeyByPrivateKey(privateKey) {
        return new Promise((resolve, reject) => {
            this.db.run(
                'DELETE FROM meme_wallets WHERE private_key = ?',
                [privateKey],
                function (error) {
                    if (error) {
                        reject(new Error(`Could not delete wallet: ${error.message}`));
                    } else {
                        resolve(this.changes > 0);
                    }
                }
            );
        });
    }

    async getRandomMemeKeyWithConnect() {
        try {
            await this.connect();
            const key = await this.getRandomMemeKey();
            await this.close();
            return key;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async deleteMemeKeyByPrivateKeyWithConnect(privateKey) {
        try {
            await this.connect();
            const result = await this.deleteMemeKeyByPrivateKey(privateKey);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }
}

class CustomAddressManager extends WalletManager {
    constructor(debugMode) {
        const dbPaths = getDbPaths(debugMode);
        super(dbPaths.other);
    }

    async getAvailableCustomEndings() {
        return new Promise((resolve, reject) => {
            // Implementation would query custom address endings
            // This is a placeholder
            resolve([]);
        });
    }

    async getCustomAddressByEnding(ending) {
        return new Promise((resolve, reject) => {
            // Implementation would find custom address by ending
            // This is a placeholder
            resolve(null);
        });
    }

    async markCustomAddressAsUsed(ending, mintAddress = null) {
        return new Promise(async (resolve, reject) => {
            // Implementation would mark address as used
            // This is a placeholder
            resolve(false);
        });
    }

    async getAvailableCustomEndingsWithConnect() {
        try {
            await this.connect();
            const endings = await this.getAvailableCustomEndings();
            await this.close();
            return endings;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async getCustomAddressByEndingWithConnect(ending) {
        try {
            await this.connect();
            const address = await this.getCustomAddressByEnding(ending);
            await this.close();
            return address;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async markCustomAddressAsUsedWithConnect(ending, mintAddress = null) {
        try {
            await this.connect();
            const result = await this.markCustomAddressAsUsed(ending, mintAddress);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }
}

const walletManager = new WalletManager(DB_PATH);
const customAddressManager = new CustomAddressManager(DEBUG_MODE);

module.exports = {
    WalletManager,
    walletManager,
    CustomAddressManager,
    customAddressManager
};