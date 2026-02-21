# CUMTD Bus Mapper

A graph-based transit routing system that models the Champaign-Urbana Mass Transit District (CUMTD) bus network and finds the fastest routes between stations using the A* search algorithm.

## Features

- **A\* Pathfinding** — Finds the fastest route between any two bus stations at a given time of day using a great-circle distance heuristic
- **Graph Visualization** — Generates PNG images of the bus network using both geographic (lat/lon) and force-directed layouts
- **BFS Traversal** — Identifies connected components across the bus network via breadth-first search
- **Time-Aware Routing** — Filters available routes by current day of week and time, so results reflect real-world schedules
- **GTFS Data Pipeline** — Python scripts download and parse official CUMTD GTFS data into structured JSON for the C++ engine

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Core Engine** | C++11 |
| **Build System** | CMake (2.8+) |
| **Data Processing** | Python 3 (urllib, csv, json, dateutil) |
| **JSON Parsing** | nlohmann/json |
| **Image Generation** | lodepng, custom PNG/HSLAPixel utilities |
| **Testing** | Catch2 |
| **Data Source** | CUMTD GTFS API |

## Project Structure

```
CUMTD_Bus_Mapper/
├── bus-mapper/
│   ├── include/
│   │   ├── graph/          # Template graph ADT, A* implementation, BFS iterator
│   │   ├── bus/            # Station, Stop, Trip, Platform data structures
│   │   └── utils/          # PNG rendering, color utilities, disjoint sets
│   ├── src/
│   │   ├── pathfind.cpp    # Pathfinding CLI entry point
│   │   ├── visualize.cpp   # Visualization CLI entry point
│   │   ├── bus/            # Graph construction from JSON data
│   │   └── utils/          # Visualizer drawing logic
│   └── tests/              # Catch2 test suite
├── jtfs/
│   ├── parse.py            # GTFS data download and processing
│   └── jtfs_*.json         # Processed station, platform, route, trip data
└── visualizer/             # Matplotlib-based visualization helper
```

## Getting Started

### Prerequisites

- C++11 compatible compiler (GCC/Clang)
- CMake 2.8+
- Python 3

### Build

```bash
cd bus-mapper
mkdir build && cd build
cmake ..
make pathfind     # Build the pathfinding tool
make visualize    # Build the visualization tool
make test         # Build the test suite
```

### Prepare Data

```bash
cd jtfs
python parse.py   # Downloads GTFS data and generates JSON files
```

### Run

```bash
cd bus-mapper/build

# Find the fastest route between two stations
./pathfind ILLINI ALTGELD

# Generate a geographic layout of the network
./visualize output.png

# Generate a force-directed layout
./visualize output.png -f

# Run the test suite
./test
```

## How It Works

### Graph Construction
The Python pipeline downloads CUMTD GTFS data and parses it into JSON files representing stations, platforms, routes, and trips. The C++ engine reads these files and constructs a weighted directed graph where stations are vertices and bus connections are edges, filtered by the current day and time.

### A* Pathfinding
The search uses a priority queue with edge weights based on travel time (arrival minus departure) and a great-circle distance heuristic to efficiently find the shortest path. The algorithm filters edges by departure time so only reachable connections are considered.

### Force-Directed Visualization
An iterative physics simulation applies repulsive forces between all nodes and attractive forces along edges, with a cooling schedule over 50 iterations, to produce a readable network layout rendered as a PNG image.

### Template Graph ADT
The graph is implemented as a generic `Graph<Data, Weight, CompareHash>` template, making it reusable beyond transit data. A functor pattern provides pluggable heuristic and weight functions for the A* algorithm.
