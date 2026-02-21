#pragma once

#include <vector>

#include <utils/HSLAPixel.h>
#include <utils/PNG.h>

using cs225::PNG;
using cs225::HSLAPixel;

class Visualizer {
public:
  Visualizer(unsigned width, unsigned height);
  Visualizer(const Visualizer& other);
  ~Visualizer();

  Visualizer& operator=(const Visualizer& other);

  PNG* draw(std::vector<std::pair<int, int>> nodes, std::vector<std::pair<int, int>> edges);

private:
  const float kRadiusMultiplier = 0.005;
  const float kThicknessMultiplier = 0.001;
  const HSLAPixel kEdgePixel = HSLAPixel(0, 0, 0, 1);
  const HSLAPixel kNodePixel = HSLAPixel(0, 1, 0.5, 1);

  PNG* canvas_ = NULL;
  int min_dimension_ = 0;

  void reset();
  void setup(unsigned width, unsigned height);

  void drawLine(int x1, int y1, int x2, int y2, HSLAPixel pixel);
  void drawCircle(int x, int y, int r, HSLAPixel pixel);

  bool isValidPixel(int x, int y);
};