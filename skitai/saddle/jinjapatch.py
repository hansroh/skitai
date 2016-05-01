from jinja2 import environment
from jinja2 import lexer as olexer
from jinja2 import parser
from jinja2 import nodes
import re


# patch for enabling line_statement_prefix raw
from jinja2.lexer import TOKEN_DATA, TOKEN_RAW_END, Failure, \
	TOKEN_WHITESPACE, TOKEN_FLOAT, TOKEN_INTEGER, TOKEN_NAME, TOKEN_STRING, TOKEN_OPERATOR, \
	whitespace_re, float_re, integer_re, name_re, string_re, operator_re, compile_rules


def get_lexer (environment):
	c = lambda x: re.compile(x, re.M | re.S)
	e = re.escape
	tag_rules = [
	    (whitespace_re, TOKEN_WHITESPACE, None),
	    (float_re, TOKEN_FLOAT, None),
	    (integer_re, TOKEN_INTEGER, None),
	    (name_re, TOKEN_NAME, None),
	    (string_re, TOKEN_STRING, None),
	    (operator_re, TOKEN_OPERATOR, None)
	]	
	root_tag_rules = compile_rules(environment)
	block_suffix_re = environment.trim_blocks and '\\n?' or ''
	block_prefix_re = '%s' % e(environment.block_start_string)
	prefix_re = {}
	
	if environment.lstrip_blocks:
		no_lstrip_re = e('+')
		block_diff = c(r'^%s(.*)' % e(environment.block_start_string))
		m = block_diff.match(environment.comment_start_string)
		no_lstrip_re += m and r'|%s' % e(m.group(1)) or ''
		m = block_diff.match(environment.variable_start_string)
		no_lstrip_re += m and r'|%s' % e(m.group(1)) or ''
		
		comment_diff = c(r'^%s(.*)' % e(environment.comment_start_string))
		m = comment_diff.match(environment.variable_start_string)
		no_variable_re = m and r'(?!%s)' % e(m.group(1)) or ''
		
		lstrip_re = r'^[ \t]*'
		block_prefix_re = r'%s%s(?!%s)|%s\+?' % (
		        lstrip_re,
		        e(environment.block_start_string),
		        no_lstrip_re,
		        e(environment.block_start_string),
		        )
		comment_prefix_re = r'%s%s%s|%s\+?' % (
		        lstrip_re,
		        e(environment.comment_start_string),
		        no_variable_re,
		        e(environment.comment_start_string),
		        )
		prefix_re['block'] = block_prefix_re
		prefix_re['comment'] = comment_prefix_re
		
	else:
		block_prefix_re = '%s' % e(environment.block_start_string)

	lexer = olexer.get_lexer(environment)
	lexer.rules['root'] = [
			# directives
			(c('(.*?)(?:%s)' % '|'.join(
				[r'(?P<raw_begin>(?:\s*%s\-|%s|^[ \t\v]*%s)\s*raw\s*(?:\-%s\s*|%s|\s*:?\s*))' % (
					e(environment.block_start_string),
					block_prefix_re,
					e(environment.line_statement_prefix),
					e(environment.block_end_string),
					e(environment.block_end_string)
				)] + [
					r'(?P<%s_begin>\s*%s\-|%s)' % (n, r, prefix_re.get(n,r))
					for n, r in root_tag_rules
				])), (TOKEN_DATA, '#bygroup'), '#bygroup'),
			# data
			(c('.+'), TOKEN_DATA, None)
		]
	
	lexer.rules [olexer.TOKEN_RAW_BEGIN] = [
			(c('(.*?)((?:\s*%s\-|%s|^[ \t\v]*%s)\s*endraw\s*(?:\-%s\s*|%s%s|$))' % (
				e(environment.block_start_string),
				block_prefix_re,
				e(environment.line_statement_prefix),
				e(environment.block_end_string),
				e(environment.block_end_string),
				block_suffix_re
			)), (TOKEN_DATA, TOKEN_RAW_END), '#pop'),
			(c('(.)'), (Failure('Missing end of raw directive'),), None)
		]		
	return lexer
	
	
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
	lexer = property(get_lexer, doc="The lexer for this environment.")

# enable 'raw' line statement
environment.Environment = property(get_lexer, doc="The lexer for this environment.")
