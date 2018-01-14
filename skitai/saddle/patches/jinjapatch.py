from jinja2 import environment
from jinja2 import parser
from jinja2 import nodes
from jinja2 import PackageLoader, ChoiceLoader, FileSystemLoader
import os
	
class Parser (parser.Parser):			
	def subparse(self, end_tokens=None):
		body = []
		data_buffer = []
		add_data = data_buffer.append

		if end_tokens is not None:
			self._end_token_stack.append(end_tokens)

		def flush_data():
			if data_buffer:
				lineno = data_buffer[0].lineno
				body.append(nodes.Output(data_buffer[:], lineno=lineno))
				del data_buffer[:]

		try:
			while self.stream:
				token = self.stream.current
				if token.type == 'data':
					if token.value:
						add_data(nodes.TemplateData(token.value,
													lineno=token.lineno))
					next(self.stream)
				elif token.type == 'variable_begin':
					next(self.stream)
					# added by Hans Roh 2016.5.1
					# If variable_begin & variable_end is #,
					# should excape by #"#"#
					# this patch make it easy to ##
					if self.stream.current.type == "variable_end":
						add_data(nodes.TemplateData(token.value, lineno=token.lineno))
						next(self.stream)
					else:	
						add_data(self.parse_tuple(with_condexpr=True))
						self.stream.expect('variable_end')
				elif token.type == 'block_begin':
					flush_data()
					next(self.stream)
					if end_tokens is not None and \
					   self.stream.current.test_any(*end_tokens):
						return body
					rv = self.parse_statement()
					if isinstance(rv, list):
						body.extend(rv)
					else:
						body.append(rv)
					self.stream.expect('block_end')
				else:
					raise AssertionError('internal parsing error')

			flush_data()
		finally:
			if end_tokens is not None:
				self._end_token_stack.pop()

		return body


class Environment (environment.Environment):
	def _parse(self, source, name, filename):
		return Parser(self, source, name, environment.encode_filename(filename)).parse()

def overlay (
	app_name, 
	variable_start_string = "{{", 
	variable_end_string = "}}",
	block_start_string = "{%", 
	block_end_string = "%}", 
	comment_start_string = "{#",
	comment_end_string = "#}",
	line_statement_prefix = "%", 
	line_comment_prefix = "%%",
	**karg
	):
	
	if len (variable_start_string) == 1 and len (variable_end_string) == 1:
		env_class = Environment
	else:	
		env_class = environment.Environment
	
	return env_class (
		loader = PackageLoader (app_name),
		variable_start_string=variable_start_string,
		variable_end_string=variable_end_string,	  
		block_end_string = block_end_string,
		block_start_string = block_start_string,
		comment_start_string = comment_start_string,
		comment_end_string = comment_end_string,	  
		line_statement_prefix = line_statement_prefix,
		line_comment_prefix = line_comment_prefix,
		trim_blocks = True,
		lstrip_blocks = True,
		**karg
	)
