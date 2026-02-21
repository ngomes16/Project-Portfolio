# Database Design

## Entity-Relationship Diagram
![ER Diagram](https://user-images.githubusercontent.com/78306706/197315966-01fb242c-0ef2-461e-8b9f-2174d7f2f669.png)

## Assumptions
- Every Game has a single owning User. Every User can own many Games.
- Every Game is played by multiple Users. Every User can play many Games.
- Every Artifact belongs to a single Game. Every Game can contain many Artifacts.
- Each Artifact can be owned by multiple Users, and each User can own multiple Artifacts.
- Every Artifact contains multiple Facts. Each Fact belongs to a single Artifact.
- The Facts contained in an Artifact have a Display Order in which they are meant to be listed on the Artifact's page.
- Facts and Artifacts each are associated with one Key. Each Key can be unlock several Facts and Artifacts.
- Users have access to any number of keys. Each Key can be possessed by any number of Users.

## Relational Schema
User (\
  id: VARCHAR(36) NOT NULL [PK],\
  username: VARCHAR(20) NOT NULL\
);

Campaign (\
  id: VARCHAR(36) NOT NULL [PK],\
  gm_user_id: VARCHAR(36) NOT NULL [FK to User.id],\
  name: TINYTEXT\
);

Artifact (\
  id: VARCHAR(36) NOT NULL [PK],\
  title: TINYTEXT,\
  created_at: DATETIME,\
  updated_at: DATETIME,\
  access_key: VARCHAR(36) NOT NULL [FK to AccessKey.id],\
  campaign_id: VARCHAR(36) NOT NULL [FK to Campaign.id]\
);

Fact (\
  id: VARCHAR(36) NOT NULL [PK],\
  entry: MEDIUMTEXT,\
  access_key: VARCHAR(36) NOT NULL [FK to AccessKey.id],\
  display_order: INT,\
  artifact_id: VARCHAR(36) NOT NULL [FK to Artifact.id]\
);

AccessKey (\
  id: VARCHAR(36) NOT NULL [PK]\
);

UserAccess (\
  user_id: VARCHAR(36) NOT NULL [PK, FK to User.id],\
  access_key_id: VARCHAR(36) NOT NULL [PK, FK to AccessKey.id],\
  unlocked_at: DATETIME\
);

ArtifactOwnership (\
  user_id: VARCHAR(36) NOT NULL [PK, FK to User.id],\
  artifact_id: VARCHAR(36) NOT NULL [PK, FK to Artifact.id]\
);

CampaignMembership (\
  campaign_id: VARCHAR(36) NOT NULL [PK, FK to Campaign.id],\
  user_id: VARCHAR(36) NOT NULL [PK, FK to User.id]\
)

## DDL
```sql
CREATE TABLE User (
  id VARCHAR(36) NOT NULL,
  username VARCHAR(20) NOT NULL,
  PRIMARY KEY (id)
);

CREATE TABLE Campaign (
  id VARCHAR(36) NOT NULL,
  gm_user_id VARCHAR(36) NOT NULL,
  name TINYTEXT,
  PRIMARY KEY (id),
  CONSTRAINT campaign_gm_fk FOREIGN KEY (gm_user_id) REFERENCES User (id)
);

CREATE TABLE Artifact (
  id VARCHAR(36) NOT NULL,
  title TINYTEXT,
  created_at DATETIME,
  updated_at DATETIME,
  access_key VARCHAR(36) NOT NULL,
  campaign_id VARCHAR(36) NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT artifact_campaign_id_fk FOREIGN KEY (campaign_id) REFERENCES Campaign (id),
  CONSTRAINT artifact_access_key_fk FOREIGN KEY (access_key) REFERENCES AccessKey (id)
);

CREATE TABLE Fact (
  id VARCHAR(36) NOT NULL,
  entry MEDIUMTEXT,
  access_key VARCHAR(36) NOT NULL,
  display_order INT,
  artifact_id VARCHAR(36) NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT fact_access_key_fk FOREIGN KEY (access_key) REFERENCES AccessKey (id),
  CONSTRAINT fact_artifact_fk FOREIGN KEY (artifact_id) REFERENCES Artifact (id)
);

CREATE TABLE AccessKey (
  id VARCHAR(36) NOT NULL,
  PRIMARY KEY (id)
);

CREATE TABLE UserAccess (
  user_id VARCHAR(36) NOT NULL,
  access_key_id VARCHAR(36) NOT NULL,
  unlocked_at DATETIME,
  CONSTRAINT user_access_key_fk FOREIGN KEY (access_key_id) REFERENCES AccessKey (id),
  CONSTRAINT user_access_user_fk FOREIGN KEY (user_id) REFERENCES User (id)
);

CREATE TABLE ArtifactOwnership (
  user_id VARCHAR(36) NOT NULL,
  artifact_id VARCHAR(36) NOT NULL,
  PRIMARY KEY (user_id,artifact_id),
  CONSTRAINT artifact_ownership_artifact_fk FOREIGN KEY (artifact_id) REFERENCES Artifact (id),
  CONSTRAINT artifact_ownership_user_fk FOREIGN KEY (user_id) REFERENCES User (id)
);

CREATE TABLE CampaignMembership (
  campaign_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  PRIMARY KEY (campaign_id,user_id),
  CONSTRAINT campaign_membership_campaign_fk FOREIGN KEY (campaign_id) REFERENCES Campaign (id),
  CONSTRAINT campaign_membership_user_fk FOREIGN KEY (user_id) REFERENCES User (id)
);
```
![image](https://user-images.githubusercontent.com/90533044/197310727-eabd544f-845b-4b29-8ce7-632b9d0ef23b.png)

