#include <bus/station.h>

void from_json(const nlohmann::json &j, Station &s) {
  s.id_ = j.at("station_id").get<std::string>();
  s.name_ = j.at("name").get<std::string>();
  s.platforms_ = j.at("platforms").get<std::vector<Platform>>();
  s.lat_ = j.at("lat").get<double>();
  s.lon_ = j.at("lon").get<double>();
}

double Station::getLat() const { return lat_; }

double Station::getLon() const { return lon_; }

const std::string &Station::getName() const { return name_; }