
from pypy.rlib.objectmodel import compute_hash
from pypy.rlib import debug
from pypy.rlib.rstring import StringBuilder
from hippy.objects.base import W_Root
from hippy.objects.convert import convert_string_to_number


class W_StringObject(W_Root):
    """Abstract base class.  Concrete subclasses use various strategies.
    This base class defines the general methods that can be implemented
    without needing to call (too often) the strlen() and character()
    methods.
    """

    @staticmethod
    def newliststr(chars):
        return W_ListStringObject(chars)

    @staticmethod
    def newconststr(s):
        return W_ConstStringObject(s)

    def hash(self, space):
        # XXX improve
        return compute_hash(self.str_w(space))

    def as_string(self, space):
        return self

    def as_number(self, space):
        s = self.str_w(space)
        w_number, valid = convert_string_to_number(space, s)
        return w_number      # ignore 'valid'

    def is_really_valid_number(self, space):
        s = self.str_w(space)
        w_number, valid = convert_string_to_number(space, s)
        return valid

    def int_w(self, space):
        return space.int_w(self.as_number(space))

    def float_w(self, space):
        return space.float_w(self.as_number(space))

    def uplusplus(self, space):
        if self.is_really_valid_number(space):
            return self.as_number(space).uplusplus(space)
        result = self.as_unique_strlist()
        chars = result._chars
        i = len(chars) - 1
        extra = '1'
        while i >= 0:
            c = chars[i]
            if not c.isalnum():
                break
            if c == '9':
                c = '0'
                extra = '1'
            elif c == 'Z':
                c = 'A'
                extra = 'A'
            elif c == 'z':
                c = 'a'
                extra = 'a'
            else:
                chars[i] = chr(ord(c) + 1)
                break
            chars[i] = c
            i -= 1
        else:
            result.set_chars([extra] + chars)
        return result

    def uminusminus(self, space):
        if self.is_really_valid_number(space):
            return self.as_number(space).uminusminus(space)
        return self

    def eq_w(self, space, w_other):
        # XXX improve
        assert isinstance(w_other, W_StringObject)
        return self.str_w(space) == space.str_w(w_other)

##    def eq(self, space, w_other):
##        return space.newbool(self.eq_w(space, w_other))

    def strconcat(self, space, w_other):
        # XXX improve
        return W_ConstStringObject(self.str_w(space) + space.str_w(w_other))

##    def strslice(self, space, start, stop):
##        self.force_concat()
##        return self.strategy.strslice(space, self.storage, start, stop)

##    def inplace_concat(self, space, w_value):
##        self.force_mutable()
##        w_value = space.as_string(w_value)
##        self.strategy.inplace_concat(space, self.storage, w_value)

##    def __repr__(self):
##        return 'W_StringObject(%r)' % (self._strval,)

##    def hash(self):
##        self.force_concat()
##        return self.strategy.hash(self.storage)

    def var_dump(self, space, indent, recursion):
        s = self.str_w(space)
        space.ec.writestr('%sstring(%d) "%s"\n' % (indent, len(s), s))

##    def abs(space, self):
##        return self.as_number(space).abs(space)


class StringMixin(object):
    """This is a mixin to provide a more efficient implementation for
    each subclass.  It defines the methods that call character() a lot.
    Being a mixin, each method is actually repeated in the subclass,
    which allows character() to be inlined.
    """
    _mixin_ = True

    def getitem(self, space, w_arg):
        index = space.int_w(w_arg)
        assert 0 <= index < self.strlen()
        return SINGLE_CHAR_STRING[ord(self.character(index))]

    def as_unique_strlist(self):
        chars = [self.character(i) for i in range(self.strlen())]
        return W_ListStringObject(chars, flag=1)

    def setitem(self, space, w_arg, w_value):
        index = space.int_w(w_arg)
        c = space.getchar(w_value)
        res = self.as_unique_strlist()
        res.set_char_at(index, c)
        return res

    def str_w(self, space):
        # note: always overriden so far
        length = self.strlen()
        builder = StringBuilder(length)
        for i in range(length):
            builder.append(self.character(i))
        return builder.build()

    def is_true(self, space):
        length = self.strlen()
        if length == 0:
            return False
        elif length == 1:
            return self.character(0) != "0"
        else:
            return True

    def getchar(self, space):
        if self.strlen() >= 1:
            return self.character(0)
        else:
            return chr(0)


class W_ConstStringObject(StringMixin, W_StringObject):
    _immutable_ = True

    def __init__(self, strval):
        assert isinstance(strval, str)
        self._strval = strval

    def strlen(self):
        return len(self._strval)

    def character(self, index):
        return self._strval[index]

    def str_w(self, space):
        return self._strval


class W_ListStringObject(StringMixin, W_StringObject):
    _refcount = 0

    def __init__(self, chars, flag=0):
        _new_mutable_string(chars, flag)
        self.set_chars(chars)

    def set_chars(self, chars):
        debug.check_annotation(chars, _is_fixed_list_of_chars)
        self._chars = chars

    def set_char_at(self, index, c):
        assert index >= 0, "XXX: negative string offset, ignore"
        assert index <= len(self._chars), "XXX:insert spaces until long enough"
        self._chars[index] = c

    def as_unique_strlist(self):
        #if self._refcount == 1:
        #    return self
        #assert self._refcount > 1
        return W_ListStringObject(self._chars[:], flag=2)

    def incref(self):
        self._refcount += 1

    def decref(self):
        self._refcount -= 1

    def strlen(self):
        return len(self._chars)

    def character(self, index):
        return self._chars[index]

    def str_w(self, space):
        return ''.join(self._chars)


def _is_fixed_list_of_chars(s_arg, bookkeeper):
    from pypy.annotation.model import SomeList, SomeChar
    assert isinstance(s_arg, SomeList)
    s_arg.listdef.never_resize()
    assert SomeChar().contains(s_arg.listdef.listitem.s_value)

def _new_mutable_string(chars, flag):
    pass

SINGLE_CHAR_STRING = [W_ConstStringObject(chr(_i)) for _i in range(256)]
EMPTY_STRING = W_ConstStringObject("")
