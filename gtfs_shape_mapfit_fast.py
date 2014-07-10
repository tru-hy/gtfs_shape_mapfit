import sys
import time

from pymapmatch import osmmapmatch as om
from common import read_gtfs_shapes
import matplotlib.pyplot as plt
import numpy as np

proj = om.CoordinateProjector("+init=epsg:3067")
shape = [s for s in read_gtfs_shapes(sys.stdin)][1][1]
shape = [proj(*c) for c in shape]

x, y = zip(*shape)
plt.plot(x, y, 'o-')

graph = om.OsmGraph(sys.argv[1], proj, om.BUSWAY_FILTER)

def fastlines(segments, *args, **kwargs):
	import matplotlib.pyplot as plt
	invert = kwargs.pop('invert_dims', False)
	x = []
	y = []
	for a, b in segments:
		x.append(a.x)
		x.append(b.x)
		x.append(None)
		y.append(a.y)
		y.append(b.y)
		y.append(None)
	if invert:
		x, y = y, x
	return plt.plot(x, y, *args, **kwargs)

fastlines(graph.get_edge_coordinates(), 'k', alpha=0.3);

model = om.DrawnGaussianStateModel(30.0, 30.0, graph)
matcher = om.MapMatcher2d(graph, model, 100.0)

print "Got map"

points = [om.Point2d(x, y) for x, y in shape]
t = time.time()
#matcher.measurements([0]*len(points), points)
for i, c in enumerate(shape):
	#print >>sys.stderr, i
	matcher.measurement(0, *c)
print (time.time() - t)/len(points)*1000
coords = matcher.best_match_coordinates()
coords = [(c.x, c.y) for c in coords]
plt.plot(*zip(*coords), color='red')
#plt.plot(*zip(*shape))
plt.show()

"""
plt.ion()
line, = plt.plot([], [], color='black')
measurement, = plt.plot([], [], color='red')
ms = []

t = time.time()
for c in shape:
	matcher.measurement(0, *c)
	ms.append(c)
	coords = matcher.best_match_coordinates()
	coords = [(c.x, c.y) for c in coords]

	x, y = zip(*coords[-100:])
	line.set_data(x, y)
	x, y = zip(*ms[-100:])
	measurement.set_data(x, y)
	#plt.cla()
	#plt.gca().set_xlim(np.min(x), np.max(x))
	#plt.gca().set_ylim(np.min(y), np.max(y))
	plt.gca().relim()
	plt.gca().autoscale_view()
	plt.draw()
	#plt.gca().draw_artist(line)
	#plt.gcf().canvas.blit(plt.gca().bbox)
	plt.gcf().canvas.flush_events()
print (time.time()-t)/len(shape)*1000
"""
#coords = matcher.best_match_coordinates()
#coords = [(c.x, c.y) for c in coords]

#x, y = zip(*shape)
#plt.plot(x, y, 'g-')
#x, y = zip(*coords)
#plt.plot(x, y, 'r-')
#plt.show()
