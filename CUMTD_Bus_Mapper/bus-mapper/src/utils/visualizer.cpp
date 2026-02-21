#include <cmath>
#include <vector>

#include <utils/visualizer.h>

using cs225::PNG;
using cs225::HSLAPixel;

Visualizer::Visualizer(unsigned width, unsigned height) {
  setup(width, height);
}

Visualizer::~Visualizer() {
  
}

Visualizer::Visualizer(const Visualizer& other) {
  canvas_ = new PNG(*other.canvas_);
}
  
Visualizer& Visualizer::operator=(const Visualizer& other) {
  if (this != &other) {
    delete canvas_;
    setup(other.canvas_->width(), other.canvas_->height());
  }

  return *this;
}

PNG* Visualizer::draw(std::vector<std::pair<int, int>> nodes, std::vector<std::pair<int, int>> edges) {
  for (std::pair<int, int>& edge : edges) {
    std::pair<int, int>& n1 = nodes[edge.first];
    std::pair<int, int>& n2 = nodes[edge.second];

    drawLine(n1.first, n1.second, n2.first, n2.second, kEdgePixel);
  }
  
  for (std::pair<int, int>& node : nodes) {
    drawCircle(node.first, node.second, min_dimension_ * kRadiusMultiplier, kNodePixel);
  }

  return canvas_;
}

void Visualizer::setup(unsigned width, unsigned height) {
  canvas_ = new PNG(width, height);
  min_dimension_ = std::min(canvas_->width(), canvas_->height());
}

void Visualizer::drawLine(int x1, int y1, int x2, int y2, HSLAPixel pixel) {
  if (!isValidPixel(x1, y1)  || !isValidPixel(x2, y2)) return;

  int x_diff = x2 - x1;
  int y_diff = y2 - y1;

  int steps = std::max(std::abs(x_diff), std::abs(y_diff));

  float dx = (float) x_diff / steps;
  float dy = (float) y_diff / steps;

  for (int i = 0; i < steps; i++) {
    drawCircle(x1 + i*dx, y1 + i*dy, min_dimension_ * kThicknessMultiplier, pixel);
  }
}

void Visualizer::drawCircle(int x, int y, int r, HSLAPixel pixel) {
  int r_squared = std::pow(r, 2);

  for (int i = x - r; i < x + r + 1; i++) {
    for (int j = y - r; j < y + r + 1; j++) {
      if (!isValidPixel(i, j)) continue;
      if (std::pow(i - x, 2) + std::pow(j - y, 2) > r_squared) continue;
      
      canvas_->getPixel(i, canvas_->height() - 1 - j) = pixel;
    }
  }
}

bool Visualizer::isValidPixel(int x, int y) {
  return (x >= 0 && x < (int) canvas_->width()) && (y >= 0 && y < (int) canvas_->height());
}