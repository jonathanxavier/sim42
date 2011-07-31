#!/usr/bin/python
import marshal
import sys

MAGIC23 = ';\xf2\r\n'

def load_pyc(filename):
        f = open(filename, 'rb')
        try:
                magic = f.read(4)
                timestamp = f.read(4)
                codeobject = marshal.load(f)
        finally:
                f.close()
                return magic, timestamp, codeobject

def dump_pyc_23(filename, timestamp, codeobject):
        assert len(timestamp)==4
        f = open(filename, 'wb')
        try:
                f.write(MAGIC23)
                f.write(timestamp)
                marshal.dump(codeobject, f, 0)
        finally:
                f.close()

magic, timestamp, codeobject = load_pyc(sys.argv[1])
dump_pyc_23(sys.argv[2], timestamp, codeobject)