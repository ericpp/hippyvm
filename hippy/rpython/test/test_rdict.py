
import py
from hippy.rpython.rdict import RDict, new_dict_lltype
from hippy.rpython import lldict
from pypy.rpython.test.tool import LLRtypeMixin, BaseRtypingTest
from pypy.rpython.annlowlevel import llstr
from pypy.rpython.lltypesystem import lltype

class Obj(object):
    def __init__(self, v=0):
        self.v = v

class SubObj(Obj):
    pass

class TestLLDirect(object):
    def test_resize(self):
        T = new_dict_lltype(lltype.Signed)
        d = lldict.ll_newdict(T.TO)
        lldict.ll_setitem_str(d, llstr("abc"), 3)
        lldict.ll_setitem_str(d, llstr("def"), 4)
        assert lldict.ll_getitem_str(d, llstr("abc")) == 3
        assert lldict.ll_getitem_str(d, llstr("def")) == 4
        for i in range(10):
            lldict.ll_setitem_str(d, llstr(str(i)), i * 10)
        assert lldict.ll_getitem_str(d, llstr("abc")) == 3
        assert lldict.ll_getitem_str(d, llstr("def")) == 4
        for i in range(10):
            assert lldict.ll_getitem_str(d, llstr(str(i))) == i * 10

    def test_iteration(self):
        T = new_dict_lltype(lltype.Signed)
        VT = lltype.Ptr(lltype.GcStruct('RDICTITER',
            ('curkey', lltype.Signed), ('rdict', T)))

        d = lldict.ll_newdict(T.TO)
        lldict.ll_setitem_str(d, llstr("abc"), 3)
        lldict.ll_setitem_str(d, llstr("def"), 4)
        for i in range(10):
            lldict.ll_setitem_str(d, llstr(str(i)), i * 10)
        llv = lldict.ll_new_iter(VT.TO, d)
        lst = []
        try:
            while True:
                lst.append(lldict.ll_next_iter_value(llv))
        except StopIteration:
            pass
        assert lst == [3, 4] + range(0, 100, 10)

class RDictTests(object):
    def test_basic(self):
        def f():
            d = RDict(Obj)
            o = Obj()
            d["xyz"] = o
            try:
                d["a"]
            except KeyError:
                pass
            else:
                raise Exception("Did not raise")
            return d["xyz"] == o
        assert self.interpret(f, [])

    def test_contains(self):
        def f():
            d = RDict(Obj)
            o = Obj()
            d["xyz"] = o
            return ("xyz" in d) * 10 + ("a" not in d)
        assert self.interpret(f, []) == 11

    def test_resized(self):
        def f():
            d = RDict(Obj)
            o = Obj()
            d["a"] = o
            for k in range(10):
                d[str(k)] = Obj()
            d["b"] = o
            for k in range(10):
                d[str(k)] = Obj()
            return (d["a"] is o) * 10 + (d["b"] is o)
        assert self.interpret(f, []) == 11

    def test_copy(self):
        def f():
            d = RDict(Obj)
            d2 = d.copy()
            o = Obj()
            d2["a"] = o
            return ("a" not in d) * 10 + ("a" in d2)
        assert self.interpret(f, []) == 11

    def test_subclass(self):
        def f():
            d = RDict(Obj)
            o = SubObj()
            d["a"] = o
            return int(d["a"] is o)
        assert self.interpret(f, []) == 1

    def test_mixed_types_int(self):
        py.test.skip("not yet")
        def f():
            d = RDict(Obj)
            o = Obj()
            d[35] = o
            return int(d["35"] is o) * 10 + (d[35] is o) * 100 + (35 in d)
        assert self.interpret(f, []) == 111

    def test_iteration(self):
        def f():
            d = RDict(Obj)
            lst = [Obj(i) for i in range(5)]
            for i, elem in enumerate(lst):
                d[str(i)] = elem
            i = d.iter()
            l2 = []
            try:
                while True:
                    l2.append(i.next())
            except StopIteration:
                pass
            return lst == l2
        assert self.interpret(f, []) == 1

    def test_iteration_empty(self):
        def f():
            d = RDict(Obj)
            i = d.iter()
            try:
                i.next()
            except StopIteration:
                pass
            else:
                raise Exception("did not raise")
        self.interpret(f, [])

    def test_iteration_2(self):
        def f():
            d = RDict(Obj)
            lst = [Obj() for i in range(5)]
            for i, elem in enumerate(lst):
                d[str(i)] = elem
            i = d.iter()
            l2 = []
            try:
                while True:
                    l2.append(i.nextitem())
            except StopIteration:
                pass
            return [(str(i), v) for i, v in enumerate(lst)] == l2
        assert self.interpret(f, []) == 1

    def test_len(self):
        def f():
            d = RDict(Obj)
            for i in range(10):
                d[str(i)] = Obj()
            return len(d)
        assert self.interpret(f, []) == 10        

class TestRDictDirect(RDictTests):
    def interpret(self, f, args):
        return f(*args)

class TestRDictLLtype(RDictTests, BaseRtypingTest, LLRtypeMixin):
    pass
