#pragma once
#include <bus/stop.h>
#include <string>
#include <utils/json.hpp>
#include <vector>

typedef int t_offset;

class Trip {
public:
  friend void from_json(const nlohmann::json &j, Trip &t);

private:
  std::string trip_id_;
  std::string route_;
  std::string shape_;
  std::vector<t_offset> service_;
  std::vector<Stop> stops_;
  t_offset duration_;
};