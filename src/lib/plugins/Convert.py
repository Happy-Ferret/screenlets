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

# The base Converter class. Not to be used directly.
# For a commented example on how to write general converter modules, see the 
# file BaseConverter.py. But first, please, read below if a RatioConverter isn't 
# well suitable for your desired task.

class Converter(object):
	"""The base class for the converters. The converters look after maintaining 
	the list of currently shown values - initialising, accepting keyboard input, 
	etc.."""

	# the name of the class
	__name__ = 'Converter'
	# a short description to be used for selecting the converter
	__title__ = 'Base'

	# the number of fields shown on the display between 2 and 4
	num_fields = 0
	# field captions up to 4 chars long
	field_names = []
	# zero-based index of field having input focus
	active_field = 0
	# the list of currently shown 'values'. They should always be strings.
	values = []
	# replace: True = replace all the input by next keypress
	replace = True

	# initialize the list of values and fill it with defaults (strings!). 
	# Override this if you don't want then be '0's.
	def __init__(self):
		self.values = []
		for i in range(self.num_fields):
			self.values.append('0')
		self.active_field = 0
	
	def on_key_press(self, key):
		"""If accepted, appends the pressed key to the value in the currently 
		active field."""
		translate_dict = {'comma': '.', 'period': '.', 'Add': '+', 'plus': '+', 
				'Subtract': '-', 'minus': '-'}
		if key[:3] == 'KP_':
			key = key[3:]		# keys from numerical keypad come as digits
		if translate_dict.has_key(key):
			key = translate_dict[key]
		if key == 'BackSpace':	# try to guess :-)
			self.values[self.active_field] = self.values[self.active_field][:-1]
		elif key == 'Escape':	# clean the field
			self.values[self.active_field] = ''
		elif key == 'Down':		# move field focus
			if self.active_field < self.num_fields - 1:
				self.active_field += 1
				self.replace = True	# after a change, don't append next pressed 
				return True			# key but start over
			return False
		elif key == 'Up':
			if self.active_field > 0:
				self.active_field -= 1
				self.replace = True
				return True
			return False
		elif key == 'Tab':
			self.active_field += 1
			self.active_field %= self.num_fields
			self.replace = True
			return True
		else:		# leave other keys unchanged
			if not self.filter_key(key):
				return False
			if self.replace:
				self.values[self.active_field] = key
			# limit input length to 10 characters
			elif len(self.values[self.active_field]) < 10:
				self.values[self.active_field] = \
					self.values[self.active_field] + key
			self.replace = False
		self.neaten_input()
		self.convert()
		return True

	# You can use this function instead of str or fixed-width % - it leaves 
	# 3 digits after the decimal point for floats, and no decimal part if the 
	# number is integer.
	# Serves good if the same converter can be used for both ints ant floats,
	# so that the user doesn't get '1.000' when not necessary, also for showing
	# '0' instead of '0.000' in all cases.
	def str(self, val):
		if val == int(val):
			return str(int(val))
		else:
			return '%.3f' % val

	# Overridable functions:

	# neaten_input: see the docstring
	# Return value: none
	# If you don't want such function, override it in your converter with pass.
	# If you override it by something more complicated, be careful not to modify 
	# the current value so that it breaks the input.
	def neaten_input(self):
		"""Replaces an empty value with '0' and again removes leading '0' in 
		a non-empty string."""
		# This version is aware of the possibility of negative input values,
		# but you must allow + and - keys in filter_key and avoid an error when 
		# the input is '-'. See TemperatureConverter for an example.
		if self.values[self.active_field] == '' or \
				self.values[self.active_field][-1] == '+':
					self.values[self.active_field] = '0'
		elif self.values[self.active_field][-1] == '-':
			self.values[self.active_field] = '-'
		if len(self.values[self.active_field]) > 1 and \
				self.values[self.active_field][0] == '0':
			self.values[self.active_field] = self.values[self.active_field][1:]

	# filter_key: decides if pressed key can be appended to current value.
	# "key" is the GDK name of the key pressed by user
	# Return value: True - accept key, False - reject it.
	# There is no way to modify the value of key.
	# Be prepared for various "keys", e.g., 'apostrophe' must not match 'a'.
	def filter_key(self, key):
		"""Decides whether to accept pressed key."""
		return False

	# convert: actualizes field values to reflect input
	# Return value: none
	# Active value can be modified, but not so that it breaks the input.
	def convert(self):
		"""Recalculates field values after changes."""
		pass


# A subclass of Converter representing numerical converters whose field are 
# bound by a simple linear relation. It cares about float value input and output 
# and conversion, so the developer who wants to use it doesn't need to provide 
# any functions. Besides the __anything__, num_fields and field_names variables, 
# he must only provide a list describing desired ratios (see below).
# Not to be used directly. See LengthConverter for a commented example.

class RatioConverter(Converter):
	"""A base class of converters having linear dependances between their 
	fields."""

	__name__ = 'RatioConverter'
	__title__ = 'Base / Ratio'

	# The list of relative weights of the individual fields. The length of this 
	# list must be equal to num_fields. The ratio between two fields will be 
	# inverse to the ratio of corresponding entries in this list. For example, 
	# see LengthConverter. One may ask whether not to better use relative 
	# ratios, i.e., ratios between fields = ratio between entries, the answer is 
	# that this approach is more intuitive. You would set 1 for some unit and 
	# 1000 for the corresponding kilo-unit this way.
	# The above implies that the values in this list are relative to whichever 
	# one you would choose, e.g., [10, 5, 1] (will be converted to float) is 
	# equivalent to [2.0, 1.0, 0.2]. Actually, integer (exact) values are 
	# preferred if they reflect the logic of the conversion.
	weights = []

	def filter_key(self, key):
		# Accept digits
		if key.isdigit():
			return True
		# Also accept a decimal point if there is no one yet
		elif key == '.':
			return not ('.' in self.values[self.active_field])
		else:
			return False

	def convert(self):
		# A multiply-then-divide approach is used to help avoiding little
		# inaccuracies arising in operations like (3/10)*100.
		val = float(self.values[self.active_field]) \
				* self.weights[self.active_field]
		for i in range(self.num_fields):
			if i == self.active_field:
				continue
			self.values[i] = self.str(val / float(self.weights[i]))
	# Note: if you don't like the Converter.str() function used above which 
	# tries to always display integers as integers, you can provide your own, 
	# e.g., def str(self, val): return '%.3f' % val
