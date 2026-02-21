#include <bus/platform.h>

void from_json(const nlohmann::json &j, Platform &p) {
  p.platform_id_ = j.at("platform_id").get<std::string>();
  p.name_ = j.at("name").get<std::string>();
  p.station_ = j.at("station").get<std::string>();
  
}

void to_json(nlohmann::json &j, const Platform &p) {
  j["platform_id"] = p.platform_id_;
  j["name"] = p.name_;
  j["station"] = p.station_;
}
