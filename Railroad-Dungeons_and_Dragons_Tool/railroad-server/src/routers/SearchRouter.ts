import { Request, Response } from 'express';

import BaseRouter from './BaseRouter';
import Database from '../lib/Database';

class SearchRouter extends BaseRouter {
  constructor(db: Database) {
    super(db);

    this.router_.get('/', this.search.bind(this));
  }

  private async search(req: Request, res: Response) {
    if (!('keyword' in req.query)) {
      return res.sendStatus(400);
    }

    const results = await this.db_.execute(
      `
            SELECT * FROM (
                (
                    SELECT a.id, a.title
                    FROM Artifact a
                    WHERE a.title LIKE CONCAT('%', :keyword, '%')
                ) UNION (
                    SELECT DISTINCT a.id, a.title
                    FROM Fact f JOIN Artifact a ON a.id = f.artifact_id
                    WHERE f.entry LIKE CONCAT('%', :keyword, '%')
                )
            ) r
            ORDER BY CASE
            WHEN title LIKE CONCAT(:keyword, '%') THEN 0
            WHEN title LIKE CONCAT('% %', :keyword, '% %') THEN 1
            WHEN title LIKE CONCAT('%', :keyword) THEN 2
            ELSE 3
            END;
        `,
      {
        keyword: req.query.keyword as string,
      }
    );

    return res.send(results);
  }
}

export default SearchRouter;
