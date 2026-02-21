#include <bus/stop.h>

void from_json(const nlohmann::json &j, Stop &s) {
  s.departure_ = j.at("departure").get<t_offset>();
  s.arrival_ = j.at("arrival").get<t_offset>();
  s.sequence_ = j.at("sequence").get<int>();
  s.platform_id_ = j.at("platform").get<std::string>();
  s.station_ = j.at("station").get<std::string>();
  s.route_ = j.at("route").get<std::string>();
}

t_offset Stop::getTimeDiff(unsigned time) { return departure_ - time; }

std::string const &Stop::getRoute() const { return route_; }