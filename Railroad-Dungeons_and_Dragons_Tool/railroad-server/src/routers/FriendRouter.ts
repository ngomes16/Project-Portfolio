/* eslint-disable functional/no-class */
import { Request, Response } from 'express';

import Database from '../lib/Database';

import BaseRouter from './BaseRouter';

class FriendRouter extends BaseRouter {
  constructor(db: Database) {
    super(db);

    this.router_.get('/:userId?', this.get.bind(this));
  }

  private async get(req: Request, res: Response) {
    const userId = req.params.userId ?? req.session.userId;

    if (!userId) {
      return res.sendStatus(400);
    }

    const results = await this.db_.execute(
      `
      SELECT DISTINCT u.id, u.username
      FROM User u JOIN CampaignMembership cm ON u.id = cm.user_id
      WHERE cm.campaign_id IN (
          SELECT campaign_id
          FROM CampaignMembership cm1
          WHERE cm1.user_id = :userId
      );
        `,
      { userId }
    );

    return res.send(results);
  }
}

export default FriendRouter;
