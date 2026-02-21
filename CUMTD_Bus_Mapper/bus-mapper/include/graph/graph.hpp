#pragma once
#include <utils/visualizer.h>

#include <algorithm>
#include <cmath>
#include <deque>
#include <iostream>
#include <limits>

template <typename Data, typename Weight, typename CompareHash>
Graph<Data, Weight, CompareHash>::~Graph() {
  std::unordered_set<Edge *> edges;
  for (auto it : vertices) {
    for (auto e : it.second->edges) delete e;
    delete it.second;
  }
}
/**
 *  Graph ADT methods
 */
template <typename Data, typename Weight, typename CompareHash>
void Graph<Data, Weight, CompareHash>::insertVertex(const std::string &K,
                                                    const Data &val) {
  Vertex *vtx = new Vertex();
  vtx->t = val;
  vertices.emplace(K, vtx);
  never_v2_[vtx] = true;
}

template <typename Data, typename Weight, typename CompareHash>
void Graph<Data, Weight, CompareHash>::removeVertex(const std::string &K) {
  auto it = vertices.find(K);
  if (it != vertices.end()) {
    for (auto e : it->second->edges) {
      delete e;
    }
    delete it->second;
    vertices.erase(it);
  }
}

template <typename Data, typename Weight, typename CompareHash>
std::vector<typename Graph<Data, Weight, CompareHash>::Edge *>
Graph<Data, Weight, CompareHash>::incidentEdges(const std::string &K) const {
  Vertex *v1 = vertices.at(K);
  return v1->edges;
}

template <typename Data, typename Weight, typename CompareHash>
bool Graph<Data, Weight, CompareHash>::dirEdgeExists(
    const std::string &K1, const std::string &K2) const {
  if (vertices.count(K1) == 0 || vertices.count(K2) == 0) return false;

  Vertex *vert2 = vertices.at(K2);

  for (const auto &edge : vertices.at(K1)->edges) {
    if (edge->v2 == vert2) return true;
  }

  return false;
}

template <typename Data, typename Weight, typename CompareHash>
bool Graph<Data, Weight, CompareHash>::areAdjacent(
    const std::string &K1, const std::string &K2) const {
  return dirEdgeExists(K1, K2) || dirEdgeExists(K2, K1);
}

template <typename Data, typename Weight, typename CompareHash>
void Graph<Data, Weight, CompareHash>::insertEdge(const std::string &K1,
                                                  const std::string &K2,
                                                  const Weight &W) {
  Edge *e = new Edge();
  e->w = W;
  e->v1 = vertices.at(K1);
  e->v2 = vertices.at(K2);
  vertices.at(K1)->edges.push_back(e);
  never_v2_[e->v2] = false;
}

template <typename Data, typename Weight, typename CompareHash>
void Graph<Data, Weight, CompareHash>::removeEdge(const std::string &K1,
                                                  const std::string &K2) {
  if (!areAdjacent(K1, K2)) return;

  Vertex *v1 = vertices.at(K1);
  Vertex *v2 = vertices.at(K2);

  for (auto it = v1->edges.begin(); it != v1->edges.end(); ++it) {
    if ((*it)->v2 == v2 || (*it)->v1 == v2) {
      std::iter_swap(it, --v1->edges.end());
      break;
    }
  }

  delete v1->edges.back();
  v1->edges.pop_back();
}

template <typename Data, typename Weight, typename CompareHash>
cs225::PNG *Graph<Data, Weight, CompareHash>::draw(bool force) {
  int width = 1920;
  int height = 1080;

  std::vector<std::pair<int, int>> nodes;
  std::vector<std::pair<int, int>> edges;

  std::unordered_map<Vertex *, int> node_idx;
  std::vector<std::pair<double, double>> doubles;
  std::vector<std::pair<double, double>> changes;
  int idx = 0;
  for (const auto &it : vertices) {
    node_idx[it.second] = idx++;
    doubles.push_back(CompareHash::coords(it.second));
    changes.emplace_back(0, 0);
  }

  // Force direction.
  if (force) {
    int iter = 50;
    double area = width * height;
    double k = std::sqrt(area / nodes.size());

    double t = 0.1 * width;
    double dt = t / (iter + 1.0);

    for (int i = 0; i < iter; ++i) {
      for (int j = 0; j < doubles.size(); j++) {
        changes[j].first = 0;
        changes[j].second = 0;

        for (int k = 0; k < doubles.size(); k++) {
          if (j == k) continue;

          double dx = doubles[j].first - doubles[k].first;
          double dy = doubles[j].second - doubles[k].second;
          double dm = std::sqrt(std::pow(dx, 2) + std::pow(dy, 2));

          double fr = std::pow(k, 2) / dm;

          changes[j].first += (dx / dm) * fr;
          changes[j].second += (dy / dm) * fr;
        }
      }

      for (const auto &it : vertices) {
        for (Edge *e : it.second->edges) {
          int j = node_idx[e->v1];
          int k = node_idx[e->v2];

          double dx = doubles[j].first - doubles[k].first;
          double dy = doubles[j].first - doubles[k].second;
          double dm = std::sqrt(std::pow(dx, 2) + std::pow(dy, 2));

          double fa = std::pow(dm, 2) / k;

          changes[j].first -= (dx / dm) * fa;
          changes[j].second -= (dy / dm) * fa;
          changes[k].first += (dx / dm) * fa;
          changes[k].second += (dy / dm) * fa;
        }
      }

      for (int j = 0; j < doubles.size(); j++) {
        auto &change = changes[j];

        double dm =
            std::sqrt(std::pow(change.first, 2) + std::pow(change.second, 2));
        double multiplier = std::min(dm, t);

        change.first *= multiplier / dm;
        change.second *= multiplier / dm;

        if (!std::isnan(change.first) && !std::isnan(change.second)) {
          doubles[j].first += change.first;
          doubles[j].second += change.second;
        }
      }

      t -= dt;
    }
  }

  // Adjusting locations to fit image dimensions.
  double min_lon = doubles.begin()->first;
  double max_lon = doubles.begin()->first;
  double min_lat = doubles.begin()->second;
  double max_lat = doubles.begin()->second;
  for (const auto &it : doubles) {
    if (it.first < min_lon) {
      min_lon = it.first;
    }
    if (it.first > max_lon) {
      max_lon = it.first;
    }
    if (it.second < min_lat) {
      min_lat = it.second;
    }
    if (it.second > max_lat) {
      max_lat = it.second;
    }
  }

  for (auto &it : doubles) {
    it.first -= min_lon;
    it.first /= max_lon - min_lon;
    it.first *= width;

    it.second -= min_lat;
    it.second /= max_lat - min_lat;
    it.second *= height;

    nodes.push_back(std::make_pair(it.first, it.second));
  }

  for (const auto &it : vertices) {
    for (Edge *e : it.second->edges) {
      edges.push_back(std::make_pair(node_idx[e->v1], node_idx[e->v2]));
    }
  }

  Visualizer vis(width, height);
  return vis.draw(nodes, edges);
}

template <typename Data, typename Weight, typename CompareHash>
std::vector<typename Graph<Data, Weight, CompareHash>::Edge *>
Graph<Data, Weight, CompareHash>::findPath(const std::string &_start,
                                           const std::string &_goal,
                                           unsigned zero) {
  Vertex *start = vertices.at(_start);
  Vertex *goal = vertices.at(_goal);

  std::unordered_map<Vertex *, int> g_scores;
  for (const auto &it : vertices)
    g_scores[it.second] = std::numeric_limits<int>::max();

  std::unordered_map<Vertex *, int> f_scores;
  for (const auto &it : vertices)
    f_scores[it.second] = std::numeric_limits<int>::max();

  // Lambda function used as a comparator for vertices.
  auto set_comp = [&f_scores](Vertex *a, Vertex *b) -> bool {
    return f_scores.at(a) > f_scores.at(b);
  };

  std::deque<Vertex *> open_set;
  std::make_heap(open_set.begin(), open_set.end(), set_comp);

  std::unordered_map<Vertex *, bool> os_contains;
  std::unordered_map<Vertex *, Edge *> came_from;

  open_set.push_back(start);
  os_contains[start] = true;
  g_scores[start] = 0;
  f_scores[start] = CompareHash::H(start, goal);
  int i = 0;
  while (!open_set.empty()) {
    Vertex *curr = open_set.front();
    if (curr == goal) return _getEdgePath(curr, came_from);

    std::pop_heap(open_set.begin(), open_set.end());
    open_set.pop_back();
    os_contains[curr] = false;

    for (auto edge : curr->edges) {
      int tentative_g = g_scores[curr] + CompareHash::G(edge, zero);
      auto neighbor = edge->v2;
      if (tentative_g < g_scores[neighbor]) {
        came_from[neighbor] = edge;
        g_scores[neighbor] = tentative_g;
        f_scores[neighbor] = tentative_g + CompareHash::H(neighbor, goal);
        if (!os_contains[neighbor]) {
          open_set.push_back(neighbor);
          std::push_heap(open_set.begin(), open_set.end());
          os_contains[neighbor] = true;
        }
      }
    }
  }

  // Returns empty path if path not found.
  return std::vector<Edge *>();
}

template <typename Data, typename Weight, typename CompareHash>
std::vector<typename Graph<Data, Weight, CompareHash>::Edge *>
Graph<Data, Weight, CompareHash>::_getEdgePath(
    Vertex *curr, std::unordered_map<Vertex *, Edge *> edges) {
  std::vector<Edge *> edgePath;

  while (edges.count(curr) == 1) {
    edgePath.push_back(edges[curr]);
    curr = edges[curr]->v1;
  }

  std::reverse(edgePath.begin(), edgePath.end());
  return edgePath;
}
