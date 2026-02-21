#include <bus/graphing.h>

#include <cstdlib>
#include <iostream>

int main(int argc, char *argv[]) {
  if (argc != 3) {
    std::cout << "Wrong arg count, provide only to and from stations"
              << std::endl;
    return -1;
  }

  std::string const HOME = std::getenv("HOME") ? std::getenv("HOME") : ".";
  std::time_t syst = std::time(0);  // get time now
  std::tm *now = std::localtime(&syst);
  auto g = make_graph(HOME, syst);

  try {
    auto v = g->findPath(argv[1], argv[2], syst);
    if (v.empty()) {
      std::cout << "Path not found" << std::endl;
      delete g;
      return -1;
    }

    char mbstr[100];
    std::strftime(mbstr, sizeof(mbstr), "%c", std::localtime(&syst));
    std::cout << "Finding best trip of the day starting from " << mbstr
              << std::endl;

    std::list<Boarding> boards;
    for (auto e : v) {
      std::time_t t = e->w.getTimeDiff(0);
      std::strftime(mbstr, sizeof(mbstr), "%c", std::localtime(&t));
      if (boards.empty() || e->w.getRoute() != boards.back().route) {
        Boarding b{e->w.getRoute(), mbstr};
        b.stop_names.push_back(e->v1->t.getName());
        boards.push_back(b);
      }
      boards.back().stop_names.push_back(e->v2->t.getName());
    }

    for (const auto &b : boards) {
      std::cout << b.route << ' ' /*<< b.time*/ << " : ";
      for (const auto &stop : b.stop_names) {
        if (stop != b.stop_names.front()) std::cout << " -> ";
        std::cout << stop;
      }
      std::cout << std::endl;
    }
  } catch (const std::out_of_range &e) {
    std::cout << "Invalid station IDs" << std::endl;
    delete g;
    return -1;
  }

  delete g;
  return 0;
}
