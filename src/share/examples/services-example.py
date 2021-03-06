#!/usr/bin/env python

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

# (c) 2007 RYX (aka Rico Pfaus) <ryx@ryxperience.com>
# This is an example of accessing the new ScreenletService. It can be used
# to access signals and methods within a Screenlet from other applications or
# other Screenlets.

# import services-module
import screenlets.services

# check for Clock-service
if not screenlets.services.service_is_running('Clock'):
	print "Clock-service not found. Pleaselaunch the ClockScreenlet first."
else:
	# get general interface for this screenlet
	service_iface = screenlets.services.get_service_by_name('Clock')
	# get interface to the ClockScreenlet's custom service (we need to
	# pass the special interface for the Clock's additonal methods here)
	clock_iface =  screenlets.services.get_service_by_name('Clock', 
		interface='org.screenlets.Clock')
	
	# if interface was returned, 
	if service_iface:
		
		try:
			# get list with instance ids
			ids = service_iface.list_instances()
			for id in ids:
				print id
			
			# id of first instance
			instance_id = ids[0]
			
			# + METHDODS: remote-calling of methods in a Screenlet
			# call testing functions
			service_iface.debug('Hello World!')
			service_iface.test()
			# set options
			#clock.set(instance_id, 'theme_name', 'tango')
			service_iface.set(instance_id, 'x', 700)
			service_iface.set(instance_id, 'y', 500)
			# add a new instance
			service_iface.add('myClock')
			service_iface.set('myClock', 'scale', 3.5)
			service_iface.set('myClock', 'theme_name', 'tango')
			# if clock service is available
			if clock:
				# call special function of the ClockService
				#clock.debug('TEST')
				print clock_iface.get_time(instance_id)
				print clock_iface.get_date(instance_id)
			
			# + SIGNALS: connecting to signals in a screenlet
			def handle_alarm (instance_id):
				print "Signal received: Clock '%s' raised alarm." % (instance_id)
			clock_iface.connect_to_signal('alarm_start', handle_alarm)
			
			# start mainloop (needed to receive events)
			import gobject
			mainloop = gobject.MainLoop()
			mainloop.run()

		except Exception, e:
			print "Error: " + str(e)

