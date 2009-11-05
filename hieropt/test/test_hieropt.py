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

import copy
from cStringIO import StringIO as sio

import hieropt
from hieropt.test import *

def makeSimple():
    simple = hieropt.Group('simple')
    simple.register(hieropt.Int('int'))
    simple.register(hieropt.Bool('bool'))
    simple.register(hieropt.Float('float'))
    return simple

def makeSimpleWithDefaults():
    simple = hieropt.Group('simple')
    simple.register(hieropt.Int('int', 1))
    simple.register(hieropt.Bool('bool', True))
    simple.register(hieropt.Float('float', 1.0))
    return simple

def makeSimpleWithComments():
    simple = hieropt.Group('simple', comment='simple group')
    simple.register(hieropt.Int('int', comment='simple int'))
    simple.register(hieropt.Bool('bool', comment='simple bool'))
    simple.register(hieropt.Float('float', comment='simple float'))
    return simple
    
def makeSimpleWithDefaultsAndComments():
    simple = hieropt.Group('simple', comment='simple group')
    simple.register(hieropt.Int('int', 1, comment='simple int'))
    simple.register(hieropt.Bool('bool', True, comment='simple bool'))
    simple.register(hieropt.Float('float', 1.0, comment='simple float'))
    return simple

def assert_write_then_read_equivalence(config):
    fp = sio()
    config.writefp(fp)
    initial = fp.getvalue()
    initial_defaults = [(name, value.expectsValue() and
                               value.isSet() and
                               value.isDefault())
                        for (name, value) in config]
    fp.seek(0)
    config.readfp(fp)
    fp.seek(0)
    config.writefp(fp)
    subsequent = fp.getvalue()
    subsequent_defaults = [(name, value.expectsValue() and
                                  value.isSet() and
                                  value.isDefault())
                           for (name, value) in config]
    assert_equals(initial, subsequent)
    assert_equals(initial_defaults, subsequent_defaults)
    
def test_simple_basic_read_write():
    for simple in [makeSimple(), makeSimpleWithDefaults(),
                   makeSimpleWithComments(), makeSimpleWithDefaultsAndComments()]:
        assert_write_then_read_equivalence(simple)
        simple.int.set(2)
        assert_write_then_read_equivalence(simple)
        simple.bool.set(False)
        assert_write_then_read_equivalence(simple)
        simple.float.set(0.1)
        assert_write_then_read_equivalence(simple)

def test_simple_int():
    simple = makeSimple()
    simple.int.set(1)
    assert_equals(simple.int(), 1)
    simple.int.set(0)
    assert_equals(simple.int(), 0)
    simple.int.set(-1)
    assert_equals(simple.int(), -1)
    simple.int.setFromString('1')
    assert_equals(simple.int(), 1)
    simple.int.setFromString('-1')
    assert_equals(simple.int(), -1)
    simple.int.setFromString('0xFF')
    assert_equals(simple.int(), 255)
    simple.int.setFromString('0777')
    assert_equals(simple.int(), 7*1 + 7*8 + 7*64)
    assert_write_then_read_equivalence(simple)

def test_simple_bool():
    simple = makeSimple()
    simple.bool.set(True)
    assert_equals(simple.bool(), True)
    simple.bool.set(False)
    assert_equals(simple.bool(), False)
    for s in ['on', 'true', '1', 'yes', 'On', 'YES']:
        simple.bool.setFromString(s)
        assert_equals(simple.bool(), True)
    for s in ['off', 'false', '0', 'no', 'Off', 'NO']:
        simple.bool.setFromString(s)
        assert_equals(simple.bool(), False)
    assert_write_then_read_equivalence(simple)

def test_simple_float():
    simple = makeSimple()
    simple.float.set(0.0)
    assert_equals(simple.float(), 0.0)
    assert_write_then_read_equivalence(simple)

def test_simple_defaults_commented_out():
    simple = makeSimpleWithDefaults()
    fp = sio()
    simple.writefp(fp)
    fp.seek(0)
    for line in fp:
        line = line.strip()
        if line:
            assert line.startswith('#'), 'Default is not commented out: %r' % line
    simple.int.set(0)
    simple.bool.set(False)
    simple.float.set(0.0)
    fp.seek(0)
    simple.writefp(fp)
    fp.seek(0)
    for line in fp:
        line = line.strip()
        if line:
            assert not line.startswith('#'), 'Non-default commented out: %r' % line
    assert_write_then_read_equivalence(simple)

def test_simple_defaults_returned():
    simple = makeSimpleWithDefaults()
    assert_equals(simple.int(), 1)
    assert_equals(simple.bool(), True)
    assert_equals(simple.float(), 1.0)
    assert_write_then_read_equivalence(simple)

def test_simple_defaults_overridden():
    simple = makeSimpleWithDefaults()
    simple.int.set(0)
    simple.bool.set(False)
    simple.float.set(0.0)
    assert_equals(simple.int(), 0)
    assert_equals(simple.bool(), False)
    assert_equals(simple.float(), 0.0)
    assert_write_then_read_equivalence(simple)

def test_simple_iter():
    simple = makeSimple()
    flattened = list(simple)
    assert_equals(flattened[0], ('simple', simple))
    assert_equals(flattened[1], ('simple.int', simple.int))
    assert_equals(flattened[2], ('simple.bool', simple.bool))
    assert_equals(flattened[3], ('simple.float', simple.float))
    assert_write_then_read_equivalence(simple)

def test_simple_env():
    simple = makeSimple()
    simple.readenv({'SIMPLE_INT': '0', 'SIMPLE_FLOAT': '0.0'})
    assert_equals(simple.int(), 0)
    assert_equals(simple.bool(), None)
    assert_equals(simple.float(), 0.0)
    assert_write_then_read_equivalence(simple)

def test_simple_optparse():
    simple = makeSimple()
    parser = simple.toOptionParser()
    parser.parse_args(['--simple-int', '0', '--simple-float', '0.0'])
    assert_equals(simple.int(), 0)
    assert_equals(simple.bool(), None)
    assert_equals(simple.float(), 0.0)
    assert_write_then_read_equivalence(simple)

def test_expectsValue():
    simple = makeSimple()
    assert not simple.expectsValue()
    assert simple.int.expectsValue()

def test_equals_works_as_separator():
    simple = makeSimple()
    fp = sio("""
simple.int: 1
simple.bool = True
""")
    assert_equals(simple.int(), None)
    assert_equals(simple.bool(), None)
    simple.readfp(fp)
    assert_equals(simple.int(), 1)
    assert_equals(simple.bool(), True)

def test_callable_as_default():
    config = hieropt.Group('config')
    def callable_default():
        return 1.5
    config.register(hieropt.Float('float', default=callable_default))
    assert_equals(config.float(), 1.5)

def test_inflexible_group():
    config = hieropt.Group('config')
    config.register(hieropt.Int('x', default=1))
    assert_raises(AttributeError, getattr, config, 'y')
    fp = sio("""
config.x: 2
config.y: 2
""")
    assert_raises(hieropt.UnregisteredName, config.readfp, fp)
        
def test_flexible_group():
    config = hieropt.Group('config')
    config.register(hieropt.Group('strings', Child=hieropt.Value))
    config.register(hieropt.Group('ints', Child=hieropt.Int))
    assert_write_then_read_equivalence(config)
    config.strings.s1.set('foo')
    assert_write_then_read_equivalence(config)
    assert_equals(config.strings.s1(), 'foo')
    config.strings.s2.set('bar')
    assert_write_then_read_equivalence(config)
    assert_equals(config.strings.s2(), 'bar')
    config.ints.x.set(1)
    assert_equals(config.ints.x(), 1)
    assert_write_then_read_equivalence(config)
    config.ints.y.set(2)
    assert_equals(config.ints.y(), 2)
    assert_write_then_read_equivalence(config)
    fp = sio("""
config.strings.s3: baz
config.ints.z: 3
""")
    config.readfp(fp)
    assert_equals(config.strings.s3(), 'baz')
    assert_equals(config.ints.z(), 3)
    assert_write_then_read_equivalence(config)

def test_parent_supplies_default():
    config = hieropt.Group('config')
    config.register(hieropt.Int('x', default=1))
    config.x.register(hieropt.Int('y', default=hieropt.parent))
    assert_equals(config.x(), 1)
    assert_equals(config.x.y(), 1)
    assert_write_then_read_equivalence(config)
    config.x.set(2)
    assert_equals(config.x(), 2)
    assert_equals(config.x.y(), 2)
    assert_write_then_read_equivalence(config)
    config.x.y.set(3)
    assert_equals(config.x(), 2)
    assert_equals(config.x.y(), 3)
    assert_write_then_read_equivalence(config)

def test_value_predicates():
    no_default = hieropt.Int('x')
    assert not no_default.isSet()
    assert no_default.isDefault()
    no_default.set(1)
    assert no_default.isSet()
    with_default = hieropt.Int('x', default=1)
    assert with_default.isSet()
    assert with_default.isDefault()
    with_default.set(2)
    assert not with_default.isDefault()

def test_writeComment():
    fp = sio()
    L = []
    for i in xrange(100):
        fp.seek(0)
        comment = ' '.join(L)
        hieropt.writeComment(fp, comment)
        fp.seek(0)
        for line in fp:
            assert line.startswith('#')
            assert len(line) < 80, 'Line longer than 80 chars: %r' % line
        L.append('xyz')

def test_emptyFile():
    # No defaults
    simple = makeSimple()
    assert_equals(simple.int(), None)
    assert_equals(simple.bool(), None)
    assert_equals(simple.float(), None)
    # Preserved by reading empty file?
    simple.readfp(sio())
    assert_equals(simple.int(), None)
    assert_equals(simple.bool(), None)
    assert_equals(simple.float(), None)
    # Preserved by reading one-comment file?
    simple.readfp(sio('#!/usr/bin/env finitd\n'))
    assert_equals(simple.int(), None)
    assert_equals(simple.bool(), None)
    assert_equals(simple.float(), None)
    # Set values and try again
    simple.int.set(1)
    simple.bool.set(True)
    simple.float.set(1.0)
    assert_equals(simple.int(), 1)
    assert_equals(simple.bool(), True)
    assert_equals(simple.float(), 1.0)
    # Preserved by reading empty file?
    simple.readfp(sio())
    assert_equals(simple.int(), 1)
    assert_equals(simple.bool(), True)
    assert_equals(simple.float(), 1.0)
    # Preserved by reading one-comment file?
    simple.readfp(sio('#!/usr/bin/env finitd\n'))
    assert_equals(simple.int(), 1)
    assert_equals(simple.bool(), True)
    assert_equals(simple.float(), 1.0)

def test_writefp_annotate():
    config = hieropt.Group('config')
    config.register(hieropt.Int('x', default=1, comment='config int x'))
    fp = sio()
    config.writefp(fp)
    assert_equals(fp.getvalue().strip(), """
# config int x
# config.x: 1

""".strip())

    fp = sio()
    config.writefp(fp, annotate=False)
    assert_equals(fp.getvalue().strip(), """
# config.x: 1
""".strip())

    config.x.set(2)
    fp = sio()
    config.writefp(fp)
    assert_equals(fp.getvalue().strip(), """
# config int x
config.x: 2
""".strip())

    fp = sio()
    config.writefp(fp, annotate=False)
    assert_equals(fp.getvalue().strip(), """
config.x: 2
""".strip())

def test_deepcopy():
    simple = makeSimple()
    simple.int.register(hieropt.Int('x'))
    simple.int.x.register(hieropt.Int('y'))
    assert_equals(simple.int(), None)
    assert_equals(simple.int.x(), None)
    assert_equals(simple.int.x.y(), None)
    assert_equals(simple.bool(), None)
    assert_equals(simple.float(), None)
    simple2 = copy.deepcopy(simple)
    assert_equals(simple2.int(), None)
    assert_equals(simple2.int.x(), None)
    assert_equals(simple2.int.x.y(), None)
    assert_equals(simple2.bool(), None)
    assert_equals(simple2.float(), None)
    simple2.int.set(1)
    simple2.int.x.set(2)
    simple2.int.x.y.set(3)
    assert_equals(simple.int(), None)
    assert_equals(simple.int.x(), None)
    assert_equals(simple.int.x.y(), None)
    assert_equals(simple2.int(), 1)
    assert_equals(simple2.int.x(), 2)
    assert_equals(simple2.int.x.y(), 3)
    
