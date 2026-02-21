#include <bus/graphing.h>

#include <cstdlib>
#include <iostream>

int main(int argc, char *argv[]) {
  if (argc != 2 && argc != 3) {
    std::cout << "Wrong arg count, specify output file path and (optionally) "
                 "force direction [-f]"
              << std::endl;
    return -1;
  }

  std::string const HOME = std::getenv("HOME") ? std::getenv("HOME") : ".";
  std::time_t t = std::time(0);  // get time now
  std::tm *now = std::localtime(&t);
  auto g = make_graph(HOME, t);
  auto p = g->draw(argc == 3 && std::string(argv[2]) == "-f");
  p->writeToFile(argv[1]);
  delete p;
  delete g;
  return 0;
}
