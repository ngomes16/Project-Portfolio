#pragma once
#include <utils/PNG.h>
#include <iterator>
#include <list>
#include <map>
#include <queue>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

template <typename Data, typename Weight, typename CompareHash>
class Graph {
 public:
  struct Edge;
  struct Vertex;

  struct Edge {
    Weight w;
    Vertex *v1;
    Vertex *v2;
  };

  struct Vertex {
    Data t;
    std::vector<Edge *> edges;
  };

  ~Graph();
  void insertVertex(const std::string &K, const Data &val);
  void removeVertex(const std::string &K);
  std::vector<Edge *> incidentEdges(const std::string &K) const;

  // Returns whether an edge exists directed from node 1 to node 2.
  bool dirEdgeExists(const std::string &K1, const std::string &K2) const;

  // Returns whether an edge exists between node 1 to node 2 directed either
  // way.
  bool areAdjacent(const std::string &K1, const std::string &K2) const;

  void insertEdge(const std::string &K1, const std::string &K2,
                  const Weight &W);
  void removeEdge(const std::string &K1, const std::string &K2);

  // Finds a path from start node to goal node. Zero parameter is used to floor
  // weight-determining function if necessary.
  std::vector<Edge *> findPath(const std::string &_start,
                               const std::string &_goal, unsigned zero = 0);

  // Returns a force-directed visualization of the Graph.
  cs225::PNG *draw(bool forced = false);

  // Iterates over all nodes of the Graph using Breadth-First Search.
  class iterator : std::iterator<std::forward_iterator_tag, Data> {
   public:
    iterator();
    iterator(std::queue<Vertex *> n);
    Data &operator*();
    Data *operator->();
    iterator &operator++();    // prefix increment
    iterator operator++(int);  // postfix increment
    bool operator==(const iterator &) const;
    bool operator!=(const iterator &) const;
    friend iterator Graph<Data, Weight, CompareHash>::begin() const;
    friend iterator Graph<Data, Weight, CompareHash>::end() const;

   private:
    Vertex *v_;
    std::unordered_set<Vertex *> been_visited_;
    std::queue<Vertex *> work_queue_;
    std::queue<Vertex *> never_v2s_;
  };

  iterator begin() const;
  iterator end() const;

 private:
  std::vector<Edge *> _getEdgePath(Vertex *curr,
                                   std::unordered_map<Vertex *, Edge *> edges);

  std::unordered_map<std::string, Vertex *> vertices;

  // Tracks source nodes
  std::unordered_map<Vertex *, bool> never_v2_;
};

// Graph ADT methods
#include "graph.hpp"
//  Iterator methods
#include "graph_iterator.hpp"
