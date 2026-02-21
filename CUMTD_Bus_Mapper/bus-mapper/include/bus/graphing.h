#pragma once
#include <bus/station.h>
#include <bus/stop.h>
#include <graph/graph.h>

struct Functor {
  static int G(Graph<Station, Stop, Functor>::Edge *e, unsigned time);
  static int H(Graph<Station, Stop, Functor>::Vertex *v1,
               Graph<Station, Stop, Functor>::Vertex *v2);
  static std::pair<double, double> coords(
      Graph<Station, Stop, Functor>::Vertex *v);
};

Graph<Station, Stop, Functor> *make_graph(std::string const &root_dir,
                                          unsigned time);

struct Boarding {
  std::string route;
  std::string time;
  std::list<std::string> stop_names;
};