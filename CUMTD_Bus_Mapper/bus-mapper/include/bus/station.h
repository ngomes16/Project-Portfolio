#pragma once
#include <bus/platform.h>
#include <string>
#include <utils/json.hpp>
#include <vector>

class Station {
 public:
  friend void from_json(const nlohmann::json &j, Station &s);
  double getLat() const;
  double getLon() const;
  const std::string &getName() const;

 private:
  std::string id_;
  std::string name_;
  std::vector<Platform> platforms_;
  double lat_;
  double lon_;
};

void from_json(const nlohmann::json &j, Station &s);