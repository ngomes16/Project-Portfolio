
# SFPA Project Proposal

###  1. Leading Question
  Using the publicly available bus routing information of the [Champaign-Urbana Mass Transit District (CUMTD)](https://mtd.org/), is it possible to accurately map the bus routes as a graph of stations joined by bus lines, and to then use that structure to visually represent routes on an overhead street map and give a user the fastest possible travel itinerary to any one station from another at a given time of day?
    
### 2.  Dataset Acquisition and Processing
  The dataset to be used is, as mentioned above, the [GTFS](http://code.google.com/transit/spec/transit_feed_specification.html)-format data obtainable [here](https://developer.cumtd.com/) from the CUMTD for all bus stations and lines in the Champaign-Urbana district. This data can be queried from their freely and readily available API, and comes as CSV files with the Google-designed format for transit data, which we can then process directly into a node-vertex format as a multigraph, wherein each graph node is a station, and station can have multiple edges connecting them, each representing a single bus line. This processed data can then be stored for further use in analysis. The MTD data following such a well-supported format allows us to easy check for errors or missing entries with preexisting validators like those available [here](https://developers.google.com/transit/gtfs/guides/tools). 
    
### 3.  Graph Algorithms
- BFS Traversal

  Using BFS, we can traverse through the nodes (stations) of the graph to determine the number of connected components, and which component each node belongs to. This will allow us to precompute whether a node is directly reachable from another node before we begin fastest-route finding.

- Graph visualization

  This project involves the use of the data collected to project bus routes using force direction.

- Fastest-route finding

  Given a start station and an end station by the user, we can use our data to find the optimal route between the two, with or without changing buses, at any given time of day.
  
  For fastest-route finding, we expect to take in four separate inputs: from_station, to_station, from_time, to_time. These inputs will be used to traverse a pre-created graph consisting of stations (vertices) and bus connections (edges) using the A* algorithm to find the shortest path within the given time range.

  As the goal is to find the fastest route, the graph will be weighted according to the arrival time at the destination node for each edge, represented as the `(arrival_time - from_time)`. We will also ignore all edges that depart before `from_time` and arrive after `to_time` during traversal to ensure we do not traverse any negatively-weighted edges.

  With A*, we intend to use the Great-circle distance as a heuristic. We believe this is an admissible heuristic as the direct distance between two stations will never result in an overestimation.

  Our target big-O runtime is expected to be O(|E|), where E describes the edges (direct connecting path between two stations) of our graph.
    
### 4.  Timeline
- Week 1:
   ----
   - Obtain and process MTD data
   - Map out and implement node structure
   - Implement graph ADT
- Week 2:
   ----
   - Implement basic node traversal
   - Implement fastest-route finding
 - Week 3:
   ----
    - Implement map visualization with force direction
