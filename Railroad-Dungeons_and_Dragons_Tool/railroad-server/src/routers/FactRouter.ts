/* eslint-disable functional/no-class */
import { Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';

import Database from '../lib/Database';

import BaseRouter from './BaseRouter';

class FactRouter extends BaseRouter {
  constructor(db: Database) {
    super(db);

    this.router_.get('/list/:artifactId', this.getAll.bind(this));
    this.router_.get('/:factId', this.get.bind(this));
    this.router_.delete('/:factId', this.deleteFact.bind(this));
    this.router_.put('/:artifactId', this.createNewFact.bind(this));
    this.router_.post('/:factId', this.updateEntry.bind(this));
  }

  private async getAll(req: Request, res: Response) {
    if (!('artifactId' in req.params)) {
      return res.sendStatus(400);
    }

    const results = await this.db_.execute(
      `
            SELECT id, artifact_id
            FROM Fact a
            WHERE a.artifact_id = :id
            ORDER BY a.display_order;
        `,
      {
        id: req.params.artifactId,
      }
    );

    return res.send(results);
  }

  private async get(req: Request, res: Response) {
    if (!('factId' in req.params)) {
      return res.sendStatus(400);
    }

    const results = await this.db_.execute(
      `
            SELECT *
            FROM Fact a
            WHERE a.id = :id;
        `,
      {
        id: req.params.factId,
      }
    );

    return res.send(results);
  }

  private async createNewFact(req: Request, res: Response) {
    if (!('artifactId' in req.params)) return res.sendStatus(400);

    const id = uuidv4();
    const access_key = uuidv4();
    let results = await this.db_.execute(
      `
            INSERT INTO AccessKey(id) VALUES (:key)
        `,
      {
        key: access_key,
      }
    );

    results = await this.db_.execute(
      `
            SELECT MAX(display_order) as max_order FROM Fact where artifact_id = :artifact_id;
        `,
      {
        artifact_id: req.params.artifactId,
      }
    );

    results = await this.db_.execute(
      `
            INSERT INTO Fact(id, access_key, artifact_id, display_order)
            VALUES (:id, :access_key, :artifact_id, :order);
        `,
      {
        id: id,
        access_key: access_key,
        artifact_id: req.params.artifactId,
        order: results[0].max_order + 1,
      }
    );

    return res.send({
      id: id,
      access_key: access_key,
    });
  }

  private async updateEntry(req: Request, res: Response) {
    if (!('factId' in req.params)) {
      return res.sendStatus(400);
    }

    const body = req.body;

    if (!('entry' in body)) {
      return res.sendStatus(400);
    }

    await this.db_.execute(
      `
            UPDATE Fact a
            SET entry = :entry
            WHERE a.id = :id;
        `,
      { id: req.params.factId, entry: body.entry }
    );

    return res.sendStatus(200);
  }

  private async deleteFact(req: Request, res: Response) {
    if (!('factId' in req.params)) {
      return res.sendStatus(400);
    }

    // DB must clear unused access keys.
    const results = await this.db_.execute(
      `
            DELETE FROM Fact WHERE id = :id;
        `,
      {
        id: req.params.factId,
      }
    );

    return res.sendStatus(200);
  }
}

export default FactRouter;
