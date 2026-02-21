#pragma once
#include <string>
#include <utils/json.hpp>

typedef int t_offset;

class Stop {
 public:
  friend void from_json(const nlohmann::json &j, Stop &s);
  t_offset getTimeDiff(unsigned time);
  std::string const &getRoute() const;

 private:
  t_offset departure_;
  t_offset arrival_;
  int sequence_;
  std::string platform_id_;
  std::string station_;
  std::string route_;
};