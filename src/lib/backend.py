# This application is released under the GNU General Public License 
# v3 (or, at your option, any later version). You can find the full 
# text of the license under http://www.gnu.org/licenses/gpl.txt. 
# By using, editing and/or distributing this software you agree to 
# the terms and conditions of this license. 
# Thank you for using free software!
#
# screenlets.backend (c) RYX (aka Rico Pfaus) 2007 <ryx@ryxperience.com>
#
# INFO:
# - The backend offers an abstracted way of saving a Screenlet's data
#
# TODO: 
# - add "type"-argument to save_option and read_option to be able to correctly
#   set the values in GconfBackend (instead of storing only strings).
#

import glob
import os
import gobject
import gettext

gettext.textdomain('screenlets')
gettext.bindtextdomain('screenlets', '/usr/share/locale')

def _(s):
	return gettext.gettext(s)


try:
	import gconf
except:
	print "GConf python module not found. GConf settings backend is disabled."


class ScreenletsBackend(object):
	"""The backend performs the loading/saving of the 'key=value'-strings. 
	Extend this superclass to implement different saving-backends."""
	
	def __init__ (self):
		pass
	
	def delete_instance (self, id):
		"""Delete an instance's configuration by its id."""
		pass
	
	def flush (self):
		"""Immediately store all values to disk (in case the backend doesn't
		save in realtime anyway."""
		pass
	
	def load_option (self, id, name):
		"""Load one option for the instance with the given id."""
		pass
	
	def load_instance (self, id):
		"""Load all options for the instance with the given id."""
		pass
	
	def save_option (self, id, name, value):
		"""Save one option for the instance with the given id."""
		pass
	

class GconfBackend (ScreenletsBackend):
	"""Backend for storing settings in the GConf registry"""
	
	gconf_dir = '/apps/screenlets/'
	
	def __init__ (self):
		ScreenletsBackend.__init__(self)
		print 'GConfBackend: initializing'
		self.client = gconf.client_get_default()
	
	def delete_instance (self, id):
		"""Delete an instance's configuration by its id."""
		os.system('gconftool-2 --recursive-unset ' + self.key + id)
		return True
	
	def flush (self):
		"""Immediately store all values to disk (in case the backend doesn't
		save in realtime anyway."""
		pass	#No need, GConf saves in realtime

	def load_option (self, id, name):
		"""Load one option for the instance with the given id."""
		return self.client.get_string(self.gconf_dir + id + '/' + name)
	
	def load_instance (self, id):
		"""Load all options for the instance with the given id."""
		keys = []
		vals = []
		for i in self.client.all_entries(self.gconf_dir + id):
			keys.append(i.key.split('/')[4])
			vals.append(self.client.get_string(i.key))
		return dict(zip(keys, vals))
		return None
	
	def save_option (self, id, name, value):
		"""Save one option for the instance with the given id."""
		self.client.set_string(self.gconf_dir + id + '/' + name, value)
		print 'Saved option %s%s/%s = %s' % (self.gconf_dir, id, name, value)


class CachingBackend (ScreenletsBackend):
	"""A backend that stores the settings in arrays and saves after a short 
	interval to avoid overhead when multiple values are set within a short time. 
	The data gets saved into $HOME/.config/Screenlets/<Screenletname>/, in a 
	file for each element (named like its id with the extension '.ini')."""
	
	# internals
	__instances = {}		# a dict with (id:dict)-entries cntaining the data
	__delay_time = 3000		# delay to wait before performing save
	__timeout = None		# the id of the timeout-function
	__queue = []			# list with ids of instances that need saving
	
	# attribs
	path = ''				# the path to store the files
	
	# Constructor
	def __init__ (self, path):
		ScreenletsBackend.__init__(self)
		self.path = path
		self.__load_cache()
	
	def delete_instance (self, id):
		"""Delete an instance from the list and from the filesystem."""
		if self.__instances.has_key(id):
			del self.__instances[id]
			try:
				import os
				os.remove(self.path + id + '.ini')
			except Exception,ex:
				print ex
				print "Temporary file didn't exist - nothing to remove."
				return False
		print "CachingBackend: <#%s> removed!" % id
		return True
	
	def flush (self):
		"""Immediately save all pending data."""
		self.__save_cache()
	
	def save_option (self, id, name, value):
		"""Save option for an instance to cache and start saving-timeout 
		for that element (value must be of type string)."""
		# create key for option, if not existent yet
		if self.__instances.has_key(id) == False:
			self.__instances[id] = {}
		# set option in array
		self.__instances[id][name] = str(value)
		#print "CachingBackend.save_option: "+name+"="+self.__instances[id][name]
		# if id is not already in queue, add the id to the queue
		if self.__queue.count(id) == 0:
			self.__queue.append(id)
		# reset timeout and start new
		if self.__timeout:
			gobject.source_remove(self.__timeout)
		self.__timeout = gobject.timeout_add(self.__delay_time, 
			self.__save_cache)#, id)
	
	def load_option (self, id, name):
		"""TODO: Load option from the backend (returned as str)."""
		return self.__instances[id][name]
	
	def load_instance (self, id):
		"""Load all options for the instance with the given id."""
		#print "Load element: "+id
		if self.__instances.has_key(id):
			return self.__instances[id]
		return None

	def __load_cache (self):
		"""Load all cached files from path."""
		# perform saving
		print "CachingBackend: Loading instances from cache"
		# get dir content of self.path
		dirname = self.path
		dirlst = glob.glob(dirname + '*')
		tdlen = len(dirname)
		lst = []
		for fname in dirlst:
			dname = fname[tdlen:]
			if dname.endswith('.ini'):
				id = dname[:-4]
				print "CachingBackend: Loading <%s>" % id
				#print "ID: "+id
				if self.__instances.has_key(id) == False:
					self.__instances[id] = {}
				# open file
				try:
					f = open(fname, 'r')
					lines = f.readlines()
					# read all options for this element from file
					for line in lines:
						#print "LOAD: "+line[:-1]
						parts = line[:-1].split('=', 1)
						if len(parts) > 1:
							self.__instances[id][parts[0]] = parts[1]
					f.close()
				except Exception, ex:
					print "Error while loading options: %s" % str(ex)
	
	def __save_cache (self):
		"""Save the cache (for all pending instances in queue) to self.path."""
		# loop through all instances in queue:
		for id in self.__queue:
			# if element with id not exists, remove it and break
			if self.__instances.has_key(id) == False:
				print "Queue-element <%s> not found (already removed?)!" % id
				self.__queue.remove(id)
				break
			# create list with options
			#print "CachingBackend: Saving <#%s> :) ..." % id
			lst = []
			for oname in self.__instances[id]:
				lst.append([oname, self.__instances[id][oname]])
			# and save them (if any)
			if len(lst) > 0:
				self.__save_settings (self.path + id + '.ini', lst)
		# clear queue
		self.__queue = []
		# NOT continue the timeout-function (!!!!!)
		return False

	def __save_settings (self, filename, lst):
		""" Try to save settings in a file, first save this to a temporal file avoid encodings a disk full errors """
		filenametmp = filename + '.tmp'
		isOk = True
		newini = ''
		try:
			# Is posible to fail with encoding error?
			for el in lst:
				newini += "%s=%s\n" % (el[0], el[1])
		except:
			isOk = False
			print "error while convert config to string (encoding error?), I lose your last changes :'("

		if isOk:
			# Write the new settings to a temporal file, disk full, encoding, rights may fails at this point.
			try:
				open(filenametmp, 'w').write(newini)
			except:
				isOk = False
				print "error while saving configuration to a temporal file %s, disk full?" % filenametmp

		if isOk:
			# Move saved settings to definitive configuration file, disk error o incorrect rights may fails at this point.
			try:
				import shutil
				shutil.move(filenametmp, filename)
			except:
				print "error while moving temporal file to configuration file, %s > %s, sorry, I lose your settings. :'(" % (filenametmp, filename)

