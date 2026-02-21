# Advanced Queries

## Query 1: Search artifacts and facts by title and entry
Uses subqueries, joins and set operations.
```sql
SELECT title FROM (
	(
		SELECT a.title
		FROM Artifact a
		WHERE a.title LIKE "INSERT_QUERY_HERE"
	) UNION (
		SELECT DISTINCT a.title
		FROM Fact f JOIN Artifact a ON a.id = f.artifact_id
		WHERE f.entry LIKE "INSERT_QUERY_HERE"
	)
) r
ORDER BY title ASC;
```
![](https://cdn.discordapp.com/attachments/903052212102660166/1033183065553506355/unknown.png)

### Indexing

The `EXPLAIN ANALYZE` results for the following attempts are available in `search_result.txt`.

#### Attempt 1: FULLTEXT on Artifact Title
Since search is at least partially dependent on the lookup speeds on the artifact title, we believed that this would improve speeds on title queries. We felt confident using FULLTEXT as the titles are stored as TINYTEXT, which should be small enough for indexing. We observed a query performance that was slower than the baseline.

#### Attempt 2: PARTIAL (50) on Artifact Title
Since it was apparent that using the entirety of the title, a TINYTEXT, was too slow for indexing purposes, we decided to try a partial index to improve performance. We observed a query performance that was approximately the same as baseline.

#### Attempt 3: PARTIAL (50) on Fact Entry
Finally, we tried to tackle the speed of lookup for fact entries. Since we noticed that the contents of TINYTEXT are already too big for indexing, we decided to use a PARTIAL index directly. We picked a size of 50 as the average English word has 5 characters, and the size allows us to store indexes of approximately 10 words at a time. We observed significantly improved performance over baseline.

#### Summary
From the performance observations above, we decided to keep the indices from Attempt 2 and 3 to optimize performance for our search query. We dropped Attempt 1 as it was not ideal, and performed worse than Attempt 2 on the same column.

## Query 2: Find all other users that a given user can interact with
Uses subqueries and joins.
```sql
SELECT DISTINCT u.username
FROM User u JOIN CampaignMembership cm ON u.id = cm.user_id
WHERE cm.campaign_id IN (
	SELECT campaign_id
	FROM CampaignMembership
	WHERE user_id = "INSERT_USER_ID_HERE"
);
```
![](https://cdn.discordapp.com/attachments/903052212102660166/1033183321343152158/unknown.png)

### Indexing

The `EXPLAIN ANALYZE` results for the following attempts are available in `friend_result.txt`.

#### Attempt 1: BTree on CampaignMembership Campaign ID
For this query, we repeatedly lookup users with the same Campaign ID as the User. Given our dataset, a Campaign is more likely to have more Users than a User would have Campaigns. We believed that using this fact for indexing would give better results. We observed approximately the same performance as baseline.

#### Attempt 2: BTree on CampaignMembership User ID
Following a similar thought process as above, we decided to try creating an index on User ID. We observed no performance differences against baseline. We believe that since CampaignMembership is a junction table, the default index is likely already a clustered BTree index on a combination of Campaign ID and User ID, so manually adding narrower indexes did not help performance.

#### Attempt 3: Hash on CampaignMembership Campaign ID
We revisited Attempt 1, and observed that our queries would benefit from a degree of temporal locality, which theoretically would not benefit from the BTree index that we selected earlier, but may from using a Hash index. We observed marginally faster performance than baseline.

#### Summary
As the query already had acceptable performance, and none of our manually-added indexes had significant performance impacts, we decided to continue using the default primary key index provided by the database.
