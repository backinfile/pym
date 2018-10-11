import re
from collections import namedtuple

show_tokens = False
show_steps = False
show_var = False
output_short = False

patterns = [
	#('\n',        r'(\n)'),

	('cmp',        r'(==)'),
	('cmp',        r'(!=)'),
	('cmp',        r'(>=)'),
	('cmp',        r'(<=)'),
	('cmp',        r'(>)'),
	('cmp',        r'(<)'),

	('int',        r'(\d+)'),
	('str',        r"'([^\n']*)'"),
	('str',        r'"([^\n"]*)"'),
	
	('or',        r'(\|\|)'),
	('or',        r'(\bor\b)'),
	('and',        r'(&&)'),
	('and',        r'(\band\b)'),
	
	('inc',        r'(\+\+)'),
	('dec',        r'(--)'),

	('assign',    r'(\+=)'),
	('assign',    r'(-=)'),
	('assign',    r'(\/=)'),
	('assign',    r'(\*=)'),
	('assign',    r'(=)'),

	('+',        r'(\+)'),
	('-',        r'(-)'),
	('*',        r'(\*)'),
	('/',        r'(\/)'),
	('not',        r'(!)'),
	('not',        r'\b(not)\b'),
	('print',    r'\b(print)\b'),

	(';',        r'(;)'),
	(':',        r'(:)'),
	(',',        r'(,)'),
	('.',        r'(\.)'),
	('(',        r'(\()'),
	(')',        r'(\))'),
	('[',        r'(\[)'),
	(']',        r'(\])'),
	('{',        r'(\{)'),
	('}',        r'(\})'),

	('if',        r'(\bif\b)'),
	('else',    r'(\belse\b)'),
	('for',        r'(\bfor\b)'),
	('while',    r'(\bwhile\b)'),
	('break',    r'(\bbreak\b)'),
	('continue',r'(\bcontinue\b)'),
	('return',    r'(\breturn\b)'),
	('function',r'(\bfunction\b)'),
	('True',    r'(\bTrue\b)'),
	('False',    r'(\bFalse\b)'),
	
	('name',    r'([A-Za-z_][\w_]*)'),
]

Token = namedtuple("Token", ["type", "value", "str"])
def _token_repr(self):
	return " {0:9} ==>  {1:8} ({2})".format(self.type, self.value.replace("\n", r"\n"), self.str.replace("\n", r"\n"))
Token.__repr__ = _token_repr
Step = namedtuple("Step", ["type", "value"])
def _step_repr(self):
	return " {0:14} ({2}){1:<12}".format(self.type, str(self.value).replace("\n", r"\n"), 
										 str(type(self.value)).replace("<type '","").replace("'>",""))
Step.__repr__ = _step_repr

def tokenize(buf):
	if type(buf) == "str":
		raise Exception("not a function")
	tokens = []
	i = 0
	l = len(buf)
	while i < l:
		prestr = ""
		while i < l and buf[i] in " \r\n\t":
			prestr += buf[i]
			i += 1
		if i >= l:
			break
		for t,p in patterns:
			m = re.match(p, buf[i:])
			if m:
				prestr += m.group(0)
				token = Token(t, m.group(1), prestr)
				tokens.append(token)
				i += len(m.group(0))
				if show_tokens:
					print(token)
				break
		else:
			raise Exception("not match any pattern-")
	return tokens

def stepize(tokens, isexpr=False):
	class Trans(object):
		def __init__(self, tokens):
			self.i = 0
			self.tokens = tokens
			self.l = len(tokens)
			self.steps = []
			self.continue_point = -1
			self.break_point = -1
		def pos(self):
			return len(self.steps)
		def type(self):
			if self.i >= self.l:
				return None
			return self.tokens[self.i].type
		def prestr(self):
			if self.i >= self.l:
				return ""
			return self.tokens[self.i].str
		def reset(self, pos, value):
			self.steps[pos] = Step(self.steps[pos].type, value)
		def value(self):
			if self.i >= self.l:
				return None
			return self.tokens[self.i].value
		def push(self, t, v=None):
			self.steps.append(Step(t,v))
		def match(self, p):
			if self.i >= self.l:
				raise Exception("unexceptable end")
			if self.tokens[self.i].type != p:
				raise Exception("should be "+p)
			self.i += 1
		def stmt(self):
			if self.type() == "print":
				self.i += 1
				while 1:
					if self.type() == ';':
						self.i += 1
						break
					self.expr5()
					if self.type() == ',':
						self.i += 1
					elif self.type() == ';':
						self.i += 1
						break
					else:
						raise Exception("not ok-")
				self.push("PRINT")
			elif self.type() == 'break':
				self.break_point = self.pos()
				self.push("JUMP")
				self.i += 1
				self.match(';')
			elif self.type() == 'continue':
				self.continue_point = self.pos()
				self.push("JUMP")
				self.i += 1
				self.match(';')
			elif self.type() == "return":
				self.i += 1
				if self.type() == ";":
					self.push("PUSH_CONST", None)
					self.i += 1
				else:
					self.expr5()
					self.match(';')
				self.push("RETURN")
			elif self.type() == 'function':
				self.i += 1
				name = ""
				if self.type() == 'name':
					self.push("PUSH_VAR",self.value())
					name = self.value()
					self.i += 1
				self.match('(')
				names = []
				while 1:
					if self.type() == 'name':
						names.append(self.value())
						self.i += 1
					else:
						self.match(')')
						break
					if self.type() == ',':
						self.i += 1
					elif self.type() == ')':
						self.i += 1
						break
					else:
						raise Exception("bad function")
				s = ''
				self.match('{')
				count = 1
				while 1:
					if self.type() == '{':
						count += 1
					elif self.type() == '}':
						count -= 1
						if count == 0:
							self.i += 1
							break
					s += self.prestr()
					self.i += 1
				self.push('PUSH_CONST', s)
				self.push('PUSH_CONST', names)
				self.push('MAKE_FUNCTION')
				if name:
					self.push("ASSIGN")
			elif self.type() == 'if':
				self.i += 1
				self.match('(')
				self.expr5()
				self.match(')')
				jump_pos = self.pos()
				self.push('JUMP_IF_FALSE')
				self.block()
				if self.type() == 'else':
					self.i += 1
					jump_back_pos = self.pos()
					self.push('JUMP')
					self.reset(jump_pos, self.pos())
					self.block()
					self.reset(jump_back_pos, self.pos())
				else:
					self.reset(jump_pos, self.pos())
			elif self.type() == 'while':
				self.i += 1
				self.match('(')
				jump_here = self.pos()
				self.expr5()
				self.match(')')
				jump_pos = self.pos()
				self.push('JUMP_IF_FALSE')
				self.block()
				self.push('JUMP', jump_here)
				self.reset(jump_pos, self.pos())
				if self.break_point != -1:
					self.reset(self.break_point, self.pos())
					self.break_point = -1
				if self.continue_point != -1:
					self.reset(self.continue_point, jump_here)
					self.continue_point = -1
			elif self.type() == "name":
				self.push("PUSH_VAR", self.value())
				name = self.value()
				self.i += 1
				if self.type() == ';':
					self.i += 1
				elif self.type() == 'assign':
					t = self.value()
					if t != '=':
						self.push("PUSH_VAR", name)
					self.i += 1
					if t == '=':
						self.expr5()
						self.push("ASSIGN")
					elif t == '+=':
						self.expr5()
						self.push("ADD")
						self.push("ASSIGN")
					elif t == '*=':
						self.expr5()
						self.push("MUL")
						self.push("ASSIGN")
					elif t == '-=':
						self.expr5()
						self.push("SUB")
						self.push("ASSIGN")
					elif t == '/=':
						self.expr5()
						self.push("DIV")
						self.push("ASSIGN")
					else:
						raise Exception("bad assign")
					self.match(';')
				elif self.type() == "inc":
					self.i += 1
					self.push("INC")
					self.match(';')
				elif self.type() == "dec":
					self.i += 1
					self.push("DEC")
					self.match(';')
				else:
					self.name_tail()
					self.match(';')
					self.push("POP_ALL")
			else:
				self.expr5()
				self.push("POP_ALL")
				self.match(';')
		def expr(self):
			if self.type() == "int":
				self.push("PUSH_CONST", int(self.value()))
				self.i += 1
			elif self.type() == "False":
				self.push("PUSH_CONST", False)
				self.i += 1
			elif self.type() == "True":
				self.push("PUSH_CONST", True)
				self.i += 1
			elif self.type() == "not":
				self.i += 1
				self.expr()
				self.push("NOT")
			elif self.type() == "-":
				self.i += 1
				self.expr()
				self.push("NEG")
			elif self.type() == "str":
				self.push("PUSH_CONST", str(self.value()))
				self.i += 1
			elif self.type() == "name":
				self.push("PUSH_VAR", self.value())
				self.i += 1
			elif self.type() == '(':
				self.i += 1
				self.expr5()
				self.match(")")
			elif self.type() == '[':
				self.i += 1
				count = 0
				while self.type() != ']':
					self.expr5()
					count += 1
					if self.type() == ']':
						break
					self.match(',')
				self.match(']')
				self.push("BUILD_LIST", count)
			elif self.type() == '{':
				self.i += 1
				count = 0
				while self.type() != '}':
					self.expr5()
					self.match(':')
					self.expr5()
					count += 1
					if self.type() == '}':
						break
					self.match(',')
				self.match('}')
				self.push("BUILD_MAP", count)
			elif self.type() == 'function':
				self.i += 1
				name = ""
				if self.type() == 'name':
					name = self.value()
					self.push("PUSH_VAR", name)
					self.i += 1
				self.match('(')
				names = []
				while 1:
					if self.type() == 'name':
						names.append(self.value())
						self.i += 1
					else:
						self.match(')')
						break
					if self.type() == ',':
						self.i += 1
					elif self.type() == ')':
						self.i += 1
						break
					else:
						raise Exception("bad function")
				s = ''
				self.match('{')
				count = 1
				while 1:
					if self.type() == '{':
						count += 1
					elif self.type() == '}':
						count -= 1
						if count == 0:
							self.i += 1
							break
					s += self.prestr()
					self.i += 1
				self.push('PUSH_CONST', s)
				self.push('PUSH_CONST', names)
				self.push('MAKE_FUNCTION')
				if name:
					self.push('ASSIGN')
			self.name_tail()
		def name_tail(self):
			while True:
				if self.type() == "(":
					self.i += 1
					count = 0
					while 1:
						if self.type() == ")":
							self.i += 1
							break
						self.expr5()
						count += 1
						if self.type() == ",":
							self.i += 1
						elif self.type() == ")":
							self.i += 1
							break
						else:
							raise Exception("not ok")
					self.push("CALL", count)
				elif self.type() == '[':
					self.i += 1
					self.expr5()
					self.match(']')
					self.push("GET_ITEM")
				elif self.type() == '.':
					self.i += 1
					if self.type() != 'name':
						raise Exception("need a name")
					self.push("PUSH_CONST", self.value())
					self.i += 1
					self.push("GET_METHOD")
				elif self.type() == "inc":
					self.i += 1
					self.push("INC")
				else:
					break
		def expr1(self):
			self.expr()
			while self.type() == '*' or self.type() == '/':
				t = self.type()
				self.i += 1
				self.expr()
				if t == "*":
					self.push("MUL")
				else:
					self.push("DIV")
		def expr2(self):
			self.expr1()
			while self.type() == '+' or self.type() == '-':
				t = self.type()
				self.i += 1
				self.expr1()
				if t == "+":
					self.push("ADD")
				else:
					self.push("SUB")
		def expr3(self):
			self.expr2()
			while self.type() == "cmp":
				t = self.value()
				self.i += 1
				self.expr2()
				if t == ">=":
					self.push("GE")
				elif t == "<=":
					self.push("LE")
				elif t == "<":
					self.push("LT")
				elif t == ">":
					self.push("GT")
				elif t == "==":
					self.push("EQ")
				else:
					self.push("NE")
		def expr4(self):
			self.expr3()
			while self.type() == 'or' or self.type() == 'and':
				t = self.type()
				self.i += 1
				self.expr3()
				if t == "or":
					self.push("OR")
				else:
					self.push("AND")
		def expr5(self):
			self.expr4()
		def block(self):
			if self.type() == '{':
				self.i += 1
				while self.type() != '}':
					self.stmt()
				self.i += 1
			else:
				self.stmt()
		def eval(self):
			while self.i < self.l:
				self.stmt()
	t = Trans(tokens)
	if isexpr:
		t.expr();
	else:
		t.eval();
	return t.steps

class Auto(object):
	def __init__(self,value=None,belongto=None,argnames=None,name=None,buildin=None):
		self.value = value
		self.belongto = belongto
		self.argnames = argnames or []
		self.buildin = buildin
		self.steps = []
		if name:
			self.namespace = {'self':self, '__name__':Auto(name)}
		else:
			self.namespace = {'self':self}
	def __str__(self):
		s = str(self.value).replace("\n",r"\n")
		if output_short and len(s)>15:
			return s[:10]+'...'
		return s
	def __repr__(self):
		s = str(self.value).replace("\n",r"\n")
		if output_short and len(s)>15:
			return "Auto("+s[:10]+'...'+")"
		return "Auto("+s+")"
	def call(self, args=None):
		if self.buildin != None:
			return self.buildin(args)
		self.stack = []
		if not isinstance(self.value, str):
			raise Exception("uncallable")
		if args:
			for x,y in zip(self.argnames,args):
				y.belongto = self
				y.namespace['__name__'] = Auto(x)
				self.namespace[x] = y
		if not self.steps:
			funcname = self.namespace.get('__name__')
			if not funcname:
				funcname = ''
			else:
				funcname = str(funcname.value)
			if show_tokens:
				print "\n[TOKENIZE "+funcname+"]"
			tokens = tokenize(self.value)
			if show_steps:
				print "\n[STEPIZE "+funcname+"]"
			stepstmp = stepize(tokens)
			if show_steps:
				for i,x in enumerate(stepstmp):
					print " {0:3}".format(i),x
			self.steps = stepstmp
		
		# run steps
		if show_var:
			print "\n[CALL "+funcname+"]"
		self.l = len(self.steps)
		self.i = 0 # for step_once
		while self.i < self.l:
			self.step_once()
		if show_var:
			print "[END "+funcname+"]\n"
		if self.stack:
			return self.stack[0]
		else:
			return Auto(None)
	def step_once(self):
		t = self.steps[self.i]
		if show_var:
			print self.i,":",t
		self.i += 1
		if t.type == "PUSH_VAR":
			a = self.namespace.get(t.value)
			b = self.belongto
			
			while a == None and b != None:
				a = b.namespace.get(t.value, None)
				b = b.belongto
			if a == None:
				a = Auto(None)
				a.namespace['__name__'] = Auto(t.value)
				a.belongto = self
			self.stack.append(a)
		elif t.type == "ASSIGN":
			a = self.stack.pop()
			b = self.stack.pop()
			name = b.namespace['__name__']
			if b.belongto != None:
				a.namespace['__name__'] = name
				a.belongto = b.belongto
				b.belongto.namespace[name.value] = a
			else:
				a.namespace['__name__'] = name
				a.belongto = self
				self.namespace[name.value] = a
		elif t.type == "PUSH_CONST":
			self.stack.append(Auto(t.value))
		elif t.type == "POP_ALL":
			self.stack = []
		elif t.type == "GE":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value >= a.value))
		elif t.type == "GT":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value > a.value))
		elif t.type == "LE":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value <= a.value))
		elif t.type == "LT":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value < a.value))
		elif t.type == "EQ":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value == a.value))
		elif t.type == "NE":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value != a.value))
		elif t.type == "ADD":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value + a.value))
		elif t.type == "SUB":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value - a.value))
		elif t.type == "MUL":
			b = self.stack.pop()
			a = self.stack.pop()
			self.stack.append(Auto(b.value * a.value))
		elif t.type == "DIV":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value / a.value))
		elif t.type == "AND":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value and a.value))
		elif t.type == "OR":
			a = self.stack.pop()
			b = self.stack.pop()
			self.stack.append(Auto(b.value or a.value))
		elif t.type == "NOT":
			a = self.stack.pop()
			self.stack.append(Auto(not a.value))
		elif t.type == "NEG":
			a = self.stack.pop()
			if isinstance(a.value, str):
				self.stack.append(Auto(a.value[::-1]))
			else:
				self.stack.append(Auto(-a.value))
		elif t.type == "JUMP_IF_FALSE":
			a = self.stack.pop()
			if not a.value:
				self.i =  int(t.value)
		elif t.type == "JUMP":
			self.i = int(t.value)
		elif t.type == "PRINT":
			for x in self.stack:
				print x,
			print
			self.stack = []
		elif t.type == "GET_METHOD":
			a = self.stack.pop()
			b = self.stack.pop()
			c = b.namespace.get(a.value,Auto(None))
			c.belongto = b
			self.stack.append(c)
		elif t.type == "CALL":
			args = self.stack[-t.value:]
			for x in range(t.value):
				self.stack.pop()
			a = self.stack.pop()
			self.stack.append(a.call(args))
		elif t.type == "RETURN":
			a = self.stack.pop()
			self.stack = [a]
			self.i = self.l
		elif t.type == "MAKE_FUNCTION":
			a = self.stack.pop()
			b = self.stack.pop()
			if isinstance(b.value, str) and isinstance(a.value, list):
				self.stack.append(Auto(b.value,argnames=a.value))
			else:
				self.stack.append(Auto(None))
		elif t.type == 'BUILD_LIST':
			l = self.stack[-t.value:]
			for x in range(t.value):
				self.stack.pop()
			self.stack.append(Auto(l))
		elif t.type == 'BUILD_MAP':
			m = {}
			for x in range(t.value):
				v = self.stack.pop()
				i = self.stack.pop()
				m[i.value] = v
			self.stack.append(Auto(m))
		elif t.type == 'GET_ITEM':
			a = self.stack.pop()
			b = self.stack.pop()
			if isinstance(a.value, int) and isinstance(b.value, list):
				if a.value < len(b.value):
					c = b.value[a.value]
				else:
					c = Auto(None)
			elif isinstance(a.value, int) and isinstance(b.value, str):
				if a.value < len(b.value):
					c = Auto(b.value[a.value])
				else:
					c = Auto(None)
			elif isinstance(a.value, str) and isinstance(b.value, dict):
				c = b.value.get(a.value,Auto(None))
			else:
				raise Exception("error in getitem")
			c.belongto = b
			self.stack.append(c)
		else:
			raise Exception('canot step '+t.type)
		if show_var:
			print " "*40,self.stack
			print " "*40,self.namespace
	def func_register(self,name,func):
		self.namespace[name] = Auto("<buildin-function "+name+'>',
									buildin=func, name=name)

def function_str(args):
	return Auto(str(args[0]))
def function_int(args):
	return Auto(int(args[0]))
def function_len(args):
	return Auto(len(args[0].value))

if __name__ == '__main__':
	a = Auto(None, name='__main__')
	print 'Pym 1.2(10/11 2018)'
	while 1:
		print '\n>>>',
		try:
			a.value = raw_input()
			a.steps = []
			a.call()
		except Exception, e:
			try:
				a.steps = tokenize(a.value)
				a.steps = stepize(a.steps, True)
				res = a.call()
				print '[result]', res
			except Exception:
				print '[Error]',e
		
	
