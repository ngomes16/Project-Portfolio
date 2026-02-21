#pragma once
#include <list>

/*
 *  Iterator methods
 */
template <typename Data, typename Weight, typename CompareHash>
Graph<Data, Weight, CompareHash>::iterator::iterator() : v_(nullptr) {}

template <typename Data, typename Weight, typename CompareHash>
Graph<Data, Weight, CompareHash>::iterator::iterator(std::queue<Vertex *> n)
    : v_(n.front()), never_v2s_(n) {
  // enqueue as root
  work_queue_.push(never_v2s_.front());
  never_v2s_.pop();
}

template <typename Data, typename Weight, typename CompareHash>
Data &Graph<Data, Weight, CompareHash>::iterator::operator*() {
  return v_->t;
}

template <typename Data, typename Weight, typename CompareHash>
Data *Graph<Data, Weight, CompareHash>::iterator::operator->() {
  return &(v_->t);
}

template <typename Data, typename Weight, typename CompareHash>
typename Graph<Data, Weight, CompareHash>::iterator &
Graph<Data, Weight, CompareHash>::iterator::operator++() {
  operator++(0);
  return *this;
}  // prefix increment

template <typename Data, typename Weight, typename CompareHash>
typename Graph<Data, Weight, CompareHash>::iterator
Graph<Data, Weight, CompareHash>::iterator::operator++(int) {
  // enqueue the children of queue front
  // 1. take vertex in front of queue
  // 2. for each of the edges in its edge list, enqueue the v2 of the edge
  iterator it = iterator(*this);

  for (Edge *e : work_queue_.front()->edges) {
    work_queue_.push(e->v2);
  }

  been_visited_.insert(work_queue_.front());
  while (!work_queue_.empty() &&
         been_visited_.find(work_queue_.front()) != been_visited_.end()) {
    work_queue_.pop();
  }

  if (work_queue_.empty()) {
    if (never_v2s_.empty()) {
      v_ = nullptr;
    } else {
      work_queue_.push(never_v2s_.front());
      never_v2s_.pop();
      v_ = work_queue_.front();
    }
  } else {
    v_ = work_queue_.front();
  }

  return it;
}  // postfix increment

template <typename Data, typename Weight, typename CompareHash>
bool Graph<Data, Weight, CompareHash>::iterator::operator==(
    const iterator &other) const {
  return !(*this != other);
}

template <typename Data, typename Weight, typename CompareHash>
bool Graph<Data, Weight, CompareHash>::iterator::operator!=(
    const iterator &other) const {
  return v_ != other.v_;
}

template <typename Data, typename Weight, typename CompareHash>
typename Graph<Data, Weight, CompareHash>::iterator
Graph<Data, Weight, CompareHash>::begin() const {
  if (vertices.empty()) return end();
  // figure out never v2s.
  std::queue<Vertex *> q;
  for (const auto &it : never_v2_) {
    if (it.second) {
      q.push(it.first);
    }
  }
  if (q.empty()) q.push(vertices.begin()->second);
  return iterator(q);
}

template <typename Data, typename Weight, typename CompareHash>
typename Graph<Data, Weight, CompareHash>::iterator
Graph<Data, Weight, CompareHash>::end() const {
  return iterator();
}
