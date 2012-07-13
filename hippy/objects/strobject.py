
import weakref
from pypy.rlib.rerased import new_erasing_pair
from pypy.rlib.objectmodel import instantiate, specialize, compute_hash,\
     _hash_string
from pypy.rlib import jit
from pypy.tool.sourcetools import func_with_new_name
from hippy.objects.base import W_Root
from hippy.objects.reference import W_ContainerIntReference

cache = {}
hash_string = jit.elidable(func_with_new_name(_hash_string, 'hash_string'))

@specialize.memo()
def new_strategy(strat):
    try:
        return cache[strat]
    except KeyError:
        n = strat()
        cache[strat] = n
        return n

class StrategyMixin(object):
    _mixin_ = True

def new_weakref(obj):
    return obj

class W_StrInterpolation(W_Root):
    _immutable_fields_ = ['strings[*]', 'vars[*]']
    
    def __init__(self, strings, vars):
        self.strings = strings
        self.vars = vars
        assert len(vars) == len(strings) - 1

    @jit.unroll_safe
    def interpolate(self, space, frame, bytecode):
        # XXX mutable string support, can be made faster, by using write_into
        #     instead of casting to immutable string
        r = [self.strings[0]]
        for i in range(len(self.strings) - 1):
            r.append(space.str_w(space.as_string(
                frame.load_var(space, bytecode, self.vars[i]))))
            r.append(self.strings[i + 1])
        return space.newstrconst(''.join(r))

class BaseStringStrategy(object):
    concat = False

    def copy(self, obj):
        return W_StringObject.newcopiedstr(obj)

    def get_string_source(self, obj):
        return obj

    def force_concat(self, obj):
        pass

class ConstantStringStrategy(BaseStringStrategy):
    erase, unerase = new_erasing_pair("constant")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    concrete = True

    def conststr_w(self, storage):
        return self.unerase(storage)

    def getitem(self, storage, item):
        return self.unerase(storage)[item]

    def setitem(self, storage, item, val):
        raise Exception("Should not happen")

    def len(self, storage):
        return len(self.unerase(storage))

    def getchar(self, storage):
        s = self.unerase(storage)
        if len(s) == 0:
            return '\x00'
        return s[0]

    def str_w(self, storage):
        return self.unerase(storage)

    def force_mutable(self, strobj):
        newstrat = new_strategy(MutableStringStrategy)
        strobj.strategy = newstrat
        strobj.storage = newstrat.erase([c
                                for c in self.unerase(strobj.storage)])

    def copy(self, obj):
        return W_StringObject(self.unerase(obj.storage))

    def repr(self, storage):
        return 'C(%s)' % self.unerase(storage)

    def force_copy(self, sourcestorage, destobj):
        destobj.storage = self.erase(self.unerase(sourcestorage)[:])

    def write_into(self, storage, target, start):
        s = self.unerase(storage)
        i = 0
        for c in s:
            target[start + i] = c
            i += 1

    def append(self, storage, target):
        s = self.unerase(storage)
        i = 0
        for c in s:
            target.append(c)
            i += 1

    def is_true(self, storage):
        return bool(self.unerase(storage))

    def eq(self, space, w_obj, w_other):
        return self.unerase(w_obj.storage) == self.unerase(w_other.storage)

    def strslice(self, space, storage, start, stop):
        return W_StringObject(self.unerase(storage)[start:stop])

    def hash(self, storage):
        return compute_hash(self.unerase(storage))

class MutableStringStrategy(BaseStringStrategy):
    erase, unerase = new_erasing_pair("mutable")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    concrete = True

    def conststr_w(self, storage):
        return ''.join(self.unerase(storage))

    def getitem(self, storage, item):
        return self.unerase(storage)[item]

    def len(self, storage):
        return len(self.unerase(storage))

    def force_mutable(self, strobj):
        pass

    def setitem(self, storage, item, val):
        self.unerase(storage)[item] = val

    def getchar(self, storage):
        s = self.unerase(storage)
        if len(s) == 0:
            return '\x00'
        return s[0]

    def str_w(self, storage):
        return "".join(self.unerase(storage))

    def repr(self, storage):
        return 'M(%s)' % ''.join(self.unerase(storage))

    def force_copy(self, sourcestorage, destobj):
        destobj.storage = self.erase(self.unerase(sourcestorage)[:])

    def write_into(self, storage, target, start):
        s = self.unerase(storage)
        for i, c in enumerate(s):
            target[start + i] = c

    def append(self, storage, target):
        s = self.unerase(storage)
        target.extend(s)

    def is_true(self, storage):
        return bool(self.unerase(storage))

    def eq(self, space, w_obj, w_other):
        return self.unerase(w_obj.storage) == self.unerase(w_other.storage)

    def strslice(self, space, storage, start, stop):
        return W_StringObject.newstr(self.unerase(storage)[start:stop])

    def inplace_concat(self, space, storage, w_obj):
        l = self.unerase(storage)
        w_obj.strategy.append(w_obj.storage, l)

    def hash(self, storage):
        return hash_string(self.unerase(storage))

class StringCopyStrategy(BaseStringStrategy):
    erase, unerase = new_erasing_pair("copy")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    concrete = False

    def force(self, obj):
        w_orig = self.unerase(obj.storage)
        w_orig.force()
        obj.strategy = w_orig.strategy
        w_orig.strategy.force_copy(w_orig.storage, obj)

    def getitem(self, storage, index):
        w_parent = self.unerase(storage)
        return w_parent.strategy.getitem(w_parent.storage, index)

    def getchar(self, storage):
        w_parent = self.unerase(storage)
        return w_parent.strategy.getchar(w_parent.storage)

    def len(self, storage):
        w_parent = self.unerase(storage)
        return w_parent.strlen()

    def repr(self, storage):
        return 'SC(%r)' % self.unerase(storage)

    def write_into(self, storage, target, start):
        parent = self.unerase(storage)
        parent.write_into(target, start)

    def append(self, storage, target):
        parent = self.unerase(storage)
        parent.strategy.append(parent.storage, target)

    def get_string_source(self, obj):
        return self.unerase(obj.storage)

    def is_true(self, storage):
        parent = self.unerase(storage)
        return parent.strategy.is_true(parent.storage)

    def eq(self, space, w_obj, w_other):
        return self.unerase(w_obj.storage).eq_w(space,
                                                self.unerase(w_other.storage))

    def strslice(self, space, storage, start, stop):
        return self.unerase(storage).strslice(space, start, stop)

    def force_concat(self, obj):
        self.unerase(obj.storage).force_concat()

    def hash(self, storage):
        parent = self.unerase(storage)
        return parent.strategy.hash(parent.storage)

class StringConcatStrategy(BaseStringStrategy):
    erase, unerase = new_erasing_pair("concat")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    concrete = False
    concat = True

    def force(self, obj):
        s = ['\x00'] * self.len(obj.storage)
        self.write_into(obj.storage, s, 0)
        strategy = new_strategy(MutableStringStrategy)
        obj.storage = strategy.erase(s)
        obj.strategy = strategy

    def force_concat(self, obj):
        self.force(obj)

    def len(self, storage):
        l_one, l_two, lgt = self.unerase(storage)
        return lgt

    def append(self, storage, target):
        lgt = len(target)
        target.extend(['\x00'] * self.len(storage))
        self.write_into(storage, target, lgt)

    def write_into(self, storage, target, start):
        l_one, l_two, lgt = self.unerase(storage)
        l_one.write_into(target, start)
        l_two.write_into(target, start + l_one.strlen())
        #so_far = [(0, l_one), (l_one.strlen(), l_two)]
        #while so_far:
        #    # XXX jit driver anyone?
        #    index, obj = so_far.pop()
        #    strat = obj.strategy
        #    obj = strat.get_string_source(obj)
        #    strat = obj.strategy # might be a different one
        #    if isinstance(strat, StringConcatStrategy):
        #        one, two, lgt = strat.unerase(obj.storage)
        #        so_far.append((index, one))
        #        so_far.append((index + one.strlen(), two))
        #    else:
        #        obj.write_into(target, index)

    def repr(self, storage):
        return 'CON(%r)' % (self.unerase(storage),)

    def is_true(self, storage):
        # XXX recursion? figure out a way to flatten those easier
        left, right = self.unerase(storage)
        return (left.strategy.is_true(left.storage) or
                right.strategy.is_true(right.storage))

class W_StringObject(W_Root):
    def __init__(self, strval):
        strategy = new_strategy(ConstantStringStrategy)
        self.storage = strategy.erase(strval)
        self.strategy = strategy
        self.copies = None

    @staticmethod
    def newstr(strval):
        w_s = instantiate(W_StringObject)
        strategy = new_strategy(MutableStringStrategy)
        w_s.storage = strategy.erase(strval)
        w_s.strategy = strategy
        w_s.copies = None
        return w_s

    @staticmethod
    def newcopiedstr(origobj):
        w_s = instantiate(W_StringObject)
        strategy = new_strategy(StringCopyStrategy)
        w_s.copies = None
        w_s.storage = strategy.erase(origobj)
        w_s.strategy = strategy
        return w_s

    @staticmethod
    def newstrconcat(origobj, other):
        w_s = instantiate(W_StringObject)
        strategy = new_strategy(StringConcatStrategy)
        w_s.copies = None
        w_s.storage = strategy.erase((origobj, other, origobj.strlen() +
                                      other.strlen()))
        w_s.strategy = strategy
        origobj.add_copy(new_weakref(w_s))
        other.add_copy(new_weakref(w_s))
        return w_s

    def add_copy(self, other):
        if self.copies is None:
            self.copies = [other]
        else:
            self.copies.append(other)

    def write_into(self, s, start):
        self.strategy.write_into(self.storage, s, start)

    def force(self):
        if self.strategy.concrete:
            return
        self.strategy.force(self)

    def force_concat(self):
        self.strategy.force_concat(self)

    def _force_mutable_copies(self):
        for copy in self.copies:
            if copy:
                copy.force()
        self.copies = None

    def force_mutable(self):
        self.force()
        if self.copies:
            self._force_mutable_copies()
        self.strategy.force_mutable(self)

    def conststr_w(self, space):
        self.force()
        return self.strategy.conststr_w(self.storage)

    def itemreference(self, space, w_arg):
        return W_ContainerIntReference(space, self, space.int_w(w_arg))

    def getitem(self, space, w_arg):
        return space.newstrconst(str(self.strategy.getitem(self.storage,
                                                           space.int_w(w_arg))))

    def setitem(self, space, w_arg, w_value):
        self.force_mutable()
        self.strategy.setitem(self.storage, space.int_w(w_arg),
                              space.getchar(w_value))

    def str_w(self, space):
        self.force()
        return self.strategy.str_w(self.storage)

    def getchar(self, space):
        return self.strategy.getchar(self.storage)

    def strlen(self):
        return self.strategy.len(self.storage)

    def copy(self, space):
        res = self.strategy.copy(self)
        self.add_copy(new_weakref(res))
        return res

    def as_string(self, space):
        return self

    def is_true(self, space):
        return self.strategy.is_true(self.storage)

    def as_number(self, space):
        # XXX we might want to write two implementations of this
        s = space.str_w(self)
        # scan string for first non . non number
        i = 0
        is_float = False
        if not s:
            return space.wrap(0)
        if s[0] == '-':
            i += 1
        while i < len(s):
            if (s[i] < '0' or s[i] > '9'):
                if s[i] == '.':
                    is_float = True
                else:
                    break
            i += 1
        if i == 0:
            return space.wrap(0)
        if is_float:
            return space.newfloat(float(s[:i]))
        return space.newint(int(s[:i]))

    def float_w(self, space):
        return space.float_w(self.as_number(space))

    def uplusplus(self, space):
        # XXX this can be lazified
        self.force_mutable()
        newval = chr((ord(self.strategy.getitem(self.storage,
                                                self.strlen() - 1)) + 1) & 0xff)
        self.strategy.setitem(self.storage, self.strlen() - 1, newval)
        return self

    def uminusminus(self, space):
        # XXX this can be lazified
        self.force_mutable()
        newval = chr((ord(self.strategy.getitem(self.storage,
                                                self.strlen() - 1)) - 1) & 0xff)
        self.strategy.setitem(self.storage, self.strlen() - 1, newval)
        return self

    def eq_w(self, space, w_other):
        if self is w_other:
            return True
        assert isinstance(w_other, W_StringObject)
        self.force_concat()
        w_other.force_concat()
        if self.strategy is w_other.strategy:
            return self.strategy.eq(space, self, w_other)
        return space.str_w(w_other) == space.str_w(self)

    def eq(self, space, w_other):
        return space.newbool(self.eq_w(space, w_other))

    def strconcat(self, space, w_other):
        res = W_StringObject.newstrconcat(self, w_other)
        return res

    def strslice(self, space, start, stop):
        self.force_concat()
        return self.strategy.strslice(space, self.storage, start, stop)

    def inplace_concat(self, space, w_value):
        self.force_mutable()
        w_value = space.as_string(w_value)
        self.strategy.inplace_concat(space, self.storage, w_value)

    def __repr__(self):
        return self.strategy.repr(self.storage)

    def hash(self):
        self.force_concat()
        return self.strategy.hash(self.storage)
