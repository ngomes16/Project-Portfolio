import matplotlib.pyplot as plt
import numpy as np

from matplotlib.collections import LineCollection

dpi = 300

width, height = [ int(v) for v in input().split(' ') ]

num_nodes = int(input())
nodes = np.asarray([[float(v) for v in input().split(' ')] for i in range(num_nodes)])
num_edges = int(input())
edges = np.asarray([[nodes[int(v)] for v in input().split(' ')] for i in range(num_edges)], dtype=object)

node_colors = [plt.cm.viridis(c) for c in np.random.rand(num_nodes)]
edge_colors = [plt.cm.viridis(c) for c in np.random.rand(num_edges)]

plt.figure(figsize=(width/dpi, height/dpi), dpi=dpi)
#plt.gca().invert_yaxis()
#plt.gca().invert_xaxis()

plt.gca().add_collection(LineCollection(edges, colors=edge_colors))
plt.scatter(nodes[:,0], nodes[:,1], c=node_colors)

plt.axis('off')
plt.savefig('vis-py.png')