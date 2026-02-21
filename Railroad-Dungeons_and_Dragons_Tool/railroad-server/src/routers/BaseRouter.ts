import { Router } from 'express';
import Database from '../lib/Database';

abstract class BaseRouter {
    public router_: Router;
    public db_: Database;

    constructor(db: Database) {
        this.router_ = Router();
        this.db_ = db;
    }
}

export default BaseRouter;