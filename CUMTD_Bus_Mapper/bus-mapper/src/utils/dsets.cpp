#include <utils/dsets.h>

void DisjointSets::addelements(int num) {
  elems_.resize(elems_.size() + num, -1);
}

int DisjointSets::find(int elem) {
  if (elem >= (int)elems_.size()) return -1;
  if (elems_[elem] < 0) return elem;
  elems_[elem] = find(elems_[elem]);
  return elems_[elem];
}

void DisjointSets::setunion(int a, int b) {
  a = find(a);
  b = find(b);
  if (a == b) return;

  if (size(b) <= size(a)) {
    elems_[a] -= size(b);
    elems_[b] = a;
  } else {
    elems_[b] -= size(a);
    elems_[a] = b;
  }
}

int DisjointSets::size(int elem) { return -elems_[find(elem)]; }
