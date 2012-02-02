import sublime, sublime_plugin
import os, string, re

plugin_directory = os.getcwd()

class DetectSyntaxCommand(sublime_plugin.EventListener):
	def __init__(self):
		super(DetectSyntaxCommand, self).__init__()
		self.first_line = None
		self.file_name = None
		self.view = None
		self.syntaxes = []
		self.plugin_name = 'DetectSyntax'
		# self.plugin_dir = sublime.packages_path() + os.path.sep + self.plugin_name
		self.plugin_dir = plugin_directory
		self.user_dir = sublime.packages_path() + os.path.sep + 'User'
		self.reraise_exceptions = False


	def on_load(self, view):
		self.detect_syntax(view)

	
	def on_post_save(self, view):
		self.detect_syntax(view)
	  

	def detect_syntax(self, view):
		if view.is_scratch() or not view.file_name: # buffer has never been saved
			return

		self.reset_cache_variables(view)
		self.load_syntaxes()
		
		if not self.syntaxes:
			return

		for syntax in self.syntaxes:
			# stop on the first syntax that matches
			if self.syntax_matches(syntax):
				self.set_syntax(syntax)
				break


	def reset_cache_variables(self, view):
		self.view = view
		self.file_name = view.file_name()
		self.first_line = view.substr(view.line(0))
		self.syntaxes = []
		self.reraise_exceptions = False


	def set_syntax(self, syntax):
		name = syntax.get("name")

		# the default settings file uses / to separate the syntax name parts, but if the user
		# is on windows, that might not work right. And if the user happens to be on Mac/Linux but
		# is using rules that were written on windows, the same thing will happen. So let's
		# be intelligent about this and replace / and \ with os.path.sep to get to
		# a reasonable starting point
		name = name.replace('/', os.path.sep)
		name = name.replace('\\', os.path.sep)

		dirs = name.split(os.path.sep)
		name = dirs.pop()
		path = os.path.sep.join(dirs)

		if not path:
			path = name
	 
		new_syntax = 'Packages/' + path + '/' + name + '.tmLanguage'
		current_syntax = self.view.settings().get('syntax')

		# only set the syntax if it's different
		if new_syntax != current_syntax:
			self.view.set_syntax_file(new_syntax)


	def load_syntaxes(self):
		settings = sublime.load_settings(self.plugin_name + '.sublime-settings')
		self.reraise_exceptions = settings.get("reraise_exceptions")
		self.syntaxes = settings.get("syntaxes")


	def syntax_matches(self, syntax):
		rules = syntax.get("rules")

		for rule in rules:
			if 'function' in rule:
				result = self.function_matches(rule)
			else:
				result = self.regexp_matches(rule)

			# return on first match. don't return if it doesn't
			# match or else the remaining rules won't be applied
			if result:
				return True

		return False # there are no rules or none match


	def function_matches(self, rule):
		function = rule.get("function")
		path_to_file = function.get("source")
		function_name = function.get("name")

		if not path_to_file:
			path_to_file = function_name + '.py'

		# is path_to_file absolute?
		if not os.path.isabs(path_to_file):
			# it's not, so look in Packages/User
			if os.path.exists(self.user_dir + os.path.sep + path_to_file):
				path_to_file = self.user_dir + os.path.sep + path_to_file
			else:
				# now look in the plugin's directory
				path_to_file = self.plugin_dir + os.path.sep + path_to_file

		# bubble exceptions up only if the user wants them
		try:
			with open(path_to_file, 'r') as the_file:
				function_source = the_file.read()
		except:
			if self.reraise_exceptions:
				raise
			else:
				return False

		try:
			exec(function_source)
		except:
			if self.reraise_exceptions:
				raise
			else:
				return False

		try:
			return eval(function_name + '(\'' + self.file_name + '\')')
		except:
			if self.reraise_exceptions:
				raise
			else:
				return False


	def regexp_matches(self, rule):
		if "first_line" in rule:
			subject = self.first_line
			regexp = rule.get("first_line")
		elif "file_name" in rule:
			subject = self.file_name
			regexp = rule.get("file_name")
		else:
			return False

		if regexp and subject:
			return re.match(regexp, subject) != None
		else:
			return False

