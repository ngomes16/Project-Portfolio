import mysql, { Connection } from 'mysql2';

type SQLParam = null | string | number | boolean | object;

export default class Database {
    private conn_: Connection;

    constructor() {
        this.conn_ = mysql.createConnection({
            host: '34.70.249.231',
            user: 'server',
            password: 'server',
            database: 'db-02',
            namedPlaceholders: true
        });
    }

    execute(sql: string, params: SQLParam[] | { [key: string]: SQLParam }): Promise<unknown> {
        return new Promise((resolve, reject) => {
            this.conn_.execute(sql, params, (err, res) => {
                if (err) reject(err);

                resolve(res);
            });
        });
    }
}