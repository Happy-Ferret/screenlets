# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# A Generic API to a Music Player by vrunner
# All Players must extend this class

class GenericAPI(object):
	__name__ = 'GenericAPI'
	__version__ = '0.0'
	__author__ = 'vrunner'
	__desc__ = 'A Generic API to a Music Player. All Players must extend this'

	session_bus = False


	def __init__(self, session_bus):
		self.session_bus = session_bus
	
	# Check if the player is active : Returns Boolean
	# A handle to the dbus interface is passed in : doesn't need to be used
	# if there are other ways of checking this (like dcop in amarok)
	def is_active(self, dbus_iface):
		pass

	# Make a connection to the Player
	def connect(self):
		pass
	
	# The following return Strings
	def get_title(self):
		pass
	
	def get_album(self):
		pass

	def get_artist(self):
		pass

	def get_cover_path(self):
		pass

	# Returns Boolean
	def is_playing(self):
		pass

	# The following do not return any values
	def play_pause(self):
		pass

	def next(self):
		pass

	def previous(self):
		pass

	# The following calls the passed Callback function when one of the following event occurs:
	# - Song Change, Play/Pause, Info Change
	# If no dbus api to support it, then just do call the callback fn every few seconds
	def register_change_callback(self, fn):
		pass
	
	# I haven't put in functions yet for volume control, and track control
