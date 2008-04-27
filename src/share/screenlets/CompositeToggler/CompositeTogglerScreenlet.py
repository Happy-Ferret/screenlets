#!/usr/bin/env python

# This application is released under the GNU General Public License 
# v3 (or, at your option, any later version). You can find the full 
# text of the license under http://www.gnu.org/licenses/gpl.txt. 
# By using, editing and/or distributing this software you agree to 
# the terms and conditions of this license. 
# Thank you for using free software!

#  CompositeTogglerScreenlet (c) Whise 2007 

import screenlets
from screenlets.options import ColorOption
from screenlets import DefaultMenuItem
import pango
import gobject
import random
import gtk
import cairo
import gconf

class CompositeTogglerScreenlet (screenlets.Screenlet):
	"""A Screenlet that allows to instantly change metacity composite state"""
	
	# default meta-info for Screenlets (should be removed and put into metainfo)
	__name__	= 'CompositeTogglerScreenlet'
	__version__	= '0.1'
	__author__	= 'Whise'
	__desc__	= __doc__	# set description to docstring of class
	
	# editable options (options that are editable through the UI)
	frame_color = (1, 1, 1, 1)
	toggle_color = (0, 0, 0, 0.6)
	use_gradient = True
	composite_enabled = True
	# constructor
	def __init__ (self, **keyword_args):
		#call super (width/height MUST match the size of graphics in the theme)
		screenlets.Screenlet.__init__(self, width=100, height=70, 
			uses_theme=True,ask_on_option_override=False, **keyword_args)
		# set theme
		
		#self.theme_name = "default"
		# add option group
		self.add_options_group('Options', 'Options')

		self.add_option(ColorOption('Options','frame_color', 
			self.frame_color, 'Frame color', 
			'Frame color'))
		self.add_option(ColorOption('Options','toggle_color', 
			self.toggle_color, 'Toggle color', 
			'Toggle color'))

		# ADD a 1 second (1000) TIMER

		self.gconf_client = gconf.client_get_default() 
		self.gconf_key = "/apps/metacity/general/compositing_manager" #
		self.gconf_client.notify_add(self.gconf_key, self.update) 
		self.update()

	def update (self):
		self.composite_enabled = bool(self.gconf_client.get_bool(self.gconf_key))
		self.redraw_canvas()
		return True # keep running this event	
	
	# ONLY FOR TESTING!!!!!!!!!
	def init_options_from_metadata (self):
		"""Try to load metadata-file with options. The file has to be named
		like the Screenlet, with the extension ".xml" and needs to be placed
		in the Screenlet's personal directory. 
		NOTE: This function always uses the metadata-file relative to the 
			  Screenlet's location, not the ones in SCREENLETS_PATH!!!"""
		print __file__
		p = __file__.rfind('/')
		mypath = __file__[:p]
		print mypath
		self.add_options_from_file( mypath + '/' + \
			self.__class__.__name__ + '.xml')	


	def on_after_set_atribute(self,name, value):
		"""Called after setting screenlet atributes"""
		
		pass

	def on_before_set_atribute(self,name, value):
		"""Called before setting screenlet atributes"""
		
		pass


	def on_create_drag_icon (self):
		"""Called when the screenlet's drag-icon is created. You can supply
		your own icon and mask by returning them as a 2-tuple."""
		return (None, None)

	def on_composite_changed(self):
		"""Called when composite state has changed"""
		pass

	def on_drag_begin (self, drag_context):
		"""Called when the Screenlet gets dragged."""
		pass
	
	def on_drag_enter (self, drag_context, x, y, timestamp):
		"""Called when something gets dragged into the Screenlets area."""
		pass
	
	def on_drag_leave (self, drag_context, timestamp):
		"""Called when something gets dragged out of the Screenlets area."""
		pass

	def on_drop (self, x, y, sel_data, timestamp):
		"""Called when a selection is dropped on this Screenlet."""
		return False
		
	def on_focus (self, event):
		"""Called when the Screenlet's window receives focus."""
		pass
	
	def on_hide (self):
		"""Called when the Screenlet gets hidden."""
		pass
	
	def on_init (self):
		"""Called when the Screenlet's options have been applied and the 
		screenlet finished its initialization. If you want to have your
		Screenlet do things on startup you should use this handler."""
		
		# add default menu items
		self.add_default_menuitems()


	def on_key_down(self, keycode, keyvalue, event):
		"""Called when a keypress-event occured in Screenlet's window."""

		
		pass
	
	def on_load_theme (self):
		"""Called when the theme is reloaded (after loading, before redraw)."""
		pass
	
	def on_menuitem_select (self, id):
		"""Called when a menuitem is selected."""
		
		pass
	
	def on_mouse_down(self,event):
		x = event.x / self.scale
		y = event.y / self.scale
		
		
		if event.button == 1 and y >= 28 and x >= 72 and x <= 87:
			if y <= 43 and y >= 28:
				print 'setting composite to true'
				self.gconf_client.set_bool(self.gconf_key, True) 
				self.composite_enabled = True
				self.redraw_canvas()
				
			elif y >= 45 and y <60:
				print 'setting composite to false'
				self.gconf_client.set_bool(self.gconf_key, False) 
				self.composite_enabled = False
				self.redraw_canvas()
				
	
	def on_mouse_enter (self, event):
		"""Called when the mouse enters the Screenlet's window."""
		print 'mouse is over me'
		
	def on_mouse_leave (self, event):
		"""Called when the mouse leaves the Screenlet's window."""
		print 'mouse leave'

	def on_mouse_move(self, event):
		"""Called when the mouse moves in the Screenlet's window."""

		pass

	def on_mouse_up (self, event):
		"""Called when a buttonrelease-event occured in Screenlet's window. 
		Returning True causes the event to be not further propagated."""
		return False
	

		
	def on_realize (self):
		""""Callback for handling the realize-event."""
	
	def on_scale (self):
		"""Called when Screenlet.scale is changed."""
		pass
	
	def on_scroll_up (self):
		"""Called when mousewheel is scrolled up (button4)."""
		pass

	def on_scroll_down (self):
		"""Called when mousewheel is scrolled down (button5)."""
		pass
	
	def on_show (self):
		"""Called when the Screenlet gets shown after being hidden."""
		pass
	
	def on_switch_widget_state (self, state):
		"""Called when the Screenlet enters/leaves "Widget"-state."""
		pass
	
	def on_unfocus (self, event):
		"""Called when the Screenlet's window loses focus."""
		pass
	
	def on_draw (self, ctx):
		"""In here we draw"""
		ctx.scale(self.scale,self.scale)
		if self.use_gradient:
			gradient = cairo.LinearGradient(0, self.height*2,0, 0)
			gradient.add_color_stop_rgba(1,*self.frame_color)
			gradient.add_color_stop_rgba(0.7,self.frame_color[0],self.frame_color[1],self.frame_color[2],1-self.frame_color[3]+0.5)

			ctx.set_source(gradient)
		else:
			ctx.set_source(self.frame_color)
		self.draw_rectangle_advanced (ctx, 0, 0, self.width-12, self.height-12, rounded_angles=(5,5,5,5), fill=True, border_size=2, border_color=(0,0,0,0.5), shadow_size=6, shadow_color=(0,0,0,0.5))
		ctx.set_source_rgba(*self.toggle_color)
		self.draw_text(ctx, 'Composite', 0, 10,  'FreeSans', 10, self.width, pango.ALIGN_CENTER)
		self.draw_text(ctx, 'On', 17, 28,  'FreeSans', 10, self.width)
		self.draw_text(ctx, 'Off', 17, 45,  'FreeSans', 10, self.width)
		self.draw_circle (ctx, self.width-28, 28, 14, 12,fill=False)
		if self.composite_enabled:
			self.draw_circle (ctx, self.width-25, 30, 8, 8,fill=True)
		else:
			self.draw_circle (ctx, self.width-25, 47, 8, 8,fill=True)
		self.draw_circle (ctx, self.width-28, 45, 14, 12,fill=False)
				
	def on_draw_shape (self, ctx):
		self.on_draw(ctx)
	
# If the program is run directly or passed as an argument to the python
# interpreter then create a Screenlet instance and show it
if __name__ == "__main__":
	# create new session
	import screenlets.session
	screenlets.session.create_session(CompositeTogglerScreenlet)
