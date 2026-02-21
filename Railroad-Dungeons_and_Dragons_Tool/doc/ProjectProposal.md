# Railroad

## Summary

Railroad is a web application tool for Dungeons and Dragons campaign creation and management. As D&D games involve hidden information being revealed to players by events that occur in the game, campaign creators (aka the dungeon master, or DM) write detailed descriptions for things like locations, characters, and items which have individual facts about them that are hidden from the players until the dungeon master chooses to make the information known. In most games, players wind up having to take their own notes on what is revealed to them, making for redundant effort for each player. Railroad is a tool to allow DMs to store all their notes in one places and share facts about the world they've built with players in a few simple clicks, and to enable them to reveal each fact individually without sharing its entire containing document.

## Description

Users join workspaces called Campaigns, create top-level documents called Artifacts, capable of containing one or more Facts, which are individual sections containing pieces of information. Each Fact and Artifact has a visibility key, which can be given to other users by the creating user to allow them to view the item. Facts meant to be shared together can be grouped together under a common key, or attached to the key of their parent Artifact if they are meant to be visible the moment an Artifact is shared.

## Usefulness

Dungeons and Dragons is a globally beloved game with a variety of web tools built for various aspects of the game, but notes sharing is largely left to the physical medium, or sharing individual files via direct communication. Our web application will allow dungeon masters and players to create accounts and easily manage multiple campaigns. DMs can store all of their writing in one central place from which it is easy to share, and can format their documents to share relevant sections only to their players, making it largely useful to the game's community. 

## Realness

Our data will consist of Facts comprised of generated text content, and Users with generated personal data. Publicly available sample campaign data can also be used for our datasets.

## Functionality

Users join a campaign, created by their Game Master. All users in a campaign, including the GM, can create Artifact documents, and add Facts to each Artifact. Facts and Artifacts can then be shared with other users within the campaign, or made public to the whole campaign.

For extended functionality, we would like to support media like images and music, and theory/comment systems for players to be able to annotate Facts shared with them.

## UI Mockup:

![UI Mockup](https://user-images.githubusercontent.com/78306706/192434694-8a387cba-166d-4624-a4b2-3533e5641f6f.png)


## Work Distribution:

Justin:
* Backend: Authentication (+ related database tables, relations, constraints)
* Backend: User sessions (+ related database tables, relations, constraints)

Cristian:
* Frontend: Page templates and layouts
* Backend: Writing required database stored procedures
* Backend: Creating mock data

Nate:
* Frontend: Page interactivity, hydration
* Backend: Writing required database queries
* Backend: Creating mock data

Rishi: 
* Backend: Designing API endpoints
* Backend: Creating database interfaces to backend
