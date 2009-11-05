###
# Copyright (c) 2009, Juju, Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer. 
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author of this software nor the names of
#       the contributors to the software may be used to endorse or
#       promote products derived from this software without specific
#       prior written permission. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 
###

import os
import re
import textwrap
from OrderedDict import OrderedDict
from optparse import OptionParser, OptionValueError

class InvalidSyntax(Exception):
    def __init__(self, lineno, msg):
        self.lineno = lineno
        self.msg = msg

    def __str__(self):
        return '%s (on line %s)' % (self.msg, self.lineno)


class MissingName(InvalidSyntax):
    def __init__(self, lineno):
        InvalidSyntax.__init__(self, lineno, 'Could not find variable name')


class UnregisteredName(InvalidSyntax):
    def __init__(self, lineno, name):
        InvalidSyntax.__init__(self, lineno, 'Unregistered name: %r' % name)


class GroupExpectsNoValue(InvalidSyntax):
    def __init__(self, lineno, name):
        InvalidSyntax.__init__(self, lineno, 'Group expects no value: %r' % name)


def wrap(comment):
    return textwrap.wrap(' '.join(comment.split()))

def writeComment(fp, comment):
    for line in wrap(comment):
        fp.write('# %s\n' % line)
    
def OptparseCallback(option, optString, valueString, parser, Value):
    try:
        Value.setFromString(valueString)
    except ValueError, e:
        raise OptionValueError('%s option expected %s, received %r (%s)' %
                               (optString, Value.type(), valueString, e))
        

class Group(object):
    """All configuration variables are groups, that is, all configuration variables can have other groups and variables registered under them.  Experience (from the very similar configuration in Supybot) has shown that making non-group variables is simply not worth the trouble and inconsistency."""
    def __init__(self, name, comment=None, Child=None):
        """
        @param name: The name for this group.  An argument could be made for making the group itself name-agnostic and only giving it a name upon registration with another group, but that would cripple unregistered groups.

        @param comment: A helpful comment indicating the usage/meaning of a particular group.  This comment will be written to configuration files and used as the help text of the optparse OptionParser the group can generate.

        @param Child: A callable (usually a class) which, if not None, will be used in the get() method to create a requested child rather than raising KeyError.
        """
        # All of these are prefixed with underscores so they won't conflict with
        # registered children.
        if name.startswith('_'):
            raise ValueError('Names beginning with an underscore are forbidden: %r'%name)
        self._name = name
        self._parent = None
        self._Child = Child
        self._comment = comment
        self._children = OrderedDict()

    def get(self, name):
        """Returns the child variable with the given name.  If no such variable exists and the Child argument was given to __init__, a new variable will be created and returned.

        @param name: The name of the child to retrieve.
        """
        try:
            return self._children[name]
        except KeyError:
            if self._Child is not None:
                child = self._Child(name)
                self.register(child)
                return child
            else:
                raise
    
    def __getattr__(self, name):
        if name.startswith('_'):
            return object.__getattr__(self, name)
        try:
            return self.get(name)
        except KeyError:
            raise AttributeError(name)

    def __call__(self):
        # Having this here offers a better exception/error message than __getattr__'s
        # AttributeError.
        raise GroupExpectsNoValue(self._fullname())

    def register(self, child):
        """Registers the given child with this group.  Any previously-registered children
        with the same name are replaced.

        @param child: The child to register.
        """
        self._children[child._name] = child
        child._parent = self
        return child

    def _fullname(self, parentName=None, childName=None):
        if childName is None:
            childName = self._name
        if parentName is None and self._parent is not None:
            parentName = self._parent._fullname()
        if not parentName:
            return childName
        else:
            return '%s.%s' % (parentName, childName)
        
    def writefp(self, fp, annotate=True, parentName=None):
        """Writes this configuration group and its children in their current state to the given file(-like) object. 

        @param fp: The file(-like) object to write.
        @param annotate: Flag determining whether to write comments to the given file object.  Default values are still written, but commented out.
        @param parentName: The name of the parent to prefix to this group's own name and the name of its children.
        """
        if self._comment and annotate:
            writeComment(fp, self._comment)
            fp.write('\n')
        myname = self._fullname(parentName)
        for child in self.children():
            child.writefp(fp, annotate=annotate, parentName=myname)

    _sepRe = re.compile(r'\s*[:=]\s*')
    def readfp(self, fp):
        """Reads the given file object, setting the state of this configuration group and its children appropriately.  Comment lines and blank lines are ignored; comment lines are those which begin (apart from leading whitespace) with a '#' character.  Comments cannot be initiated part way through a line: e.g., a line 'foo: bar # baz' gives the 'foo' configuration variable the literal value 'bar # baz'.  Non-comment lines consist of a configuration variable name followed by optional whitespace, a separator of ':' or '=', more optional whitespace, and finally the value of that variable in string form."""
        lineno = 0
        for line in fp:
            lineno += 1
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                (name, value) = self._sepRe.split(line, 1)
            except ValueError:
                raise MissingName(lineno)
            value = value.strip()
            parts = name.split('.')
            if parts.pop(0) != self._name:
                raise UnregisteredName(lineno, name)
            group = self
            for part in parts:
                try:
                    group = group.get(part)
                except KeyError:
                    raise UnregisteredName(lineno, name)
            if not group.expectsValue():
                raise GroupExpectsNoValue(lineno, name)
            group.setFromString(value)

    def read(self, filename):
        """Calls readfp with a file object opened with the given name."""
        fp = open(filename)
        try:
            self.readfp(fp)
        finally:
            fp.close()

    def readenv(self, environ=None):
        """Reads the given environment dictionary, setting the state of this configuration group and its children appropriately.  Unrecognized env variable names are ignored.  Environment variables are expected to be capitalized, parts separated by underscores.  For instance, if you would access the configuration variable via 'foo.bar.baz' in Python, the environment variable expected would be FOO_BAR_BAZ.

        @param environ: The environment dictionary.  Defaults to os.environ.
        @type environ: dict
        """
        if environ is None:
            environ = os.environ
        for (name, variable) in self:
            if not variable.expectsValue():
                continue
            envName = name.replace('.', '_').upper()
            try:
                variable.setFromString(environ[envName])
            except KeyError:
                continue
            except ValueError, e:
                raise ValueError('Invalid environment variable %s: %s' % (envName, e))
        
    def __iter__(self):
        """Generates a series of (fullname, configuration variable) pairs for this Group
        and its children."""
        yield (self._name, self)
        for child in self.children():
            for (childname, grandchild) in child:
                yield (self._fullname(self._name, childname), grandchild)

    def toOptionParser(self, parser=None, **kwargs):
        """Modifies or produces an optparse.OptionParser which will set the appropriate variables in this configuration tree when certain options are given.  Options are converted to lowercase and separated by dashes, in accordance with the common practice for long options in *nix.  For instance, if you would access the configuration variable via 'foo.bar.baz' in Python, the command line option associated with that variable would be --foo-bar-baz."""
        if parser is None:
            parser = OptionParser(**kwargs)
        for (name, variable) in self:
            if not variable.expectsValue():
                continue
            optionName = name.replace('.', '-').lower()
            parser.add_option('', '--' + optionName, action="callback",
                              type="string", callback=OptparseCallback,
                              metavar=variable.type().upper(), help=variable._comment,
                              callback_args=(variable,))
        return parser
                              
    def children(self):
        return self._children.values()

    def expectsValue(self):
        return False


parent = object()
class Value(Group):
    def __init__(self, name, default=None, **kwargs):
        Group.__init__(self, name, **kwargs)
        self._value = None
        self._default = default

    @property
    def default(self):
        if callable(self._default):
            return self._default()
        elif self._default is parent:
            return self._parent()
        else:
            return self._default

    def __call__(self):
        if self._value is None:
            return self.default
        else:
            return self._value

    @classmethod
    def type(cls):
        if cls is Value:
            return 'string'
        else:
            return cls.__name__.lower()

    def set(self, v):
        self._value = v

    def setFromString(self, s):
        self.set(self.fromString(s))

    def fromString(self, s):
        return s

    def toString(self, v):
        return str(v)

    def __str__(self):
        return self.toString(self())

    def writefp(self, fp, annotate=True, parentName=None):
        myname = self._fullname(parentName)
        if self._comment is not None and annotate:
            writeComment(fp, self._comment)
        if self._value is None:
            fp.write('# ') # Document the default value, but comment it out.
        if self() is None:
            stringValue = '(no default)'
        else:
            stringValue = str(self)
        fp.write('%s: %s\n' % (myname, stringValue))
        if annotate:
            fp.write('\n') # Extra newline makes comments more easily distinguishable.
        for child in self.children():
            child.writefp(fp, annotate=annotate, parentName=myname)

    def expectsValue(self):
        return True

    def isSet(self):
        return self._value is not None or self.default is not None

    def isDefault(self):
        return self._value is None

    def reset(self):
        self._value = None
    

class Bool(Value):
    def fromString(self, s):
        if s.lower() in ['true', 'on', '1', 'yes']:
            return True
        elif s.lower() in ['false', 'off', '0', 'no']:
            return False
        else:
            raise ValueError('%r cannot be converted to bool' % s)


class Int(Value):
    def fromString(self, s):
        if s.startswith('0x'):
            return int(s[2:], 16)
        elif s.startswith('0'):
            return int(s, 8)
        else:
            return int(s)


class Float(Value):
    fromString = float
