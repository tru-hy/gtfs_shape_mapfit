import sys
import codecs
import csv
from collections import namedtuple
import time
import cPickle

import numpy as np
import pyproj

from pymapmatch import osm2graph, slowmapmatch

# Change this according to your location
coord_proj = pyproj.Proj(init="epsg:3067")

class NamedTupleCsvReader:
	def __init__(self, *args, **kwargs):
		self._reader = iter(csv.reader(*args, **kwargs))
		hdr = self._reader.next()
		self.tupletype = namedtuple('csvtuple', hdr)
	
	def __iter__(self):
		return self
	
	def next(self):
		return self.tupletype(*self._reader.next())


def bomstrip(f):
	c = f.read(3)
	if c != codecs.BOM_UTF8:
		f.seek(-3)
	return f


def read_gtfs_shapes(fileobj):
	shapes = {}
	for row in NamedTupleCsvReader(fileobj):
		if row.shape_id not in shapes:
			shapes[row.shape_id] = []
		shapes[row.shape_id].append((
			int(row.shape_pt_sequence),
			float(row.shape_pt_lat),
			float(row.shape_pt_lon)))
	
	for shape_id, coords in shapes.iteritems():
		# Could use a heap if this causes
		# performance problems (probably wont)
		coords.sort()
		lat, lon = zip(*coords)[1:]
		latlon = zip(lat, lon)
		yield (shape_id, latlon)

def vectangle(a, b):
	cosa = np.dot(a, b)/(np.linalg.norm(a)*np.linalg.norm(b))
	return np.arccos(cosa)

_ad_logpdf = slowmapmatch.gaussian_logpdf(0.1)
_lendiff_logpdf = slowmapmatch.gaussian_logpdf(0.1)
def angle_diff_logpdf(distance, straight_dist, points, path_coords):
	#reldiff = (distance - straight_dist)/straight_dist
	#return _lendiff_logpdf((distance - straight_dist)/straight_dist)
	anglediff = 0.0
	ospan = np.subtract(points[1], points[0])
	spans = np.diff(path_coords, axis=0)

	n = 0
	for span in spans:
		angle = vectangle(ospan, span)
		if np.isnan(angle):
			continue

		anglediff += np.abs(angle)
		n += 1
	
	if n == 0:
		# Give some penalty for staying in
		# the same node to avoid "truncating"
		# of end and startpoints
		anglediff = 0.1
	else:
		anglediff /= float(n)
	return _ad_logpdf(anglediff)


class MapMatcher:
	def __init__(self, edges, nodes, **kwargs):
		self.edges = edges
		edge_costs = dict(osm2graph.euclidean_edge_costs(nodes, edges))
		self.matcher = slowmapmatch.MapMatcher2d(edge_costs, nodes,
			transition_logpdf=angle_diff_logpdf,
			measurement_logpdf=slowmapmatch.gaussian_logpdf(5),
			**kwargs)
		self.nodes = nodes
		self.edge_costs = edge_costs
	
	def __call__(self, cart):
		cart = np.array(cart)
		distances = [np.linalg.norm(cart[i] - cart[i+1]) for i in range(len(cart)-1)]
		distances = [0.0] + distances
		distances = np.cumsum(distances)
		match = self.matcher(distances, cart)
		return match
		positions = match.get_map_coordinates()
		#positions = match.get_state_coordinates()
		return positions

def get_matcher(mapfile, **kwargs):
	raw_nodes, edges, tags = osm2graph.get_graph(mapfile)
	nodes = {}
	for key, coords in raw_nodes.iteritems():
		cart = coord_proj(*coords)
		nodes[key] = cart
	
	
	matcher = MapMatcher(edges, nodes, **kwargs)
	return matcher

def fit_shape(matcher, coords):
	cart = np.array(coord_proj(*zip(*coords)[::-1])).T
	match = matcher(cart)
	return match
	#fit = np.array(match.get_map_coordinates())
	#osm2graph.plot_graph(matcher.nodes, matcher.edges, color='black', alpha=0.5)
	#plt.plot(*cart.T)
	#plt.plot(*fit.T)
	#plt.show()

def process(mapfile, whitelist="", badpoints="", search_radius=50.0):
	
	if whitelist != "":
		whitelist = whitelist.split(',')
		do_include = lambda x: x in whitelist
	else:
		do_include = lambda x: True
	
	if badpoints != "":
		badpoints = map(float, badpoints.split(','))
		badpoints = zip(badpoints, badpoints[1:])
		def point_filter(points):
			good = []
			for p in points:
				pp = coord_proj(*p[::-1])
				for bp in badpoints:
					dist = np.linalg.norm(np.subtract(bp, pp))
					if np.linalg.norm(np.subtract(bp, pp)) < 3:
						break
				else:
					good.append(p)
			return good
	else:
		point_filter = lambda x: x
	
	print >>sys.stderr, "Loading matcher"
	matcher = get_matcher(mapfile, search_radius=search_radius)
	
	shapes = [s for s in read_gtfs_shapes(bomstrip(sys.stdin)) if do_include(s[0])]
	n = len(shapes)
	times = []
	for i, (shape_id, coords) in enumerate(shapes):
		t = time.time()
		print >>sys.stderr, "Processing %i/%i"%(i+1, n)
		coords = point_filter(coords)
		match = fit_shape(matcher, coords)
		fit = match.get_map_coordinates()
		states = match.get_winner_state_path()
		cPickle.dump((shape_id, coords, fit, states), sys.stdout, -1)
		sys.stdout.flush()
		t = time.time() - t
		times.append(t)
		print >>sys.stderr, "Took %fs (avg %fs, approx %fm left)"%(
			t, np.mean(times), (np.mean(times)*(n-(i+1)))/60.0 )

def export():
	fits = {}
	while True:
		try:
			fit = cPickle.load(sys.stdin)
			fits[fit[0]] = fit
		except EOFError:
			break
	
	print "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence"
	for (shape_id, coords, fit, states) in fits.itervalues():
		lonlat = zip(*coord_proj(*zip(*fit), inverse=True))
		for i, (lon, lat) in enumerate(lonlat):
			print ",".join(map(str, (shape_id, lat, lon, i+1)))
			

def view(mapfile, whitelist=""):
	import matplotlib.pyplot as plt
	
	if whitelist != "":
		whitelist = whitelist.split(',')
		do_include = lambda x: x in whitelist
	else:
		do_include = lambda x: True
	
	fits = {}
	while True:
		try:
			fit = cPickle.load(sys.stdin)
			if not do_include(fit[0]): continue
			fits[fit[0]] = fit
		except EOFError:
			break
	
	raw_nodes, edges, tags = osm2graph.get_graph(mapfile)
	nodes = {}
	for key, coords in raw_nodes.iteritems():
		cart = coord_proj(*coords)
		nodes[key] = cart

	
	stats = []
	for fitstuff in fits.itervalues():
		(shape_id, coords, fit, states) = fitstuff
		cart = np.array(coord_proj(*zip(*coords)[::-1])).T
		
		assert len(states) == len(coords)
		
		points = []
		diffs = []
		for i in range(1, len(states)):
			mapcoords = [states[i-1].point]
			mapcoords.extend([nodes[n] for n in states[i].path])
			mapcoords.append(states[i].point)
			points.extend(mapcoords)
			diffs.extend([slowmapmatch.lineseg_point_projection(p, cart[i-1], cart[i])[1] for p in mapcoords])
		stats.append((np.max(diffs), diffs, points, fitstuff))
	
	stats.sort(key=lambda s: -s[0])
	for (maxdiff, diffs, points, fitstuff) in stats:
		(shape_id, coords, fit, states) = fitstuff
		cart = np.array(coord_proj(*zip(*coords)[::-1])).T
		print "%s,%f"%(shape_id,maxdiff)
		plt.title("%s max diff %fm"%(shape_id, maxdiff))
		osm2graph.plot_graph(nodes, edges, color='black', alpha=0.5)
		plt.plot(*cart.T, linewidth=2, alpha=0.5)
		plt.plot(*np.array(fit).T, linewidth=2, alpha=0.5)
		x, y = zip(*points)
		plt.scatter(x, y, c=diffs, lw=0)
		plt.show()


if __name__ == '__main__':
	import argh
	parser = argh.ArghParser()
	parser.add_commands([process, view, export])
	parser.dispatch()

