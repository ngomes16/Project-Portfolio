#include <graph/graph.h>
#include "../catch.hpp"

TEST_CASE("Graph: Iterators") {
  Graph<char, int, int> g;
  g.insertVertex("A", 'A');

  SECTION("Begin iterator") {
    Graph<char, int, int>::iterator it = g.begin();
    REQUIRE(*it == 'A');
  }

  SECTION("Iterator equality") {
    REQUIRE(g.begin() == g.begin());
    REQUIRE(g.end() == g.end());
    REQUIRE_FALSE(g.begin() == g.end());
  }

  SECTION("Iterator inequality") {
    REQUIRE_FALSE(g.begin() != g.begin());
    REQUIRE_FALSE(g.end() != g.end());
    REQUIRE(g.begin() != g.end());
  }

  SECTION("Iterator increment") {
    g.insertVertex("B", 'B');

    SECTION("Disconnected components") {
      Graph<char, int, int>::iterator it = g.begin();
      SECTION("Pre-increment") {
        char c = *(++it);
        REQUIRE(c == *it);
      }

      SECTION("Post-increment") {
        char c = *(it++);
        REQUIRE(c == *(g.begin()));
        REQUIRE(c != *it);
        REQUIRE(*it == *(++g.begin()));
      }
    }

    SECTION("Connected components") {
      g.insertEdge("A", "B", 1);
      Graph<char, int, int>::iterator it = g.begin();
      SECTION("Pre-increment") {
        char c = *(++it);
        REQUIRE(c == *it);
      }

      SECTION("Post-increment") {
        char c = *(it++);
        REQUIRE(c == *(g.begin()));
        REQUIRE(c != *it);
        REQUIRE(*it == *(++g.begin()));
      }
    }
  }

  SECTION("End iterator") {
    Graph<char, int, int>::iterator it = g.begin();
    REQUIRE(it != g.end());
    ++it;
    REQUIRE_FALSE(it != g.end());
  }

  SECTION("Pointer-like access") {
    struct Thing {
      int a = 0;
    };
    Graph<Thing, int, int> g;
    Thing one;
    one.a = 1;
    g.insertVertex("thing 1", one);

    REQUIRE(g.begin()->a == 1);
  }
}