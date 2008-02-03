#!/usr/bin/env python

# This application is released under the GNU General Public License 
# v3 (or, at your option, any later version). You can find the full 
# text of the license under http://www.gnu.org/licenses/gpl.txt. 
# By using, editing and/or distributing this software you agree to 
# the terms and conditions of this license. 
# Thank you for using free software!

# Screenlets main module (c) RYX (aka Rico Pfaus) 2007 <ryx@ryxperience.com>
#
##@mainpage
#
##@section intro_sec General Information
#
# INFO:
# - Screenlets are small owner-drawn applications that can be described as
#  " the virtual representation of things lying/standing around on your desk".
#   Sticknotes, clocks, rulers, ... the possibilities are endless. The goal of 
#   the Screenlets is to simplify the creation of fully themeable mini-apps that
#   each solve basic desktop-work-related needs and generally improve the 
#   usability and eye-candy of the modern Linux-desktop.
#
# TODO: (possible improvements, not essential)
# - still more error-handling and maybe custom exceptions!!!
# - improve xml-based menu (is implemented, but I'm not happy with it)
# - switching themes slowly increases the memory usage (possible leak)
# - maybe attributes for dependancies/requirements (e.g. special 
#   python-libs or certain Screenlets)
# -
#

import pygtk
pygtk.require('2.0')
import gtk
import cairo, pango
import gobject
import rsvg
import os
import glob
import gettext
import math

# import screenlet-submodules
from options import *
import services
import utils

# TEST
import XmlMenu
# /TEST


#-------------------------------------------------------------------------------
# CONSTANTS
#-------------------------------------------------------------------------------

# the application name
APP_NAME = "Screenlets"

# the version of the Screenlets-baseclass in use
VERSION = "0.0.12"

# the application copyright
COPYRIGHT = "(c) RYX (Rico Pfaus) <ryx@ryxperience.com>"

# the application authors
AUTHORS = ["RYX (Rico Pfaus) <ryx@ryxperience.com>", "Whise (Helder Fraga)<helder.fraga@hotmail.com>","Hendrik Kaju (sorcerer)"]

# the application comments
COMMENTS = "Screenlets are small owner-drawn applications (written in Python, a very simple object-oriented programming-language) that can be described as 'the virtual representation of things lying/standing around on your desk'. Sticknotes, clocks, rulers, ... the possibilities are endless."

# the application website
WEBSITE = 'http://www.screenlets.org'

# the third party screenlets download site
THIRD_PARTY_DOWNLOAD = "http://screenlets.org/index.php/Category:UserScreenlets"

# install prefix (/usr or /usr/local) DO NOT CHANGE YET, WILL CHANGE WITH v0.1.0
INSTALL_PREFIX = '/usr'

# the global PATH where the screenlets are installed 
PATH = INSTALL_PREFIX + '/share/screenlets'

# A list containing all the paths to search for screenlet-"packages"
# (these paths get searched when a new screenlet-instance shall be
# loaded through the module-loader function or a screenlet needs data
# from its personal dir)
SCREENLETS_PATH = [os.environ['HOME'] + '/.screenlets', PATH]

# translation stuff
gettext.textdomain('screenlets')
gettext.bindtextdomain('screenlets', '/usr/share/locale')

def _(s):
	return gettext.gettext(s)


#-------------------------------------------------------------------------------
# CLASSES
#-------------------------------------------------------------------------------

class DefaultMenuItem:
	"""A container with constants for the default menuitems"""
	
	# default menuitem constants (is it right to increase like this?)
	NONE		= 0
	DELETE		= 1
	THEMES		= 2
	INFO		= 4
	SIZE		= 8
	WINDOW_MENU	= 16
	PROPERTIES	= 32
	# EXPERIMENTAL!! If you use this, the file menu.xml in the 
	# Screenlet's data-dir is used for generating the menu ...
	XML			= 512
	# the default items
	STANDARD	= 1|2|8|16|32


class ScreenletTheme (dict):
	"""ScreenletThemes are simple storages that allow loading files
	as svg-handles within a theme-directory. Each Screenlet can have 
	its own theme-directory. It is up to the Screenlet-developer if he
	wants to let his Screenlet support themes or not. Themes are 
	turned off by default - if your Screenlet uses Themes, just set the 
	attribute 'theme_name' to the name of the theme's dir you want to use.
	TODO: remove dict-inheritance"""
	
	# meta-info (set through theme.conf)
	__name__	= ''
	__author__	= ''
	__version__	= ''
	__info__	= ''
	
	# attributes
	path		= ""
	loaded		= False
	width		= 0
	height		= 0
	option_overrides = {}
	p_fdesc = None
	p_layout = None
	tooltip = None
	notify = None

	def __init__ (self, path):
		# set theme-path and load all files in path
		self.path = path
		self.svgs = {}
		self.pngs = {}	
		self.option_overrides = {}
		self.loaded = self.__load_all()
		if self.loaded == False:
			raise Exception(_("Error while loading ScreenletTheme in: ") + path)
	
	def __getattr__ (self, name):
		if name in ("width", "height"):
			if self.loaded and len(self)>0:
				size=self[0].get_dimension_data()
				if name=="width":
					return size[0]
				else:
					return size[1]
		else:
			return object.__getattr__(self, name)
	
	def apply_option_overrides (self, screenlet):
		"""Apply this theme's overridden options to the given Screenlet."""
		# disable the canvas-updates in the screenlet
		screenlet.disable_updates = True
		# theme_name needs special care (must be applied last)
		theme_name = ''
		# loop through overrides and appply them
		for name in self.option_overrides:
			print _("Override: ") + name
			o = screenlet.get_option_by_name(name)
			if o and not o.protected:
				if name == 'theme_name':
					# import/remember theme-name, but not apply yet
					theme_name = o.on_import(self.option_overrides[name])
				else:
					# set option in screenlet
					setattr(screenlet, name, 
						o.on_import(self.option_overrides[name]))
			else:
				print _("WARNING: Option '%s' not found or protected.") % name
		# now apply theme
		if theme_name != '':
			screenlet.theme_name = theme_name
		# re-enable updates and call redraw/reshape
		screenlet.disable_updates = False
		screenlet.redraw_canvas()
		screenlet.update_shape()
		
	def check_entry (self, filename):
		"""Checks if a file with filename is loaded in this theme."""
		try:
			if self[filename]:
				return True
		except:
			#raise Exception
			return False

	def draw_text(self, ctx, text, x, y,  font, size, width, allignment):
		"""Draws text"""
		ctx.save()
		ctx.translate(x, y)
		if self.p_layout == None :
	
			self.p_layout = ctx.create_layout()
		else:
			
			ctx.update_layout(self.p_layout)
		self.p_fdesc = pango.FontDescription()
		self.p_fdesc.set_family_static(font)
		self.p_fdesc.set_size(size * pango.SCALE)
		self.p_layout.set_font_description(self.p_fdesc)
		self.p_layout.set_width(width * pango.SCALE)
		self.p_layout.set_alignment(allignment)
		self.p_layout.set_markup(text)
		ctx.show_layout(self.p_layout)
		ctx.restore()


	def draw_circle(self,ctx,x,y,width,height,fill=True):
		"""Draws a circule"""
		ctx.save()
		ctx.translate(x, y)
       		ctx.arc(width/2,height/2,min(height,width)/2,0,2*math.pi)
		if fill:ctx.fill()
		else: ctx.stroke()
		ctx.restore()

	def draw_line(self,ctx,start_x,start_y,end_x,end_y,line_width = 1,close=False,preserve=False):
		"""Draws a line"""
		ctx.save()
		ctx.move_to(start_x, start_y)
		ctx.set_line_width(line_width)
        	ctx.rel_line_to(end_x, end_y)
		if close : ctx.close_path()
		if preserve: ctx.stroke_preserve()
		else: ctx.stroke()
		ctx.restore()

	def draw_rectangle(self,ctx,x,y,width,height,fill=True):
		"""Draws a rectangle"""
		ctx.save()
		ctx.translate(x, y)
		ctx.rectangle (0,0,width,height)
		if fill:ctx.fill()
		else: ctx.stroke()
		ctx.restore()

	def draw_rounded_rectangle(self,ctx,x,y,rounded_angle,width,height,fill=True):
		"""Draws a rounded rectangle"""
		ctx.save()
		ctx.translate(x, y)
		padding=0 # Padding from the edges of the window
        	rounded=rounded_angle # How round to make the edges 20 is ok
        	w = width
		h = height

        	# Move to top corner
        	ctx.move_to(0+padding+rounded, 0+padding)
        	
        	# Top right corner and round the edge
        	ctx.line_to(w-padding-rounded, 0+padding)
        	ctx.arc(w-padding-rounded, 0+padding+rounded, rounded, math.pi/2, 0)
	
        	# Bottom right corner and round the edge
        	ctx.line_to(w-padding, h-padding-rounded)
        	ctx.arc(w-padding-rounded, h-padding-rounded, rounded, 0, math.pi/2)
       	
        	# Bottom left corner and round the edge.
        	ctx.line_to(0+padding+rounded, h-padding)
        	ctx.arc(0+padding+rounded, h-padding-rounded, rounded, math.pi+math.pi/2, math.pi)
	
        	# Top left corner and round the edge
        	ctx.line_to(0+padding, 0+padding+rounded)
        	ctx.arc(0+padding+rounded, 0+padding+rounded, rounded, math.pi/2, 0)
        	
        	# Fill in the shape.
		if fill:ctx.fill()
		else: ctx.stroke()
		ctx.restore()

	def show_notification (self,text):
	        """Show notification window at current mouse position."""
		if self.notify == None:
	      		self.notify = Notify()
	        	self.notify.text = text
	        	self.notify.show()

	def hide_notification (self):
	        """hide notification window"""
		if self.notify != None:
			self.notify.hide()
			self.notify = None

	def show_tooltip (self,text,tooltipx,tooltipy):
	        """Show tooltip window at current mouse position."""
		if self.tooltip == None:
      			self.tooltip = Tooltip(300, 400)
        		self.tooltip.text = text
        		self.tooltip.x    = tooltipx
        		self.tooltip.y    = tooltipy
			self.tooltip.show()

	def hide_tooltip (self):
	        """hide tooltip window"""
		if self.tooltip != None:
			self.tooltip.hide()
			self.tooltip = None		

	def has_overrides (self):
		"""Check if this theme contains overrides for options."""
		return len(self.option_overrides) > 0
	
	def load_conf (self, filename):
		"""Load a config-file from this theme's dir and save vars in list."""
		ini = utils.IniReader()
		if ini.load(filename):
			if ini.has_section('Theme'):
				self.__name__ = ini.get_option('name', section='Theme')
				self.__author__ = ini.get_option('author', section='Theme')
				self.__version__ = ini.get_option('version', section='Theme')
				self.__info__ = ini.get_option('info', section='Theme')
			if ini.has_section('Options'):
				opts = ini.list_options(section='Options')
				if opts:
					for o in opts:
						self.option_overrides[o[0]] = o[1]
			print _("theme.conf loaded: ")
			print _("Name: ") + str(self.__name__)
			print _("Author: ") +str(self.__author__)
			print _("Version: ") +str(self.__version__)
			print _("Info: ") +str(self.__info__)
		else:
			print _("Failed to load theme.conf")
	
	
	def load_svg (self, filename):
		"""Load an SVG-file into this theme and reference it as ref_name."""
		if self.has_key(filename):
			del self[filename]
		self[filename] = rsvg.Handle(self.path + "/" + filename)
		self.svgs[filename[:-4]] = self[filename]
		if self[filename] != None:
			# set width/height
			size=self[filename].get_dimension_data()
			if size:
				self.width = size[0]
				self.height = size[1]
			return True
		else:
			return False
	
	def load_png (self, filename):
		"""Load a PNG-file into this theme and reference it as ref_name."""
		if self.has_key(filename):
			del self[filename]
		self[filename] = cairo.ImageSurface.create_from_png(self.path + 
			"/" + filename)
		self.pngs[filename[:-4]] = self[filename]
		if self[filename] != None:
			return True
		else:
			return False
	
	def __load_all (self):
		"""Load all files in the theme's path. Currently only loads SVGs and
		PNGs."""
		# clear overrides
		#self.__option_overrides = {}
		# read dir
		dirlst = glob.glob(self.path + '/*')
		if len(dirlst)==0:
			return False
		plen = len(self.path) + 1
		for file in dirlst:
			fname = file[plen:]
			if fname.endswith('.svg'):
				# svg file
				if self.load_svg(fname) == False:
					return False
			elif fname.endswith('.png'):
				# svg file
				if self.load_png(fname) == False:
					return False
			elif fname == "theme.conf":
				print _("theme.conf found! Loading option-overrides.")
				# theme.conf
				if self.load_conf(file) == False:
					return False
		return True
	
	def reload (self):
		"""Re-Load all files in the theme's path."""
		self.free()
		self.__load_all()
	
	# TODO: fix function, rsvg handles are not freed properly
	def free (self):
		"""Deletes the Theme's contents and frees all rsvg-handles.
		TODO: freeing rsvg-handles does NOT work for some reason"""
		self.option_overrides.clear()
		for filename in self:
			#self[filename].close()
			del filename
		self.clear()
	
	# TEST: render-function
	# should be used like "theme.render(context, 'notes-bg')" and then use
	# either an svg or png image
	def render (self, ctx, name):
		"""Render an image from within this theme to the given context. This
		function can EITHER use png OR svg images, so it is possible to 
		create themes using both image-formats when a Screenlet uses this
		function for drawing its images. The image name has to be defined
		without the extension and the function will automatically select 
		the available one (SVG is prefered over PNG)."""
		"""if self.has_key(name + '.svg'):
			self[name + '.svg'].render_cairo(ctx)
		else:
			ctx.set_source_surface(self[name + '.png'], 0, 0)
			ctx.paint()"""
		try:
			#self[name + '.svg'].render_cairo(ctx)
			self.svgs[name].render_cairo(ctx)
		except:
			#ctx.set_source_surface(self[name + '.png'], 0, 0)
			ctx.set_source_surface(self.pngs[name], 0, 0)
			ctx.paint()
			
		#else:
		#	ctx.set_source_pixbuf(self[name + '.png'], 0, 0)
		#	ctx.paint()


class Screenlet (gobject.GObject, EditableOptions):
	"""A Screenlet is a (i.e. contains a) shaped gtk-window that is
	fully invisible by default. Subclasses of Screenlet can render 
	their owner-drawn graphics on fully transparent background."""
	
	# default meta-info for Screenlets
	__name__	= _('No name set for this Screenlet')
	__version__	= '0.0'
	__author__	= _('No author defined for this Screenlet')
	__desc__	= _('No info set for this Screenlet')
	__requires__	= []		# still unused
	#__target_version__ = '0.0.0'
	#__backend_version__ = '0.0.1'
	
	# attributes (TODO: remove them here and add them to the constructor,
	# because they only should exist per instance)
	id				= ''		# id-attribute for handling instances
	window 			= None		# the gtk.Window behind the scenes
	theme 			= None		# the assigned ScreenletTheme
	uses_theme		= True		# flag indicating whether Screenlet uses themes
	menu 			= None		# the right-click gtk.Menu
	is_dragged 		= False		# TODO: make this work
	quit_on_close 	= True		# if True, closing this instance quits gtk
	saving_enabled	= True		# if False, saving is disabled
	dragging_over 	= False		# true if something is dragged over
	disable_updates	= False		# to temporarily avoid refresh/reshape
	p_context		= None		# PangoContext
	p_layout		= None		# PangoLayout
	
	# default editable options, available for all Screenlets
	x = 0
	y = 0
	mousex = 0
	mousey = 0
	width	= 100
	height	= 100
	scale	= 1.0
	theme_name		= ""
	is_sticky		= False
	is_widget		= False
	keep_above		= True
	keep_below		= False
	skip_pager		= True
	skip_taskbar	= True
	lock_position	= False
	allow_option_override 	= True		# if False, overrides are ignored
	ask_on_option_override	= True		# if True, overrides need confirmation
	has_started = False
	
	# internals (deprecated? we still don't get the end of a begin_move_drag)
	__lastx = 0
	__lasty = 0
	
	# some menuitems (needed for checking/unchecking)
	# DEPRECATED: remove - don't really work anyway ... (or fix the menu?)
	__mi_keep_above = None
	__mi_keep_below = None
	__mi_widget = None
	__mi_sticky = None
	__mi_lock = None	
	# for custom signals (which aren't acutally used ... yet)
	__gsignals__ = dict(screenlet_removed=(gobject.SIGNAL_RUN_FIRST,
		gobject.TYPE_NONE, (gobject.TYPE_OBJECT,)))

	def __init__ (self, id='', width=100, height=100, parent_window=None, 
		show_window=True, is_widget=False, is_sticky=False, 
		uses_theme=True, path=os.getcwd(), drag_drop=False, session=None, 
		enable_saving=True, service_class=services.ScreenletService,
		uses_pango=False):
		"""Constructor - should only be subclassed"""
		# call gobject and EditableOptions superclasses
		super(Screenlet, self).__init__()
		EditableOptions.__init__(self)
		# init properties
		self.id				= id
		self.session 		= session
		self.service		= None
		# if we have an id and a service-class, register our service
		if self.id and service_class:
			self.register_service(service_class)
			# notify service about adding this instance
			self.service.instance_added(self.id)
		self.width 			= width
		self.height 		= height
		self.is_dragged 	= False
		self.__path__ 		= path
		self.saving_enabled	= enable_saving		# used by session
		# set some attributes without calling __setattr__
		self.__dict__['theme_name'] = ""
		self.__dict__['is_widget'] 	= is_widget
		self.__dict__['is_sticky'] 	= is_sticky
		self.__dict__['x'] = 0
		self.__dict__['y'] = 0
		# TEST: set scale relative to theme size (NOT WORKING)
		#self.__dict__['scale'] = width/100.0
		# /TEST
		# shape bitmap
		self.__shape_bitmap = None
		self.__shape_bitmap_width = 0
		self.__shape_bitmap_height = 0
		# "editable" options, first create a group
		self.add_options_group('Screenlet', 
			_('The basic settings for this Screenlet-instance.'))
		# if this Screenlet uses themes, add theme-specific options
		# (NOTE: this option became hidden with 0.0.9 and doesn't use
		# get_available_themes anymore for showing the choices)
		if uses_theme:
			self.uses_theme = True
			self.add_option(StringOption('Screenlet', 'theme_name', 
				'default', '', '', hidden=True))
		# create/add options
		self.add_option(IntOption('Screenlet', 'x', 
			0, _('X-Position'), _('The X-position of this Screenlet ...'), 
			min=0, max=gtk.gdk.screen_width()))
		self.add_option(IntOption('Screenlet', 'y', 
			0, _('Y-Position'), _('The Y-position of this Screenlet ...'), 
			min=0, max=gtk.gdk.screen_height()))
		self.add_option(IntOption('Screenlet', 'width', 
			width, _('Width'), _('The width of this Screenlet ...'), 
			min=16, max=1000, hidden=True))
		self.add_option(IntOption('Screenlet', 'height', 
			height, _('Height'), _('The height of this Screenlet ...'), 
			min=16, max=1000, hidden=True))
		self.add_option(FloatOption('Screenlet', 'scale', 
			self.scale, _('Scale'), _('The scale-factor of this Screenlet ...'), 
			min=0.1, max=10.0, digits=2, increment=0.1))
		self.add_option(BoolOption('Screenlet', 'is_sticky', 
			is_sticky, _('Stick to Desktop'), 
			_('Show this Screenlet on all workspaces ...')))
		self.add_option(BoolOption('Screenlet', 'is_widget', 
			is_widget, _('Treat as Widget'), 
			_('Treat this Screenlet as a "Widget" ...')))
		self.add_option(BoolOption('Screenlet', 'lock_position', 
			self.lock_position, _('Lock position'), 
			_('Stop the screenlet from being moved...')))
		self.add_option(BoolOption('Screenlet', 'keep_above', 
			self.keep_above, _('Keep above'), 
			_('Keep this Screenlet above other windows ...')))
		self.add_option(BoolOption('Screenlet', 'keep_below', 
			self.keep_below, _('Keep below'), 
			_('Keep this Screenlet below other windows ...')))
		self.add_option(BoolOption('Screenlet', 'skip_pager', 
			self.skip_pager, _('Skip Pager'), 
			_('Set this Screenlet to show/hide in pagers ...')))
		self.add_option(BoolOption('Screenlet', 'skip_taskbar', 
			self.skip_pager, _('Skip Taskbar'), 
			_('Set this Screenlet to show/hide in taskbars ...')))
		if uses_theme:
			self.add_option(BoolOption('Screenlet', 'allow_option_override', 
			self.allow_option_override, _('Allow overriding Options'), 
				_('Allow themes to override options in this screenlet ...')))
			self.add_option(BoolOption('Screenlet', 'ask_on_option_override', 
				self.ask_on_option_override, _('Ask on Override'), 
				_('Show a confirmation-dialog when a theme wants to override ')+\
				_('the current options of this Screenlet ...')))
		# disable width/height
		self.disable_option('width')
		self.disable_option('height')
		# create window
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		if parent_window:
			self.window.set_parent_window(parent_window)
			self.window.set_transient_for(parent_window)
			self.window.set_destroy_with_parent(True)
		self.window.resize(width, height)
		self.window.set_decorated(False)
		self.window.set_app_paintable(True)
		# create pango layout, if active
		if uses_pango:
			self.p_context = self.window.get_pango_context()
			if self.p_context:
				self.p_layout = pango.Layout(self.p_context)
				self.p_layout.set_font_description(\
					pango.FontDescription("Sans 12"))
		# set type hint
		#self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
		self.window.set_keep_above(True)
		self.window.set_skip_taskbar_hint(True)
		self.window.set_skip_pager_hint(True)
		if is_sticky:
			self.window.stick()
		self.alpha_screen_changed(self.window)
		self.update_shape()
		#self.window.set_events(gtk.gdk.BUTTON_PRESS_MASK)
		self.window.set_events(gtk.gdk.ALL_EVENTS_MASK)
		self.window.connect("composited-changed", self.composite_changed)
		self.window.connect("delete_event", self.delete_event)
		self.window.connect("destroy", self.destroy)
		self.window.connect("expose_event", self.expose)
		self.window.connect("button-press-event", self.button_press)
		self.window.connect("button-release-event", self.button_release)
		self.window.connect("configure-event", self.configure_event)
		self.window.connect("screen-changed", self.alpha_screen_changed)
		self.window.connect("realize", self.realize_event)
		self.window.connect("enter-notify-event", self.enter_notify_event)
		self.window.connect("leave-notify-event", self.leave_notify_event)
		self.window.connect("focus-in-event", self.focus_in_event)
		self.window.connect("focus-out-event", self.focus_out_event)
		self.window.connect("scroll-event", self.scroll_event)
		self.window.connect("motion-notify-event",self.motion_notify_event)
		# add key-handlers (TODO: use keyword-attrib to activate?)
		self.window.connect("key-press-event", self.key_press)
		# drag/drop support (NOTE: still experimental and incomplete)
		if drag_drop:
			self.window.drag_dest_set(gtk.DEST_DEFAULT_MOTION |
				gtk.DEST_DEFAULT_DROP, #gtk.DEST_DEFAULT_ALL, 
				[("text/plain", 0, 0), 
				("image", 0, 1),
				("text/uri-list", 0, 2)], 
				gtk.gdk.ACTION_COPY)
			self.window.connect("drag_data_received", self.drag_data_received)
			self.window.connect("drag-begin", self.drag_begin)
			self.window.connect("drag-end", self.drag_end)
			self.window.connect("drag-motion", self.drag_motion)
			self.window.connect("drag-leave", self.drag_leave)
		# create menu
		self.menu = gtk.Menu()
		# show window so it can realize , but hiding it so we can show it only when atributes have been set , this fixes some placement errors arround the screen egde
		if show_window:
			self.window.show()
			self.window.hide()	

	def __setattr__ (self, name, value):
		# set the value in GObject (ESSENTIAL!!!!)
		self.on_before_set_atribute(name, value)
		gobject.GObject.__setattr__(self, name, value)
		# And do other actions
		if name=="x" or name=="y":
			self.window.move(self.x, self.y)
		elif name == 'scale':
			self.window.resize(int(self.width * self.scale), 
				int(self.height * self.scale))
			# TODO: call on_resize-handler here !!!!
			self.on_scale()
			self.redraw_canvas()
			self.update_shape()
		elif name == "theme_name":
			#self.__dict__ ['theme_name'] = value
			print _("LOAD NEW THEME: ") + value
			print _("FOUND: ") + str(self.find_theme(value))
			#self.load_theme(self.get_theme_dir() + value)
			# load theme
			path = self.find_theme(value)
			if path:
				self.load_theme(path)
			#self.load_first_theme(value)
			self.redraw_canvas()
			self.update_shape()
		elif name in ("width", "height"):
			#self.__dict__ [name] = value
			if self.window:
				self.window.resize(int(self.width*self.scale), int(self.height*self.scale))
				#self.redraw_canvas()
				self.update_shape()
		elif name == "is_widget":
			if self.has_started:
				self.set_is_widget(value)
		elif name == "is_sticky":
			if value == True:
				self.window.stick()
			else:
				self.window.unstick()
			#if self.__mi_sticky:
			#	self.__mi_sticky.set_active(value)
		elif name == "keep_above":
			self.window.set_keep_above(bool(value))
			#self.__mi_keep_above.set_active(value)
		elif name == "keep_below":
			self.window.set_keep_below(bool(value))
			#self.__mi_keep_below.set_active(value)
		elif name == "skip_pager":
			if self.window.window:
				self.window.window.set_skip_pager_hint(bool(value))
		elif name == "skip_taskbar":
			if self.window.window:
				self.window.window.set_skip_taskbar_hint(bool(value))
		# NOTE: This is the new recommended way of storing options in real-time
		#       (we access the backend through the session here)
		if self.saving_enabled:
			o = self.get_option_by_name(name)
			if o != None:
				self.session.backend.save_option(self.id, o.name, 
					o.on_export(value))
		self.on_after_set_atribute(name, value)
		# /TEST
	
	#-----------------------------------------------------------------------
	# Screenlet's public functions
	#-----------------------------------------------------------------------
	
	# NOTE: This function is deprecated and will get removed. The
	# XML-based menus should be preferred
	def add_default_menuitems (self, flags=DefaultMenuItem.STANDARD):
		"""Appends the default menu-items to self.menu. You can add on OR'ed
		   flag with DefaultMenuItems you want to add."""
		if not self.has_started: print 'WARNING - add_default_menuitems and add_menuitems should be set in on_init ,menu values will be displayed incorrectly'
		# children already exist? add separator
		if len(self.menu.get_children()) > 0:
			self.add_menuitem("", "-")
		# create menu (or submenu?)
		#if flags & DefaultMenuItem.IS_SUBMENU :
		#	menu = gtk.Menu()
		#else:
		menu = self.menu
		# EXPERIMENTAL:
		if flags & DefaultMenuItem.XML:
			# create XML-menu from screenletpath/menu.xml
			xfile = self.get_screenlet_dir() + "/menu.xml"
			xmlmenu = XmlMenu.create_menu_from_file(xfile, 
				self.menuitem_callback)
			if xmlmenu:
				self.menu = xmlmenu
			pass
		# add size-selection
		if flags & DefaultMenuItem.SIZE:
			size_item = gtk.MenuItem(_("Size"))
			size_item.show()
			size_menu = gtk.Menu()
			menu.append(size_item)
			size_item.set_submenu(size_menu)
			#for i in xrange(10):
			for i in (0.2,0.3,0.4, 0.5,0.6, 0.7,0.8,0.9, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.5, 10):
				s = str(int(i * 100))
				item = gtk.MenuItem(s + " %")
				item.connect("activate", self.menuitem_callback, 
					"scale:"+str(i))
				item.show()
				size_menu.append(item)
		# create theme-selection menu
		if flags & DefaultMenuItem.THEMES:
			themes_item = gtk.MenuItem(_("Theme"))
			themes_item.show()
			themes_menu = gtk.Menu()
			menu.append(themes_item)
			themes_item.set_submenu(themes_menu)
			# create theme-list from theme-directory
			lst = self.get_available_themes()
			for tname in lst:
				item = gtk.MenuItem(tname)
				item.connect("activate", self.menuitem_callback, 
					"theme:"+tname)
				item.show()
				themes_menu.append(item)
		# add window-options menu
		if flags & DefaultMenuItem.WINDOW_MENU:
			winmenu_item = gtk.MenuItem(_("Window"))
			winmenu_item.show()
			winmenu_menu = gtk.Menu()
			menu.append(winmenu_item)
			winmenu_item.set_submenu(winmenu_menu)
			# add "lock"-menuitem
			self.__mi_lock = item = gtk.CheckMenuItem(_("Lock"))
			item.set_active(self.lock_position)
			item.connect("activate", self.menuitem_callback, 
				"option:lock")
			item.show()
			winmenu_menu.append(item)
			# add "Sticky"-menuitem
			self.__mi_sticky = item = gtk.CheckMenuItem(_("Sticky"))
			item.set_active(self.is_sticky)
			item.connect("activate", self.menuitem_callback, 
				"option:sticky")
			item.show()
			winmenu_menu.append(item)
			# add "Widget"-menuitem
			self.__mi_widget = item = gtk.CheckMenuItem(_("Widget"))
			item.set_active(self.is_widget)
			item.connect("activate", self.menuitem_callback, 
				"option:widget")
			item.show()
			winmenu_menu.append(item)
			# add "Keep above"-menuitem
			self.__mi_keep_above = item = gtk.CheckMenuItem(_("Keep above"))
			item.set_active(self.keep_above)
			item.connect("activate", self.menuitem_callback, 
				"option:keep_above")
			item.show()
			winmenu_menu.append(item)
			# add "Keep Below"-menuitem
			self.__mi_keep_below = item = gtk.CheckMenuItem(_("Keep below"))
			item.set_active(self.keep_below)
			item.connect("activate", self.menuitem_callback, 
				"option:keep_below")
			item.show()
			winmenu_menu.append(item)
		# add Settings-item
		if flags & DefaultMenuItem.PROPERTIES:
			self.add_menuitem("", "-")
			self.add_menuitem("options", _("Properties..."))
		# add info-item
		if flags & DefaultMenuItem.INFO:
			self.add_menuitem("", "-")
			self.add_menuitem("info", _("Info..."))
		# add delete item
		if flags & DefaultMenuItem.DELETE:
			self.add_menuitem("", "-")
			self.add_menuitem("delete", _("Delete Screenlet ..."))
		# add Quit-item
		self.add_menuitem("", "-")
		self.add_menuitem("quit_instance", _("Quit this %s ...") % self.get_short_name())
		# add Quit-item
		self.add_menuitem("", "-")
		self.add_menuitem("quit", _("Quit all %ss ...") % self.get_short_name())

	def add_menuitem (self, id, label, callback=None):
		"""Simple way to add menuitems to the right-click menu."""
		if not self.has_started: print 'WARNING - add_default_menuitems and add_menuitems should be set in on_init ,menu values will be displayed incorrectly'
		if callback == None:
			callback = self.menuitem_callback
		if label == "-":
			menu_item = gtk.SeparatorMenuItem()
		else:
			menu_item = gtk.MenuItem(label)
			menu_item.connect("activate", callback, id)
		self.menu.append(menu_item)
		menu_item.show()
		return menu_item
	
	def clear_cairo_context (self, ctx):
		"""Fills the given cairo.Context with fully transparent white."""
		ctx.save()
		ctx.set_source_rgba(1, 1, 1, 0)
		ctx.set_operator (cairo.OPERATOR_SOURCE)
		ctx.paint()
		ctx.restore()

	def close (self):
		"""Close this Screenlet
		   TODO: send close-notify instead of destroying window?"""
		#self.save_settings()
		self.window.unmap()
		self.window.destroy()
		#self.window.event(gtk.gdk.Event(gtk.gdk.DELETE))
	
	def create_drag_icon (self):
		"""Create drag-icon and -mask for drag-operation. Returns a 2-tuple
		with the icon and the mask. To supply your own icon you can use the
		on_create_drag_icon-handler and return the icon/mask as 2-tuple."""
		w = self.width
		h = self.height
		icon, mask = self.on_create_drag_icon()
		if icon == None:
			# create icon
			icon = gtk.gdk.Pixmap(self.window.window, w, h)
			ctx = icon.cairo_create()
			self.clear_cairo_context(ctx)
			self.on_draw(ctx)
		if mask == None:
			# create mask
			mask = gtk.gdk.Pixmap(self.window.window, w, h)
			ctx = mask.cairo_create()
			self.clear_cairo_context(ctx)
			self.on_draw_shape(ctx)
		return (icon, mask)
	
	def enable_saving (self, enabled=True):
		"""Enable/Disable realtime-saving of options."""
		self.saving_enabled = enabled
	
	def find_theme (self, name):
		"""Find the first occurence of a theme and return its global path."""
		sn = self.get_short_name()
		for p in SCREENLETS_PATH:
			fpath = p + '/' + sn + '/themes/' + name
			if os.path.isdir(fpath):
				return fpath
		return None
	
	def get_short_name (self):
		"""Return the short name of this screenlet. This returns the classname
		of the screenlet without trailing "Screenlet". Please always use
		this function if you want to retrieve the short name of a Screenlet."""
		return self.__class__.__name__[:-9]
		
	def get_screenlet_dir (self):
		"""@DEPRECATED: Return the name of this screenlet's personal directory."""
		p = utils.find_first_screenlet_path(self.get_short_name())
		if p:
			return p
		else:
			if self.__path__ != '':
				return self.__path__
			else:
				return os.getcwd()
	
	def get_theme_dir (self):
		"""@DEPRECATED: Return the name of this screenlet's personal theme-dir.
		(Only returns the dir under the screenlet's location"""
		return self.get_screenlet_dir() + "/themes/"
	
	def get_available_themes (self):
		"""Returns a list with the names of all available themes in this
			Screenlet's theme-directory."""
		lst = []
		for p in SCREENLETS_PATH:
			d = p + '/' + self.get_short_name() + '/themes/'
			if os.path.isdir(d):
				#dirname = self.get_theme_dir()
				dirlst = glob.glob(d + '*')
				dirlst.sort()
				tdlen = len(d)
				for fname in dirlst:
					dname = fname[tdlen:]
					# TODO: check if it's a dir
					lst.append(dname)
		return lst

	def finish_loading(self):
		"""Called when screenlet finishes loading"""
		self.has_started = True
		self.on_init()
		try: self.window.show()			
		except:	print 'unable to show window'
		# the keep above and keep bellow must be reset after the window is shown this is absolutly necessary 
		self.keep_above= self.keep_above
		self.keep_below= self.keep_below
		if self.is_widget:
			self.set_is_widget(True)
	def hide (self):
		"""Hides this Screenlet's underlying gtk.Window"""
		self.window.hide()
		self.on_hide()
	
	# EXPERIMENTAL:
	# NOTE: load_theme does NOT call redraw_canvas and update_shape!!!!!
	# To do all in one, set attribute self.theme_name instead
	def load_theme (self, path):
		"""Load a theme for this Screenlet from the given path. NOTE: 
		load_theme does NOT call redraw_canvas and update_shape!!!!! To do all 
		in one call, set the attribute self.theme_name instead."""
		if self.theme:
			self.theme.free()
			del self.theme
		self.theme = ScreenletTheme(path)
		# check for errors
		if self.theme.loaded == False:
			print _("Error while loading theme: ") + path
			self.theme = None
		else:
			# call user-defined handler
			self.on_load_theme()
			# if override options is allowed, apply them
			if self.allow_option_override:
				if self.theme.has_overrides():
					if self.ask_on_option_override==True and \
						show_question(self, 
						_('This theme wants to override your settings for ')+\
						_('this Screenlet. Do you want to allow that?')) == False:
						return
					self.theme.apply_option_overrides(self)
	# /EXPERIMENTAL
	
	def main (self):
		"""If the Screenlet runs as stand-alone app, starts gtk.main()"""
		gtk.main()
	
	def register_service (self, service_classobj):
		"""Register or create the given ScreenletService-(sub)class as the new 
		service for this Screenlet. If self is not the first instance in the
		current session, the service from the first instance will be used 
		instead and no new service is created."""
		if self.session:
			if len(self.session.instances) == 0:
				# if it is the basic service, add name to call
				if service_classobj==services.ScreenletService:
					self.service = service_classobj(self, self.get_short_name())
				else:
					# else only pass this screenlet
					self.service = service_classobj(self)
			else:
				self.service = self.session.instances[0].service
			# TODO: throw exception??
			return True
		return False
	
	def set_is_widget (self, value):
		"""Set this window to be treated as a Widget (only supported by
		compiz using the widget-plugin yet)"""
		if value==True:
			# set window type to utility
			#self.window.window.set_type_hint(
			#	gtk.gdk.WINDOW_TYPE_HINT_UTILITY)
			# set _compiz_widget-property on window
			self.window.window.property_change("_COMPIZ_WIDGET", 
				gtk.gdk.SELECTION_TYPE_WINDOW,
				32, gtk.gdk.PROP_MODE_REPLACE, (True,))
		else:
			# set window type to normal
			#self.window.window.set_type_hint(
			#	gtk.gdk.WINDOW_TYPE_HINT_NORMAL)
			# set _compiz_widget-property
			self.window.window.property_delete("_COMPIZ_WIDGET")
		# notify handler
		self.on_switch_widget_state(value)
	
	def show (self):
		"""Show this Screenlet's underlying gtk.Window"""
		self.window.show()
		self.window.move(self.x, self.y)
		self.on_show()
	
	def show_settings_dialog (self):
		"""Show the EditableSettingsDialog for this Screenlet."""
		se = OptionsDialog(490, 450)
		img = gtk.Image()
		try:
			d = self.get_screenlet_dir()
			if os.path.isfile(d + '/icon.svg'):
				icn = gtk.gdk.pixbuf_new_from_file(d + '/icon.svg')
			elif os.path.isfile(d + '/icon.png'):
				icn = gtk.gdk.pixbuf_new_from_file(d + '/icon.png')
			img.set_from_pixbuf(icn)
		except:
			img.set_from_stock(gtk.STOCK_PROPERTIES, 5)
		se.set_title(self.__name__)
		se.set_info(self.__name__, self.__desc__, '(c) by ' + self.__author__, 
			version='v' + self.__version__, icon=img)
		se.show_options_for_object(self)
		resp = se.run()
		if resp == gtk.RESPONSE_REJECT:	# TODO!!!!!
			se.reset_to_defaults()
		else:
			self.update_shape()
		se.destroy()
	
	def redraw_canvas (self):
		"""Redraw the entire Screenlet's window area.
		TODO: store window alloaction in class and change when size changes."""
		# if updates are disabled, just exit
		if self.disable_updates:
			return
		if self.window:
			x, y, w, h = self.window.get_allocation()
			rect = gtk.gdk.Rectangle(x, y, w, h)
			if self.window.window:
				self.window.window.invalidate_rect(rect, True)
				self.window.window.process_updates(True)
	
	def redraw_canvas_area (self, x, y, width, height):
		"""Redraw the given Rectangle (x, y, width, height) within the 
		current Screenlet's window."""
		# if updates are disabled, just exit
		if self.disable_updates:
			return
		if self.window:
			rect = gtk.gdk.Rectangle(x, y, width, height)
			if self.window.window:
				self.window.window.invalidate_rect(rect, True)
				self.window.window.process_updates(True)

	def remove_shape(self):
		"""Removed shaped window , in case the nom composited shape has been set"""
		if self.window.window:
			self.window.window.shape_combine_mask(None,0,0)	

	def update_shape (self):
		"""Update window shape (only call this when shape has changed
		because it is very ressource intense if ran too often)."""
		# if updates are disabled, just exit
		if self.disable_updates:
			return
		print _("UPDATING SHAPE")
		# TODO:
		#if not self.window.is_composited():
		#	self.update_shape_non_composited()
		# calculate new width/height of shape bitmap
		w = int(self.width * self.scale)
		h = int(self.height * self.scale)
		# if 0 set it to 100 to avoid crashes and stay interactive
		if w==0: w = 100
		if h==0: h = 100
		# if size changed, recreate shape bitmap
		if w != self.__shape_bitmap_width or h != self.__shape_bitmap_height:
			data = ''.zfill(w*h)
			self.__shape_bitmap = gtk.gdk.bitmap_create_from_data(None, data, 
				w, h)
			self.__shape_bitmap_width = w
			self.__shape_bitmap_height = h
		# create context and draw shape
		ctx = self.__shape_bitmap.cairo_create()
		self.clear_cairo_context(ctx)		#TEST

		# shape the window acording if the window is composited  or not

		if self.window.is_composited():
			
			self.on_draw_shape(ctx)
			# and cut window with mask 	
			self.window.input_shape_combine_mask(self.__shape_bitmap, 0, 0)
		else:
			try: self.on_draw(ctx) #Works better then the shape method on non composited windows
			except:	self.on_draw_shape(ctx) # if error on on_draw use standard shape method
			# and cut window with mask 
			self.window.shape_combine_mask(self.__shape_bitmap,0,0)

	def update_shape_non_composited (self):
		"""TEST: This function is intended to shape the window whenever no
		composited environment can be found. (NOT WORKING YET!!!!)"""
		#pixbuf = gtk.gdk.GdkPixbuf.new_from_file)
		# calculate new width/height of shape bitmap
		w = int(self.width * self.scale)
		h = int(self.height * self.scale)
		# if 0 set it to 100 to avoid crashes and stay interactive
		if w==0: w = 100
		if h==0: h = 100
		# if size changed, recreate shape bitmap
		if w != self.__shape_bitmap_width or h != self.__shape_bitmap_height:
			data = ''.zfill(w*h)
			self.__shape_bitmap = gtk.gdk.pixbuf_new_from_data(data,
				gtk.gdk.COLORSPACE_RGB, True, 1, w, h, w)
			self.__shape_bitmap_width = w
			self.__shape_bitmap_height = h
			# and render window contents to it
			# TOOD!!
			if self.__shape_bitmap:
				# create new mask
				(pixmap,mask) = self.__shape_bitmap.render_pixmap_and_mask(255)
				# apply new mask to window
				self.window.shape_combine_mask(mask)

	# ----------------------------------------------------------------------
	# Screenlet's event-handler dummies
	# ----------------------------------------------------------------------
	
	def on_delete (self):
		"""Called when the Screenlet gets deleted. Return True to cancel.
		TODO: sometimes not properly called"""
		return not show_question(self, _("To quit all %s's, use 'Quit' instead. ") % self.__class__.__name__ +\
			_('Really delete this %s and its settings?') % self.get_short_name())
		"""return not show_question(self, 'Deleting this instance of the '+\
				self.__name__ + ' will also delete all your personal '+\
				'changes you made to it!! If you just want to close the '+\
				'application, use "Quit" instead. Are you sure you want to '+\
				'delete this instance?')
		return False"""
	
	# TODO: on_drag
	# TODO: on_drag_end

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
	
	def on_draw (self, ctx):
		"""Callback for drawing the Screenlet's window - override
		in subclasses to implement your own drawing."""
		pass
	
	def on_draw_shape (self, ctx):
		"""Callback for drawing the Screenlet's shape - override
		in subclasses to draw the window's input-shape-mask."""
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
		pass
	
	def on_key_down (self, keycode, keyvalue, event=None):
		"""Called when a key is pressed within the screenlet's window."""
		pass
	
	def on_load_theme (self):
		"""Called when the theme is reloaded (after loading, before redraw)."""
		pass
	
	def on_menuitem_select (self, id):
		"""Called when a menuitem is selected."""
		pass
	
	def on_mouse_down (self, event):
		"""Called when a buttonpress-event occured in Screenlet's window. 
		Returning True causes the event to be not further propagated."""
		return False
	
	def on_mouse_enter (self, event):
		"""Called when the mouse enters the Screenlet's window."""
		pass
		
	def on_mouse_leave (self, event):
		"""Called when the mouse leaves the Screenlet's window."""
		pass

	def on_mouse_move(self, event):
		"""Called when the mouse moves in the Screenlet's window."""
		pass
	
	def on_mouse_up (self, event):
		"""Called when a buttonrelease-event occured in Screenlet's window. 
		Returning True causes the event to be not further propagated."""
		return False
	
	def on_quit (self):
		"""Callback for handling destroy-event. Perform your cleanup here!"""
		return True
		
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
	
	# ----------------------------------------------------------------------
	# Screenlet's event-handlers for GTK-events
	# ----------------------------------------------------------------------
	
	def alpha_screen_changed (self, window, screen=None):
		"""set colormap for window"""
		if screen==None:
			screen = window.get_screen()
		map = screen.get_rgba_colormap()
		if map:
			pass
		else:
			map = screen.get_rgb_colormap()
		window.set_colormap(map)		
	
	def button_press (self, widget, event):
		#print "Button press"
		# set flags for user-handler
		if self.lock_position == False:
			if event.button == 1:
				self.is_dragged = True
		# call user-handler for onmousedown
		if self.on_mouse_down(event) == True:
			return True
		# unhandled? continue
		if self.lock_position == False:
			if event.button == 1:
				widget.begin_move_drag(event.button, int(event.x_root), 
					int(event.y_root), event.time)
		
		if event.button == 3:
			try:
				self.__mi_lock.set_active(self.lock_position)
				self.__mi_sticky.set_active(self.is_sticky)
				self.__mi_widget.set_active(self.is_widget)
				self.__mi_keep_above.set_active(self.keep_above)
				self.__mi_keep_below.set_active(self.keep_below)
			except : pass
			self.menu.popup(None, None, None, event.button, event.time)
		elif event.button == 4:
			print _("MOUSEWHEEL")
			self.scale -= 0.1
		elif event.button == 5:
			print _("MOUSEWHEEL")
			self.scale += 0.1
		return False
	
	def button_release (self, widget, event):
		print "Button release"
		self.is_dragged = False	# doesn't work!!! we don't get an event when move_drag ends :( ...
		if self.on_mouse_up(event):
			return True
		return False

	def composite_changed(self,widget):
		#this handle is called when composition changed
		self.remove_shape() # removing previous set shape , this is absolutly necessary
		self.window.hide() # hiding the window and showing it again so the window can convert to the right composited state
		self.is_sticky = self.is_sticky	 #changing from non composited to composited makes the screenlets loose sticky state , this fixes that
		self.window.show()
		print 'composite change to ' + str(self.window.is_composited())
		self.redraw_canvas()
		self.update_shape()
		self.is_sticky = self.is_sticky #and again ...
		self.on_composite_changed()

	# NOTE: this should somehow handle the end of a move_drag-operation
	def configure_event (self, widget, event):
		#print "onConfigure"
		#print event
		#if self.is_dragged == True:
		# set new position and cause a save of this Screenlet (not use 
		# setattr to avoid conflicts with the window.move in __setattr__)
		if event.x != self.x:
			self.__dict__['x'] = event.x
			if self.session:
				self.session.backend.save_option(self.id, 'x', str(event.x))
		if event.y != self.y:
			self.__dict__['y'] = event.y
			if self.session:
				self.session.backend.save_option(self.id, 'y', str(event.y))
		return False
	
	def delete_event (self, widget, event, data=None):
		# cancel event?
		print "delete_event"
		if self.on_delete() == True:
			print _("Cancel delete_event")
			return True
		else:
			self.close()
		return False

	def destroy (self, widget, data=None):
		# call user-defined on_quit-handler
		self.on_quit()
		#print "destroy signal occurred"
		self.emit("screenlet_removed", self)
		# close gtk?
		if self.quit_on_close:
			if self.session:	# if we have a session, flush current data
				self.session.backend.flush()
			gtk.main_quit()
		else:
			del self		# ??? does this really work???
	
	def drag_begin (self, widget, drag_context):
		print _("Start drag")
		self.is_dragged = True
		self.on_drag_begin(drag_context)
		#return False
	
	def drag_data_received (self, widget, dc, x, y, sel_data, info, timestamp):
		return self.on_drop(x, y, sel_data, timestamp)
	
	def drag_end (self, widget, drag_context):
		print _("End drag")
		self.is_dragged = False
		return False
	
	def drag_motion (self, widget, drag_context, x, y, timestamp):
		#print "Drag motion"
		if self.dragging_over == False:
			self.dragging_over = True
			self.on_drag_enter(drag_context, x, y, timestamp)
		return False
	
	def drag_leave (self, widget, drag_context, timestamp):
		self.dragging_over = False
		self.on_drag_leave(drag_context, timestamp)
		return
	
	def enter_notify_event (self, widget, event):
		#self.__mouse_inside = True
		self.on_mouse_enter(event)
		#self.redraw_canvas()
	
	def expose (self, widget, event):
		ctx = widget.window.cairo_create()
		# clear context
		self.clear_cairo_context(ctx)
		# set a clip region for the expose event
		ctx.rectangle(event.area.x, event.area.y,
			event.area.width, event.area.height)
		ctx.clip()
		# scale context
		#ctx.scale(self.scale, self.scale)
		# call drawing method
		self.on_draw(ctx)
		# and delete context (needed?)
		del ctx
		return False
	
	def focus_in_event (self, widget, event):
		self.on_focus(event)
	
	def focus_out_event (self, widget, event):
		self.on_unfocus(event)
	
	def key_press (self, widget, event):
		"""Handle keypress events, needed for in-place editing."""
		self.on_key_down(event.keyval, event.string, event)
	
	def leave_notify_event (self, widget, event):
		#self.__mouse_inside = False
		self.on_mouse_leave(event)
	
	def menuitem_callback (self, widget, id):
		if id == "delete":
			if not self.on_delete():
				# remove instance
				self.session.delete_instance (self.id)
				# notify about being rmeoved (does this get send???)
				self.service.instance_removed(self.id)
		elif id == "quit_instance":
			print 'quiting this one only'
			self.session.quit_instance (self.id)
			self.service.instance_removed(self.id)
		elif id == "quit":
			self.close()
		elif id in ("info", "about", "settings", "options", "properties"):
			# show settings dialog
			self.show_settings_dialog()
		elif id.startswith('scale:'):
			self.scale = float(id[6:])
		elif id[:5] == "size:":	# DEPRECATED??
			# set size and update shape (redraw is done by setting height)
			#self.__dict__['width'] = int(id[5:])
			self.width = int(id[5:])
			self.height = int(id[5:])
			self.update_shape()
		elif id[:6]=="theme:":
			print "Screenlet: Set theme " + id[6:]
			# set theme
			self.theme_name = id[6:]
		elif id[:8] == "setting:":
			# set a boolean option to the opposite state
			try:
				if type(self.__dict__[id[8:]]) == bool:
					self.__dict__[id[8:]] = not self.__dict__[id[8:]]	# UNSAFE!!
			except:
				print _("Error: Cannot set missing or non-boolean value '")\
					+ id[8:] + "'"
		elif id[:7] == "option:":
			# NOTE: this part should be removed and XML-menus
			#		should be used by default ... maybe
			# set option
			if id[7:]=="lock":
				if self.__mi_lock.get_active () != self.lock_position:
					self.lock_position = not self.lock_position
			elif id[7:]=="sticky":
				if self.__mi_sticky.get_active () != self.is_sticky:
					self.is_sticky = not self.is_sticky
				#widget.toggle()
			elif id[7:]=="widget":
				if self.__mi_widget.get_active () != self.is_widget:
					self.is_widget = not self.is_widget
			elif id[7:]=="keep_above":
				if self.__mi_keep_above.get_active () != self.keep_above:
					self.keep_above = not self.keep_above
					self.__mi_keep_above.set_active(self.keep_above)
					if self.keep_below and self.keep_above : 
						self.keep_below = False
						self.__mi_keep_below.set_active(False)
			elif id[7:]=="keep_below":
				if self.__mi_keep_below.get_active () != self.keep_below:
					self.keep_below = not self.keep_below
					self.__mi_keep_below.set_active(self.keep_below)
					if self.keep_below and self.keep_above : 
						self.keep_above = False
						self.__mi_keep_above.set_active(False)
		else:
			#print "Item: " + string
			pass
		# call user-handler
		self.on_menuitem_select(id)
		return False

	def motion_notify_event(self, widget, event):
		self.mousex = event.x / self.scale
		self.mousey = event.y / self.scale
		self.on_mouse_move(event)
	
	def realize_event (self, widget):
		"""called when window has been realized"""
		if self.window.window:
			self.window.window.set_back_pixmap(None, False)	# needed?

		self.on_realize()
	
	def scroll_event (self, widget, event):
		if event.direction == gtk.gdk.SCROLL_UP:
			self.on_scroll_up()
		elif event.direction == gtk.gdk.SCROLL_DOWN:
			self.on_scroll_down()
		return False



# TEST!!!
class ShapedWidget (gtk.DrawingArea):
	"""A simple base-class for creating owner-drawn gtk-widgets"""
	
	__widget=None
	
	mouse_inside = False
	width = 32
	height = 32
	
	def __init__ (self, width, height):
		# call superclass
		super(ShapedWidget, self).__init__()
		# create/setup widget
		#self.__widget = gtk.Widget()
		self.set_app_paintable(True)
		self.set_size_request(width, height)
		# connect handlers
		self.set_events(gtk.gdk.ALL_EVENTS_MASK)
		self.connect("expose-event", self.expose_event)
		self.connect("button-press-event", self.button_press)
		self.connect("button-release-event", self.button_release)
		self.connect("enter-notify-event", self.enter_notify)
		self.connect("leave-notify-event", self.leave_notify)
	
	# EXPERIMENTAL: TODO: cache bitmap until size changes
	def update_shape (self):
		"""update widget's shape (only call this when shape has changed)"""
		data = ""
		for i in xrange(self.width*self.height):
			data += "0"
		bitmap = gtk.gdk.bitmap_create_from_data(None, 
			data, self.width, self.height)
		ctx = bitmap.cairo_create()
		ctx.set_source_rgba(1, 1, 1, 0)
		ctx.set_operator (cairo.OPERATOR_SOURCE)
		ctx.paint()
		self.draw_shape(ctx)
		self.input_shape_combine_mask(bitmap, 0, 0)
		print "Updating shape."
	
	def button_press (self, widget, event):
		if event.button==1:
			print "left button pressed!"
		return False
		
	def button_release (self, widget, event):
		#if event.button==1:
			#print "left button release!"
		return False
	
	def enter_notify (self, widget, event):
		self.mouse_inside = True
		self.queue_draw()
		#print "mouse enter"
	
	def leave_notify (self, widget, event):
		self.mouse_inside = False
		self.queue_draw()
		#print "mouse leave"
	
	def draw (self, ctx):
		pass
		
	def draw_shape (self, ctx):
		self.draw(ctx)
	
	def expose_event (self, widget, event):
		ctx = widget.window.cairo_create()
		# set a clip region for the expose event
		ctx.rectangle(event.area.x, event.area.y,
			event.area.width, event.area.height)
		ctx.clip()
		# clear context
		ctx.set_source_rgba(1, 1, 1, 0)
		ctx.set_operator (cairo.OPERATOR_SOURCE)
		ctx.paint()
		# call drawing method
		self.draw(ctx)
		# and delete context
		del ctx
		return False

class Tooltip:
	"""A window that displays a text and serves as Tooltip (very basic yet)."""
	
	# internals
	__timeout    = None
    
	# attribs
	text        = ''
	font_name    = 'FreeSans 9'
	width        = 100
	height        = 20
	x             = 0
	y             = 0
    
	def __init__ (self, width, height):
		object.__init__(self)
		# init
		self.__dict__['width']    = width
		self.__dict__['height']    = height
		self.window = gtk.Window()
		self.window.set_app_paintable(True)
		self.window.set_size_request(width, height)
		self.window.set_decorated(False)
		self.window.set_accept_focus(False)
		self.window.set_skip_pager_hint(True)
		self.window.set_skip_taskbar_hint(True)
		self.window.set_keep_above(True)
		self.screen_changed(self.window)
		self.window.connect("expose_event", self.expose)
		self.window.connect("screen-changed", self.screen_changed)
		#self.window.show()
		self.p_context = self.window.get_pango_context()
		self.p_layout = pango.Layout(self.p_context)
		self.p_layout.set_font_description(\
		pango.FontDescription(self.font_name))
		#self.p_layout.set_width(-1)
		self.p_layout.set_width(width * pango.SCALE - 6)
    
	def __setattr__ (self, name, value):
		self.__dict__[name] = value
		if name in ('width', 'height', 'text'):
			if name== 'width':
				self.p_layout.set_width(width)
			elif name == 'text':
				self.p_layout.set_markup(value)
				ink_rect, logical_rect = self.p_layout.get_pixel_extents()
				self.height = min(max(logical_rect[3], 16), 400) + 6
				self.window.set_size_request(self.width, self.height)
			self.window.queue_draw()
		elif name == 'x':
			self.window.move(int(value), int(self.y))
		elif name == 'y':
			self.window.move(int(self.x), int(value))
    
	def show (self):
		"""Show the Tooltip window."""
		self.cancel_show()
		self.window.show()
		self.window.set_keep_above(True)
   
	def show_delayed (self, delay):
		"""Show the Tooltip window after a given delay."""
		self.cancel_show()
		self.__timeout = gobject.timeout_add(delay, self.__show_timeout)
    
	def hide (self):
		"""Hide the Tooltip window."""
		self.cancel_show()
		self.window.destroy()
    
	def cancel_show (self):
		"""Cancel showing of the Tooltip."""
		if self.__timeout:
			gobject.source_remove(self.__timeout)
			self.p_context = None
			self.p_layout = None
    
	def __show_timeout (self):
		self.show()
    
	def screen_changed (self, window, screen=None):
		if screen == None:
			screen = window.get_screen()
		map = screen.get_rgba_colormap()
		if not map:
			map = screen.get_rgb_colormap()
		window.set_colormap(map)
    
	def expose (self, widget, event):
		ctx = self.window.window.cairo_create()
		ctx.set_antialias (cairo.ANTIALIAS_SUBPIXEL)    # ?
		# set a clip region for the expose event
		ctx.rectangle(event.area.x, event.area.y,event.area.width, event.area.height)
		ctx.clip()
		# clear context
		ctx.set_source_rgba(1, 1, 1, 0)
		ctx.set_operator (cairo.OPERATOR_SOURCE)
		ctx.paint()
		# draw rectangle
		ctx.set_source_rgba(1, 1, 0.5, 1)
		ctx.rectangle(0, 0, self.width, self.height)
		ctx.fill()
		# draw text
		ctx.save()
		ctx.translate(3, 3)
		ctx.set_source_rgba(0, 0, 0, 1) 
		ctx.show_layout(self.p_layout)
		ctx.fill()
		ctx.restore()
		ctx.rectangle(0, 0, self.width, self.height)
		ctx.set_source_rgba(0, 0, 0, 0.7)
		ctx.stroke()

class Notify:
	"""A window that displays a text and serves as Notification (very basic yet)."""
	
	# internals
	__timeout    = None
    
	# attribs
	text        = ''
	font_name    = 'FreeSans 9'
	width        = 200
	height        = 100
	x             = 0
	y             = 0
	gradient = cairo.LinearGradient(0, 100,0, 0)
    
	def __init__ (self):
		object.__init__(self)
		# init
		self.window = gtk.Window()
		self.window.set_app_paintable(True)
		self.window.set_size_request(self.width, self.height)
		self.window.set_decorated(False)
		self.window.set_accept_focus(False)
		self.window.set_skip_pager_hint(True)
		self.window.set_skip_taskbar_hint(True)
		self.window.set_keep_above(True)
		self.screen_changed(self.window)
		self.window.connect("expose_event", self.expose)
		self.window.connect("screen-changed", self.screen_changed)
		#self.window.show()
		self.p_context = self.window.get_pango_context()
		self.p_layout = pango.Layout(self.p_context)
		self.p_layout.set_font_description(\
		pango.FontDescription(self.font_name))
		#self.p_layout.set_width(-1)
		self.p_layout.set_width(self.width * pango.SCALE - 6)
    
	def __setattr__ (self, name, value):
		self.__dict__[name] = value
		if name in ('text'):
			if name == 'text':
				self.p_layout.set_markup(value)
				ink_rect, logical_rect = self.p_layout.get_pixel_extents()
			self.window.queue_draw()

	def show (self):
		"""Show the Notify window."""
		self.window.move(gtk.gdk.screen_width() - self.width, gtk.gdk.screen_height() - self.height)
		self.cancel_show()
		self.window.show()
		self.window.set_keep_above(True)
   
	def show_delayed (self, delay):
		"""Show the Notify window after a given delay."""
		self.cancel_show()
		self.__timeout = gobject.timeout_add(delay, self.__show_timeout)
    
	def hide (self):
		"""Hide the Notify window."""
		self.cancel_show()
		self.window.destroy()
    
	def cancel_show (self):
		"""Cancel showing of the Notify."""
		if self.__timeout:
			gobject.source_remove(self.__timeout)
			self.p_context = None
			self.p_layout = None
    
	def __show_timeout (self):
		self.show()
    
	def screen_changed (self, window, screen=None):
		if screen == None:
			screen = window.get_screen()
		map = screen.get_rgba_colormap()
		if not map:
			map = screen.get_rgb_colormap()
		window.set_colormap(map)
    
	def expose (self, widget, event):
		ctx = self.window.window.cairo_create()
		ctx.set_antialias (cairo.ANTIALIAS_SUBPIXEL)    # ?
		# set a clip region for the expose event
		ctx.rectangle(event.area.x, event.area.y,event.area.width, event.area.height)
		ctx.clip()
		# clear context
		ctx.set_source_rgba(1, 1, 1, 0)
		ctx.set_operator (cairo.OPERATOR_SOURCE)
		ctx.paint()
		# draw rectangle
		self.gradient.add_color_stop_rgba(1,0.3, 0.3, 0.3, 0.9)
		self.gradient.add_color_stop_rgba(0.3, 0, 0, 0, 0.9)
		ctx.set_source(self.gradient)
		ctx.rectangle(0, 0, self.width, self.height)
		ctx.fill()
		# draw text
		ctx.save()
		ctx.translate(3, 3)
		ctx.set_source_rgba(1, 1, 1, 1) 
		ctx.show_layout(self.p_layout)
		ctx.fill()
		ctx.restore()
		ctx.rectangle(0, 0, self.width, self.height)
		ctx.set_source_rgba(0, 0, 0, 0.7)
		ctx.stroke()

# TEST (as the name implies)
"""class TestWidget(ShapedWidget):
	
	def __init__(self, width, height):
		#ShapedWidget.__init__(self, width, height)
		super(TestWidget, self).__init__(width, height)
	
	def draw(self, ctx):
		if self.mouse_inside:
			ctx.set_source_rgba(1, 0, 0, 0.8)
		else:
			ctx.set_source_rgba(1, 1, 0, 0.8)
		ctx.rectangle(0, 0, 32, 32)
		ctx.fill()
"""


# ------------------------------------------------------------------------------
# MODULE-FUNCTIONS
# ------------------------------------------------------------------------------

# the new recommended way of launching a screenlet from the "outside"
def launch_screenlet (name, debug=False):
	"""Launch a screenlet, either through its service or by launching a new
	process of the given screenlet. Name has to be the name of the Screenlet's
	class without trailing 'Screenlet'.
	NOTE: we could only launch the file here"""
	# check for service
	if services.service_is_running(name):
		# add screenlet through service, if running
		srvc = services.get_service_by_name(name)
		if srvc:
			try:
				srvc.add('')	# empty string for auto-creating ID
				return True
			except Exception, ex:
				print "Error while adding instance by service: %s" % ex
	# service not running or error? launch screenlet's file
	path = utils.find_first_screenlet_path(name)
	if path:
		# get full path of screenlet's file
		slfile = path + '/' + name + 'Screenlet.py'
		# launch screenlet as separate process
		print "Launching Screenlet from: %s" % slfile
		if debug:
			print "Logging output goes to: $HOME/.config/Screenlets/%sScreenlet.log" % name
			out = '$HOME/.config/Screenlets/%sScreenlet.log' % name
		else:
			out = '/dev/null'
		os.system('python -u %s > %s &' % (slfile, out))
		return True
	else:
		print "Screenlet '%s' could not be launched." % name
		return False

def show_message (screenlet, message, title=''):
	"""Show a message for the given Screenlet (may contain Pango-Markup).
	If screenlet is None, this function can be used by other objects as well."""
	if screenlet == None:
		md = gtk.MessageDialog(None, type=gtk.MESSAGE_INFO, 
			buttons=gtk.BUTTONS_OK)
		md.set_title(title)
	else:
		md = gtk.MessageDialog(screenlet.window, type=gtk.MESSAGE_INFO, 
			buttons=gtk.BUTTONS_OK)
		md.set_title(screenlet.__name__)
	md.set_markup(message)
	md.run()
	md.destroy()

def show_question (screenlet, message, title=''):
	"""Show a question for the given Screenlet (may contain Pango-Markup)."""
	if screenlet == None:
		md = gtk.MessageDialog(None, type=gtk.MESSAGE_QUESTION, 
			buttons=gtk.BUTTONS_YES_NO)
		md.set_title(title)
	else:
		md = gtk.MessageDialog(screenlet.window, type=gtk.MESSAGE_QUESTION, 
			buttons=gtk.BUTTONS_YES_NO)
		md.set_title(screenlet.__name__)
	md.set_markup(message)
	response = md.run()
	md.destroy()
	if response == gtk.RESPONSE_YES:
		return True
	return False

def show_error (screenlet, message, title='Error'):
	"""Show an error for the given Screenlet (may contain Pango-Markup)."""
	if screenlet == None:
		md = gtk.MessageDialog(None, type=gtk.MESSAGE_ERROR, 
			buttons=gtk.BUTTONS_OK)
		md.set_title(title)
	else:
		md = gtk.MessageDialog(screenlet.window, type=gtk.MESSAGE_ERROR, 
			buttons=gtk.BUTTONS_OK)
		md.set_title(screenlet.__name__)
	md.set_markup(message)
	md.run()
	md.destroy()

def fatal_error (message):
	"""Raise a fatal error to stdout and stderr and exit with an errorcode."""
	import sys
	msg = 'FATAL ERROR: %s\n' % message
	sys.stdout.write(msg)
	sys.stderr.write(msg)
	sys.exit(1)

# LEGACY support: functions that are not used any longer (raise fatal error)

def create_new_instance (name):
	fatal_error("This screenlet seems to be written for an older version of the framework. Please download a newer version of the %s." % name)
	

