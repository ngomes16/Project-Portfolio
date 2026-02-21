#include <graph/graph.h>

#include <map>
#include <string>
#include <unordered_set>
#include <vector>

#include "../catch.hpp"

SCENARIO("Graph: Traversal") {
  GIVEN("A line graph") {
    Graph<char, int, int> g;
    std::map<std::string, char> vs{{"A", 'A'}, {"B", 'B'}, {"C", 'C'}};
    for (const auto &v : vs) {
      g.insertVertex(v.first, v.second);
    }
    g.insertEdge("A", "B", 1);
    g.insertEdge("B", "C", 1);

    WHEN("The graph is traversed") {
      std::vector<char> cs{'A', 'B', 'C'};
      THEN("The traversal is in the right order") {
        unsigned i = 0;
        for (char c : g) {
          REQUIRE(c == cs[i++]);
        }
      }
    }
  }

  GIVEN("An elbow graph") {
    Graph<char, int, int> g;
    std::map<std::string, char> vs{{"A", 'A'}, {"B", 'B'}, {"C", 'C'}};
    for (const auto &v : vs) {
      g.insertVertex(v.first, v.second);
    }
    g.insertEdge("A", "B", 1);
    g.insertEdge("A", "C", 1);

    WHEN("The graph is traversed") {
      std::vector<char> cs{'A', 'B', 'C'};
      THEN("The traversal is in the right order") {
        unsigned i = 0;
        for (char c : g) {
          REQUIRE(c == cs[i++]);
        }
      }
    }
  }

  GIVEN("A complete binary tree") {
    Graph<char, int, int> g;
    std::map<std::string, char> vs{{"A", 'A'}, {"B", 'B'}, {"C", 'C'},
                                   {"D", 'D'}, {"E", 'E'}, {"F", 'F'},
                                   {"G", 'G'}};
    for (const auto &v : vs) {
      g.insertVertex(v.first, v.second);
    }
    g.insertEdge("A", "B", 1);
    g.insertEdge("A", "C", 1);
    g.insertEdge("B", "D", 1);
    g.insertEdge("B", "E", 1);
    g.insertEdge("C", "F", 1);
    g.insertEdge("C", "G", 1);

    WHEN("The graph is traversed") {
      std::vector<char> cs{'A', 'B', 'C', 'D', 'E', 'F', 'G'};
      THEN("The traversal is in the right order") {
        unsigned i = 0;
        for (char c : g) {
          REQUIRE(c == cs[i++]);
        }
      }
    }
  }

  GIVEN("A simple cyclical graph") {
    Graph<char, int, int> g;
    std::map<std::string, char> vs{{"A", 'A'}, {"B", 'B'}, {"C", 'C'}};
    for (const auto &v : vs) {
      g.insertVertex(v.first, v.second);
    }
    g.insertEdge("A", "B", 1);
    g.insertEdge("B", "C", 1);
    g.insertEdge("C", "A", 1);

    WHEN("The graph is traversed") {
      std::unordered_set<char> cs;
      THEN("The traversal visits all and ends") {
        unsigned i = 0;
        for (char c : g) {
          REQUIRE(cs.count(c) == 0);
          cs.insert(c);
        }
        REQUIRE(cs.count('A') == 1);
        REQUIRE(cs.count('B') == 1);
        REQUIRE(cs.count('C') == 1);
      }
    }
  }
}