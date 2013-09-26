#!/usr/bin/env python2

import cherrypy as cp
import sys
import os
import cgi
import subprocess
import errno

index_template = """
<h1>GTFS mapfit server</h1>
<fieldset>
<legend>New fit</legend>
<form method="post" enctype="multipart/form-data" action="new_fit">
<label for="session_name">Session name</label>
<input type="text" name="session_name" />
<br />
<label for="shapefile">Shape file to match</label>
<input type="file" name="shapefile" />
<br />
<input type="submit" />
</form>
</fieldset>

<fieldset>
<legend>Old fits</legend>
%(session_list)s
</fieldset>
"""

SESDIR_PREFIX = 'fitses_'

session_template = """
<h1>Fitting session %(name)s</h1>
<div>
Result: %(result)s
</div>

<fieldset>
<legend>Log output</legend>
<pre>
%(log)s
</pre>
</fieldset>
"""

def is_running(pid):
	try:
		os.kill(pid, 0)
		return True
	except:
		return False

class FitSession(object):
	def __init__(self, name, directory, mapfile, shapefile=None):
		self.name = name
		self.directory = directory
		try:
			os.mkdir(directory)
		except OSError, e:
			if e.errno != errno.EEXIST:
				raise
		
		if shapefile is not None:
			with open(os.path.join(self.directory, 'shapes.txt.in'), 'w') as outf:
				outf.write(shapefile.read())

		self.mapfile = mapfile
	
	def getpid(self):
		try:
			return int(open(os.path.join(self.directory, "pid")).read())
		except IOError:
			return None
	
	def getlog(self):
		try:
			return open(os.path.join(self.directory, "log")).read()
		except IOError, e:
			return ""
	
	def is_ready(self):
		readyfile = os.path.join(self.directory, 'ready')
		try:
			open(readyfile)
			return True
		except IOError, e:
			return False

	
	def getresult(self):
		try:
			return open(os.path.join(self.directory, "shapes.txt.out")).read()
		except IOError:
			return ""
	
	def run(self):
		pid = self.getpid()
		if pid is not None:
			return

		infile = os.path.join(self.directory, 'shapes.txt.in')
		outfile = os.path.join(self.directory, 'shapes.txt.out')
		logfile = os.path.join(self.directory, "log")
		readyfile = os.path.join(self.directory, 'ready')
		with open(os.path.join(self.directory, 'pid'), 'w') as pidfile:
			cmd = './process.sh "%s" < "%s" > "%s" 2> %s; touch %s'%(self.mapfile, infile, outfile, logfile, readyfile)
			process = subprocess.Popen(cmd, shell=True)
			pidfile.write(str(process.pid))


	@cp.expose
	def index(self):
		self.run()
		is_ready = self.is_ready()
		if not is_ready:
			result = "[Not ready]"
		else:
			result = '<a href="shapes.txt">shapes.txt</a>'

		content = session_template%dict(
			name=self.name,
			result=result,
			log=cgi.escape(self.getlog())
			)
		
		return content
	
	@cp.expose
	def shapes_txt(self):
		cp.response.headers['Content-Type']= 'text/plain'	
		with open(os.path.join(self.directory, 'shapes.txt.out')) as outfile:
			return outfile.read()

class MapfitServer(object):
	def __init__(self, working_dir, mapfile):
		self.working_dir = working_dir
		self.mapfile = mapfile

		for name in self.sessions:
			self.add_session(name)
	
	@property
	def sessions(self):
		sessions = []
		for f in os.listdir(self.working_dir):
			if not f.startswith(SESDIR_PREFIX):
				continue
			name = f[len(SESDIR_PREFIX):]
			sessions.append(name)

		return sessions

	
	def add_session(self, name, shapefile=None):
		f = SESDIR_PREFIX + name
		sdir = os.path.join(self.working_dir, f)
		session = FitSession(name, sdir, self.mapfile, shapefile)
		setattr(self, name, session)
		

	@cp.expose
	def index(self):
		session_list = "<ul>"
		for session in self.sessions:
			session_list += '<li><a href="%s/">%s</li>'%(session, session)
		session_list += "</ul>"
		content = index_template%dict(session_list=session_list)
			
		return content
	
	@cp.expose
	def new_fit(self, session_name, shapefile):
		if not session_name.isalnum():
			return "<h1>Session name can have only letters and numbers</h1>"
		if not session_name:
			return "<h1>Session name can't be empty</h1>"
		if hasattr(self, session_name):
			return "<h1>Session %s already exists</h1>"%session_name
		
		self.add_session(session_name, shapefile.file)
		raise cp.HTTPRedirect("%s/"%session_name)

def run_server(working_dir, mapfile, host="0.0.0.0", port=8080):
	cpconfig = {
                'server.socket_host': host,
                'server.socket_port': port,
		}
	cp.quickstart(MapfitServer(working_dir, mapfile),
		config={'global': cpconfig})

if __name__ == '__main__':
	import argh
	argh.dispatch_command(run_server)
