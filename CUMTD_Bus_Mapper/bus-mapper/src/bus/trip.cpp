#include <bus/trip.h>

void from_json(const nlohmann::json &j, Trip &t) {
  t.trip_id_ = j.at("trip_id").get<std::string>();
  t.route_ = j.at("route").get<std::string>();
  t.shape_ = j.at("shape").get<std::string>();
  t.service_ = j.at("service").get<std::vector<t_offset>>();
  t.stops_ = j.at("stops").get<std::vector<Stop>>();
  t.duration_ = j.at("duration").get<t_offset>();
}