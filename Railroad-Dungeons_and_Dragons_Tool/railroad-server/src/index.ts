import express, { Router } from 'express';
import session from 'express-session';
import Database from './lib/Database';

import SearchRouter from './routers/SearchRouter';
import ArtifactRouter from './routers/ArtifactRouter';
import FactRouter from './routers/FactRouter';
import FriendRouter from './routers/FriendRouter';
import AuthRouter from './routers/AuthRouter';

const app = express();

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(session({
  secret: 'ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc',
  resave: false,
  saveUninitialized: false
}));

const port = 5000;

const database = new Database();

const authRouter = new AuthRouter(database);

app.use('/auth', authRouter.router_);

const api = Router();

api.use('/friends', new FriendRouter(database).router_);

api.use('/artifact', new ArtifactRouter(database).router_);

api.use('/fact', new FactRouter(database).router_);

api.use('/search', new SearchRouter(database).router_);

app.use('/api', authRouter.hasSession);
app.use('/api', api);

app.listen(port, () => {
  console.log(`Example app listening on port ${port}`);
});
