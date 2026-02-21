/* eslint-disable functional/no-class */
import { Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';

import Database from '../lib/Database';

import BaseRouter from './BaseRouter';

class ArtifactRouter extends BaseRouter {
  constructor(db: Database) {
    super(db);

    this.router_.get('/:artifactId', this.get.bind(this));
    this.router_.post('/:artifactId', this.updateTitle.bind(this));
    this.router_.delete('/:artifactId', this.deleteArtifact.bind(this));
    this.router_.put('/', this.createNewArtifact.bind(this));
  }

  private async get(req: Request, res: Response) {
    if (!('artifactId' in req.params)) {
      return res.sendStatus(400);
    }

    const results = await this.db_.execute(
      `
            SELECT *
            FROM Artifact a
            WHERE a.id = :id;
        `,
      {
        id: req.params.artifactId,
      }
    );

    return res.send(results);
  }

  private async updateTitle(req: Request, res: Response) {
    if (!('artifactId' in req.params)) {
      return res.sendStatus(400);
    }

    if (!('title' in req.query)) {
      return res.sendStatus(400);
    }

    await this.db_.execute(
      `
            UPDATE Artifact a
            SET title = :title
            WHERE a.id = :id;
        `,
      { id: req.params.artifactId, title: req.query.title }
    );

    return res.sendStatus(200);
  }

  private async createNewArtifact(_req: Request, res: Response) {
    // if (!('keyword' in req.query)) return res.sendStatus(400);
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
    console.log(id);
    results = await this.db_.execute(
      `
            INSERT INTO Artifact(id, access_key)
            VALUES (:id, :access_key)
        `,
      {
        id: id,
        access_key: access_key,
      }
    );
    return res.send({
      id: id,
    });
  }

  private async deleteArtifact(req: Request, res: Response) {
    if (!('artifactId' in req.params)) {
      return res.sendStatus(400);
    }

    // DB must clear unused access keys.
    let results = await this.db_.execute(
      `
            DELETE FROM Fact WHERE artifact_id = :id;
        `,
      {
        id: req.params.artifactId,
      }
    );
    console.log('Fact:' + results);

    // DB must clear unused access keys.
    results = await this.db_.execute(
      `
            DELETE FROM ArtifactOwnership WHERE artifact_id = :id;
        `,
      {
        id: req.params.artifactId,
      }
    );
    console.log('Fact:' + results);

    results = await this.db_.execute(
      `
            DELETE FROM Artifact WHERE id = :id;
        `,
      {
        id: req.params.artifactId,
      }
    );
    console.log('Artifact:' + results);

    return res.sendStatus(200);
  }
}

export default ArtifactRouter;
