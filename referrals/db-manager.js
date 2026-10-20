#!/usr/bin/env node
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const { loadEnv } = require('../scripts/env');

loadEnv();

function getDebugModeFromEnv() {
    return (process.env.DEBUG_MODE || 'false').toLowerCase() === 'true';
}

function getReferralDbPath(debugMode) {
    const dbDir = __dirname;
    return path.join(dbDir, debugMode ? 'referrals_test.db' : 'referrals.db');
}

const DEBUG_MODE = getDebugModeFromEnv();
const DB_PATH = getReferralDbPath(DEBUG_MODE);

class ReferralDbManager {
    constructor(dbFile) {
        this.dbFile = dbFile;
        this.db = null;
    }

    async connect() {
        return new Promise(async (resolve, reject) => {
            this.db = new sqlite3.Database(this.dbFile, async (err) => {
                if (err) {
                    reject(new Error(`DB connection error: ${err.message}`));
                } else {
                    try {
                        await this.createTables();
                        resolve();
                    } catch (createErr) {
                        reject(createErr);
                    }
                }
            });
        });
    }

    async createTables() {
        return new Promise((resolve, reject) => {
            const createUsersTable = `
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    wallet_address TEXT,
                    referred_by INTEGER,
                    total_earned_tokens REAL DEFAULT 0,
                    total_earned_custom REAL DEFAULT 0,
                    total_referrals INTEGER DEFAULT 0,
                    bonus_custom_addresses INTEGER DEFAULT 3,
                    welcome_message_shown INTEGER DEFAULT 0,
                    created_at REAL DEFAULT (julianday('now')),
                    updated_at REAL DEFAULT (julianday('now')),
                    FOREIGN KEY (referred_by) REFERENCES users (user_id)
                )
            `;

            const createPaymentsTable = `
                CREATE TABLE IF NOT EXISTS referral_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    payment_type TEXT NOT NULL,
                    tx_hash TEXT,
                    created_at REAL DEFAULT (julianday('now')),
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referred_user_id) REFERENCES users (user_id)
                )
            `;

            this.db.run(createUsersTable, (err) => {
                if (err) {
                    reject(new Error(`Error creating users table: ${err.message}`));
                    return;
                }

                this.db.run(createPaymentsTable, (err) => {
                    if (err) {
                        reject(new Error(`Error creating payments table: ${err.message}`));
                        return;
                    }

                    this.db.run(
                        'UPDATE users SET bonus_custom_addresses = 3 WHERE bonus_custom_addresses IS NULL',
                        (migrationErr) => {
                            if (migrationErr) {
                                console.error('Migration warning:', migrationErr.message);
                            }
                            resolve();
                        }
                    );
                });
            });
        });
    }

    markWelcomeMessageShown(userId) {
        return new Promise((resolve, reject) => {
            // Implementation would mark welcome message as shown
            resolve(true);
        });
    }

    wasWelcomeMessageShown(userId) {
        return new Promise((resolve, reject) => {
            // Implementation would check if welcome message was shown
            resolve(false);
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

    addOrUpdateUser(userId, username = null, referredBy = null) {
        return new Promise((resolve, reject) => {
            // Implementation would add or update user in database
            // This is a placeholder that simulates successful operation
            resolve({ updated: true, newUser: true, referrerSet: false });
        });
    }

    setWalletAddress(userId, walletAddress) {
        return new Promise((resolve, reject) => {
            // Implementation would set wallet address
            resolve(true);
        });
    }

    removeWalletAddress(userId) {
        return new Promise((resolve, reject) => {
            // Implementation would remove wallet address
            resolve(true);
        });
    }

    getUserInfo(userId) {
        return new Promise((resolve, reject) => {
            // Implementation would get user info from database
            resolve(null);
        });
    }

    getReferrer(userId) {
        return new Promise((resolve, reject) => {
            // Implementation would get referrer info
            resolve(null);
        });
    }

    getBonusCustomAddresses(userId) {
        return new Promise((resolve, reject) => {
            // Implementation would get bonus address count
            resolve(0);
        });
    }

    useBonusCustomAddress(userId) {
        return new Promise((resolve, reject) => {
            // Implementation would use one bonus address
            resolve(false);
        });
    }

    generateReferralCode(userId) {
        const crypto = require('crypto');
        const secret = 'your_secret_salt_here';
        const combined = `${secret}_${userId}_${secret}`;
        const hash = crypto.createHash('sha256').update(combined).digest('hex');
        const hashValue = parseInt(hash.substring(0, 12), 16);

        const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        let code = "";
        let value = hashValue;

        for (let i = 0; i < 6; i++) {
            code = chars[value % 36] + code;
            value = Math.floor(value / 36);
        }

        return code;
    }

    findReferrerByCode(referralCode) {
        return new Promise((resolve, reject) => {
            // Implementation would find referrer by code
            // This is a placeholder
            resolve(null);
        });
    }

    async setReferrerByCode(userId, referralCode) {
        try {
            const referrerId = await this.findReferrerByCode(referralCode);

            if (!referrerId) return { success: false, reason: 'referrer_not_found' };
            if (referrerId === userId) return { success: false, reason: 'self_referral' };

            // Implementation would set referrer
            return { success: false, reason: 'already_has_referrer' };
        } catch (error) {
            throw error;
        }
    }

    recordPayment(referrerId, referredUserId, amount, paymentType, txHash = null) {
        return new Promise((resolve, reject) => {
            // Implementation would record payment in database
            resolve();
        });
    }

    // Methods with connect/disconnect wrappers
    async markWelcomeMessageShownWithConnect(userId) {
        try {
            await this.connect();
            const result = await this.markWelcomeMessageShown(userId);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async wasWelcomeMessageShownWithConnect(userId) {
        try {
            await this.connect();
            const result = await this.wasWelcomeMessageShown(userId);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async addOrUpdateUserWithConnect(userId, username = null, referredBy = null) {
        try {
            await this.connect();
            const result = await this.addOrUpdateUser(userId, username, referredBy);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async setWalletAddressWithConnect(userId, walletAddress) {
        try {
            await this.connect();
            const result = await this.setWalletAddress(userId, walletAddress);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async removeWalletAddressWithConnect(userId) {
        try {
            await this.connect();
            const result = await this.removeWalletAddress(userId);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async getUserInfoWithConnect(userId) {
        try {
            await this.connect();
            const result = await this.getUserInfo(userId);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async getReferrerWithConnect(userId) {
        try {
            await this.connect();
            const result = await this.getReferrer(userId);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async getBonusCustomAddressesWithConnect(userId) {
        try {
            await this.connect();
            const result = await this.getBonusCustomAddresses(userId);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async useBonusCustomAddressWithConnect(userId) {
        try {
            await this.connect();
            const result = await this.useBonusCustomAddress(userId);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async findReferrerByCodeWithConnect(referralCode) {
        try {
            await this.connect();
            const result = await this.findReferrerByCode(referralCode);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async setReferrerByCodeWithConnect(userId, referralCode) {
        try {
            await this.connect();
            const result = await this.setReferrerByCode(userId, referralCode);
            await this.close();
            return result;
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async recordPaymentWithConnect(referrerId, referredUserId, amount, paymentType, txHash = null) {
        try {
            await this.connect();
            await this.recordPayment(referrerId, referredUserId, amount, paymentType, txHash);
            await this.close();
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    async getUserStatsWithConnect(userId) {
        try {
            await this.connect();

            const userInfo = await this.getUserInfo(userId);
            const payments = [];

            await this.close();

            return {
                userInfo: userInfo,
                payments: payments,
                paymentsCount: payments.length
            };
        } catch (error) {
            await this.close();
            throw error;
        }
    }
}

const referralDbManager = new ReferralDbManager(DB_PATH);

module.exports = {
    ReferralDbManager,
    referralDbManager
};