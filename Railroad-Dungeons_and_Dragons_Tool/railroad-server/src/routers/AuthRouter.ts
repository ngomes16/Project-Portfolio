/* eslint-disable functional/no-class */
import { Request, Response } from 'express';
import { NextFunction } from 'express-serve-static-core';
import bcrypt from 'bcrypt';

import Database from '../lib/Database';

import BaseRouter from './BaseRouter';

declare module 'express-session' {
  interface SessionData {
    userId: string;
  }
}

class AuthRouter extends BaseRouter {
  private sessions: Set<string>;

  constructor(db: Database) {
    super(db);

    this.sessions = new Set();
    this.sessions.add('debug_user');

    this.router_.get('/status', this.status.bind(this));

    this.router_.post('/login', this.login.bind(this));
    this.router_.post('/logout', this.logout.bind(this));
    this.router_.post('/signup', this.signup.bind(this));

    this.hasSession = this.hasSession.bind(this);
  }

  private _isLoggedIn(req: Request) {
    return req.session.userId && this.sessions.has(req.session.userId);
  }

  private _addLogin(req: Request, userId: string) {
    this.sessions.add(userId);
    req.session.userId = userId;
  }

  public hasSession(req: Request, _res: Response, next: NextFunction) {
    if (!this._isLoggedIn(req)) return next("Not logged in.");

    return next();
  }

  private async status(req: Request, res: Response) {
    if (!this._isLoggedIn(req)) return res.sendStatus(401);

    return res.send({ userId: req.session.userId });
  }

  private async login(req: Request, res: Response) {
    if (this._isLoggedIn(req)) return res.sendStatus(400);
    if (!('username' in req.body)) return res.sendStatus(400);
    if (!('password' in req.body)) return res.sendStatus(400);

    const results = await this.db_.execute(
      `
            SELECT id, password
            FROM User u
            WHERE u.username = :username
            LIMIT 1;
      `,
      { username: req.body.username }
    ) as Array<{ id: string, password: string | null }>;

    if (results.length === 0) return res.sendStatus(401);
    if (results[0].password === null) return res.sendStatus(401);

    if (!(await bcrypt.compare(req.body.password, results[0].password))) {
      return res.sendStatus(401);
    }

    this._addLogin(req, results[0].id);

    return res.sendStatus(200);
  }

  private async logout(req: Request, res: Response) {
    if (!this._isLoggedIn(req)) return res.sendStatus(401);

    this.sessions.delete(req.session.userId);
    delete req.session.userId;

    return res.sendStatus(200);
  }

  private async signup(req: Request, res: Response) {
    if (this._isLoggedIn(req)) return res.sendStatus(400);
    if (!('username' in req.body)) return res.sendStatus(400);
    if (!('password' in req.body)) return res.sendStatus(400);

    const results = await this.db_.execute(
      `
            SELECT id, password
            FROM User u
            WHERE u.username = :username
            LIMIT 1;
      `,
      { username: req.body.username }
    ) as Array<{ id: string, password: string | null }>;

    if (results.length === 0) return res.sendStatus(401);
    if (results[0].password !== null) return res.sendStatus(401);

    const hash = await bcrypt.hash(req.body.password, 10);

    await this.db_.execute(
      `
            UPDATE User u
            SET password = :password
            WHERE u.username = :username;
        `,
      { username: req.body.username, password: hash }
    );

    this._addLogin(req, results[0].id);

    return res.sendStatus(200);
  }
}

export default AuthRouter;
