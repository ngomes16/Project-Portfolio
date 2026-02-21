#include <graph/graph.h>

#include <map>
#include <string>
#include <vector>

#include "../catch.hpp"

Graph<int, int, int> make_graph() {
  Graph<int, int, int> g;
  std::map<std::string, int> vs{
      {"one", 1}, {"two", 2}, {"three", 3}, {"four", 4}, {"five", 5}};
  for (const auto &v : vs) {
    g.insertVertex(v.first, v.second);
  }
  g.insertEdge("one", "two", 1);
  g.insertEdge("one", "three", 1);
  g.insertEdge("two", "five", 1);
  return g;
}

TEST_CASE("Graph: Inserting vertices and edges", "") {
  SECTION("Basic insertion", "") {
    Graph<int, int, int> g = make_graph();
    REQUIRE(g.dirEdgeExists("one", "two"));
    REQUIRE_FALSE(g.dirEdgeExists("two", "one"));
    REQUIRE(g.areAdjacent("one", "two"));
    REQUIRE(g.areAdjacent("two", "one"));
  }
}

TEST_CASE("Removing vertices and edges", "") {
  Graph<int, int, int> g = make_graph();

  SECTION("Vertex removal", "") {
    g.removeVertex("one");
    REQUIRE_FALSE(g.areAdjacent("one", "two"));
    REQUIRE_FALSE(g.areAdjacent("one", "three"));
    REQUIRE(g.areAdjacent("two", "five"));
  }

  SECTION("Edge removal", "") {
    g.removeEdge("one", "two");
    REQUIRE_FALSE(g.areAdjacent("one", "two"));
    REQUIRE(g.areAdjacent("one", "three"));
    REQUIRE(g.areAdjacent("two", "five"));
  }
}

TEST_CASE("Incident edges", "") {
  Graph<int, int, int> g = make_graph();
  std::vector<Graph<int, int, int>::Edge *> ie = g.incidentEdges("one");
  std::vector<int> v{2, 3};
  for (const auto &e : ie) {
    REQUIRE(std::find(v.begin(), v.end(), e->v2->t) != v.end());
    std::remove(v.begin(), v.end(), e->v2->t);
  }
}
