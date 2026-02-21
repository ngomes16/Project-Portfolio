#include <bus/graphing.h>

#include <cstdlib>
#include <ctime>
#include <fstream>
#include <unordered_map>
#include <unordered_set>
#include <vector>

int Functor::G(Graph<Station, Stop, Functor>::Edge *e, unsigned time) {
  return e->w.getTimeDiff(time);
}

int Functor::H(Graph<Station, Stop, Functor>::Vertex *v1,
               Graph<Station, Stop, Functor>::Vertex *v2) {
  auto c1 = coords(v1);
  auto c2 = coords(v2);
  return 100 * 3958.8 *
         acos(cos(c1.second) * cos(c2.second) * cos(c1.first - c2.first) +
              sin(c1.second) * sin(c2.second));
}

std::pair<double, double> Functor::coords(
    Graph<Station, Stop, Functor>::Vertex *v) {
  return std::make_pair(v->t.getLon(), v->t.getLat());
}

Graph<Station, Stop, Functor> *make_graph(std::string const &root_dir,
                                          unsigned time) {
  nlohmann::json j;
  std::ifstream f;
  std::time_t t = time;
  std::tm *now = localtime(&t);

  f.open(root_dir + "/sfpa/jtfs/jtfs_platforms.json");
  f >> j;
  f.close();

  std::unordered_map<std::string, Platform> platforms;
  for (const nlohmann::json &platform : j) {
    platforms.emplace(platform.at("platform_id").get<std::string>(), platform);
  }

  f.open(root_dir + "/sfpa/jtfs/jtfs_stations.json");
  f >> j;
  f.close();

  auto g = new Graph<Station, Stop, Functor>();

  for (nlohmann::json &station : j) {
    nlohmann::json real_platforms;
    for (const std::string &platform_id : station.at("platforms")) {
      real_platforms.push_back(platforms[platform_id]);
    }
    station["platforms"] = real_platforms;
    g->insertVertex(station["station_id"], station);
  }

  f.open(root_dir + "/sfpa/jtfs/jtfs_trips.json");
  f >> j;
  f.close();

  std::unordered_set<std::string> check;

  for (const nlohmann::json &trip : j) {
    for (int service : trip["services"]) {
      std::time_t end =
          service + trip["stops"].back()["arrival_offset"].get<int>();
      std::tm *res = localtime(&end);
      if (res->tm_wday != now->tm_wday) continue;
      if (res->tm_hour < now->tm_hour) continue;
      if (res->tm_min < now->tm_min) continue;
      if (res->tm_sec < now->tm_sec) continue;
      for (unsigned i = 0; i + 1 < trip["stops"].size(); i++) {
        nlohmann::json stop = trip["stops"][i + 1];
        stop["departure"] = stop["departure_offset"].get<int>() + time;
        stop["arrival"] = stop["departure_offset"].get<int>() + time;
        stop["route"] = trip["route"];
        g->insertEdge(trip["stops"][i]["station"],
                      trip["stops"][i + 1]["station"], stop);
      }
      break;
    }
  }

  return g;
}