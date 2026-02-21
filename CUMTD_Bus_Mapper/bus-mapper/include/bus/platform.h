#pragma once
#include <string>
#include <utils/json.hpp>

class Platform {
public:
  friend void from_json(const nlohmann::json &j, Platform &p);
  friend void to_json(nlohmann::json &j, const Platform &p);

private:
  std::string platform_id_;
  std::string name_;
  std::string station_;
};

void from_json(const nlohmann::json &j, Platform &p);
void to_json(nlohmann::json &j, const Platform &p);