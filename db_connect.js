const mysql = require('mysql2/promise');
require('dotenv').config();

async function getDbConnection() {
    try {
        const connection = await mysql.createConnection({
            host: process.env.DB_HOST,
            user: process.env.DB_USER,
            password: process.env.DB_PASSWORD,
            database: process.env.DB_NAME
        });

        return connection;
    } catch (error) {
        console.error('Error connecting to MySQL Server:', error.message);
        return null;
    }
}

module.exports = { getDbConnection };