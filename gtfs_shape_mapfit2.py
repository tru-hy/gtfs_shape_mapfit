#!/usr/bin/python2
import os
import sys
import time
import datetime

import pymapmatch.osmmapmatch as omm
from common import read_gtfs_shapes, read_gtfs_routes, read_gtfs_shape_trips
from collections import defaultdict
import itertools

class ShapeError(Exception): pass

ROUTE_TYPE_FILTERS = {
	'0': "TRAM_FILTER",
	'1': "SUBWAY_FILTER",
	'3': "BUSWAY_FILTER",
	'2': "TRAIN_FILTER",
	'109': "TRAIN_FILTER", # Non-standard type for Helsinki's data
}

def write_gtfs_shape(shape_id, coords, out):
	for i, c in enumerate(coords, 1):
		out.write("%s,%f,%f,%i\n"%(
			shape_id, c[0], c[1], i))

from threading import Lock, RLock, Thread
from Queue import Queue
stderr_lock = Lock()
def stderr(*args):
	with stderr_lock:
		print >>sys.stderr, ' '.join(args)

def threadimap(func, itr):
	return itertools.imap(func, itr)
	"""
	results = Queue()
	itr = iter(itr)
	def runit(value):
		results.put(func(value))

	n_workers = 4
	n_running = 0
	for n_running, value in enumerate(itertools.islice(itr, n_workers), start=1):
		Thread(target=runit, args=(value,)).start()

	for value in itr:
		yield results.get()
		Thread(target=runit, args=(value,)).start()
	
	for i in range(n_running):
		yield results.get()
	"""

def gtfs_shape_mapfit(map_file, projection, gtfs_directory, search_region=100.0):
	def gfile(fname):
		return open(os.path.join(gtfs_directory, fname))
	routes = read_gtfs_routes(gfile('routes.txt'))
	shapes = read_gtfs_shapes(gfile('shapes.txt'))
	shape_trips = read_gtfs_shape_trips(gfile('trips.txt'))
	def shape_route_type(shape_id):
		route_ids = set(t.route_id for t in shape_trips[shape_id])
		if not route_ids:
			return None
		types = set(routes[r_id].route_type for r_id in route_ids)
		if len(types) != 1:
			raise ShapeError("Multiple route types for shape %s!"%(shape_id))
		return types.pop()
	
	projection = omm.CoordinateProjector(projection)
	
	def sync(method):
		def synced(self, *args, **kwargs):
			with self.lock:
				stuff = method(self, *args, **kwargs)
			return stuff
		return synced

	class Graphs(defaultdict):
		def __init__(self):
			self.lock = RLock()
		
		__getitem__ = sync(defaultdict.__getitem__)
		__setitem__ = sync(defaultdict.__setitem__)
		__contains__ = sync(defaultdict.__contains__)

		def __missing__(self, type_filter):
			if type_filter is None:
				#print >>sys.stderr, "No map filter for route type %s"%route_type
				self[type_filter] = None
				return None
			filt = getattr(omm, type_filter)
			stderr("Loading graph for %s"%type_filter)
			graph = omm.OsmGraph(map_file, projection, filt)
			self[type_filter] = graph
			return graph
	graphs = Graphs()
	
	from multiprocessing.pool import ThreadPool
	def do_fit(shape):
		shape_id, shape_coords = shape
		route_type = shape_route_type(shape_id)
		type_filter = ROUTE_TYPE_FILTERS.get(route_type)
		graph = graphs[type_filter]
		if graph is None:
			#write_gtfs_shape(shape_id, shape_coords, sys.stdout)
			return shape_id, shape_coords

		state_model = omm.DrawnGaussianStateModel(30, 30, graph)
		matcher = omm.MapMatcher2d(graph, state_model, search_region)
		
		coords = [projection(*c) for c in shape_coords]
		points = [omm.Point2d(*c) for c in coords]
		times = [0.0]*len(points)
		matcher.measurements(times, points)
		#for c in coords:
		#	matcher.measurement(0, *c)
		fitted_coords = [(p.x, p.y) for p in matcher.best_match_coordinates()]
		fitted = [projection.inverse(*c) for c in fitted_coords]
		
		#import matplotlib.pyplot as plt
		#plt.cla()
		#plt.plot(*zip(*fitted))
		#plt.plot(*zip(*shape_coords))
		#import geojsonio
		#import webbrowser
		#open('/tmp/shapes/%s.geojson'%(shape_id,), 'w').write(
		#	dump_geojson(shape_id, fitted, shape_coords))
			#url = geojsonio.geojsonio_url(dump_geojson(shape_id, fitted, shape_coords), force_gist=True)
			#webbrowser.open(url)
		#write_gtfs_shape(shape_id, fitted, sys.stdout)
		return shape_id, fitted
	
	shapes = list(shapes)
	
	start_time = time.time()
	#workers = ThreadPool(4)
	#results = workers.imap_unordered(do_fit, shapes)
	#import itertools
	#results = itertools.imap(do_fit, shapes)
	results = threadimap(do_fit, shapes)
	for i, (shape_id, shape_coords) in enumerate(results):
		write_gtfs_shape(shape_id, shape_coords, sys.stdout)
		time_spent = time.time() - start_time
		mean_time = time_spent/float(i+1)
		time_left = mean_time*(len(shapes)-i)
		stderr("Shape %i/%i done, approx %s left"%(i+1, len(shapes), datetime.timedelta(seconds=time_left)))
		#plt.show()

	#plt.show()

def dump_geojson(shape_id, fitted, orig):
	import json
	output = dict(type="FeatureCollection")
	features = output['features'] = []
	geom = dict(type="LineString", coordinates=[c[::-1] for c in orig])
	feature = dict(
		type="Feature",
		geometry=geom,
		properties={"name":shape_id+" orig", "stroke":'red', "stroke-width": 4})
	features.append(feature)
	
	geom = dict(type="LineString", coordinates=[c[::-1] for c in fitted])
	feature = dict(
		type="Feature",
		geometry=geom,
		properties=dict(name=shape_id, stroke='green'))
	features.append(feature)
	
	return json.dumps(output)



if __name__ == '__main__':
	import argh
	argh.dispatch_command(gtfs_shape_mapfit)
