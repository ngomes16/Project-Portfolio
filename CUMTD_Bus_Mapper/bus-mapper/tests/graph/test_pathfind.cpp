#include <graph/graph.h>
#include <map>
#include <string>
#include <vector>
#include "../catch.hpp"

struct CH {
  static int G(Graph<int, int, CH>::Edge *e, unsigned zero) { return e->w; }
  static int H(Graph<int, int, CH>::Vertex *v, Graph<int, int, CH>::Vertex *w) {
    return w->t - v->t;
  }
};

Graph<int, int, CH> make_pathfind_graph() {
  Graph<int, int, CH> g;
  std::map<std::string, int> vs{
      {"one", 1}, {"two", 2}, {"three", 3}, {"four", 4}, {"five", 5}};
  for (const auto &v : vs) {
    g.insertVertex(v.first, v.second);
  }
  g.insertEdge("one", "two", 1);
  g.insertEdge("two", "four", 0);
  g.insertEdge("one", "three", 1);
  g.insertEdge("three", "four", 1);
  return g;
}

TEST_CASE("Path-finding", "") {
  Graph<int, int, CH> g = make_pathfind_graph();

  SECTION("Invalid vertex", "") {
    SECTION("Invalid start", "") {
      std::vector<Graph<int, int, CH>::Edge *> e = g.findPath("one", "five");
      REQUIRE(e.empty());
    }
    SECTION("Invalid goal", "") {
      std::vector<Graph<int, int, CH>::Edge *> e = g.findPath("five", "four");
      REQUIRE(e.empty());
    }
  }

  SECTION("Best of two paths", "") {
    std::vector<Graph<int, int, CH>::Edge *> e = g.findPath("one", "four");
    REQUIRE(e.size() == 2);
    REQUIRE(e[0]->v1->t == 1);
    REQUIRE(e[0]->v2->t == 2);
    REQUIRE(e[1]->v1->t == 2);
    REQUIRE(e[1]->v2->t == 4);
  }
}
