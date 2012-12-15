
from hippy.error import InterpreterError

class W_Root(object):
    """ The base class for everything that can be represented as a first-class
    object at applevel
    """
    _attrs_ = ()

    def deref(self):
        return self # anything but a reference

    def int_w(self, space):
        raise InterpreterError("TypeError: casting to int of wrong type")

    def float_w(self, space):
        raise InterpreterError("TypeError: casting to float of wrong type")

    def str_w(self, space): 
        raise InterpreterError("TypeError: casting to string of wrong type")

    def getchar(self, space):
        raise InterpreterError("TypeError: casting to string of wrong type")
        # XXX cast to string, get first char

    def getitem(self, space, w_item):
        # XXX cast to array
        raise InterpreterError("TypeError: getitem on wrong type")

    def ne(self, space, other):
        return space.newbool(not self.eq_w(space, other))

    def eq(self, space, other):
        return space.newbool(self.eq_w(space, other))

    def deref_for_store(self):
        return self.deref()

    def store_var(self, space, w_value):
        raise InterpreterError("Only variables can be used as references")

    def mark_invalid(self):
        pass

    def is_true(self, space):
        raise InterpreterError("unsupported is_true")

    def as_number(self, space):
        raise InterpreterError("unsupported as_number")

    def is_valid_number(self, space):
        raise InterpreterError("unsupported is_valid_number")

    def as_string(self, space):
        raise InterpreterError("unsupported as_string")

    def uplus(self, space):
        raise InterpreterError("unsupport uplus")

    def uminus(self, space):
        raise InterpreterError("unsupport uminus")

    def uplusplus(self, space):
        raise InterpreterError("unsupport uplusplus")

    def uminusminus(self, space):
        raise InterpreterError("unsupport uminusminus")

    def itemreference(self, space, w_item):
        raise InterpreterError("unsupported itemreference")

    def setitem(self, space, w_item, w_value):
        raise InterpreterError("unsupported setitem")

    def strlen(self):
        raise InterpreterError("unsupported strlen")

    def arraylen(self, space):
        raise InterpreterError("unsupported arraylen")

    def append(self, space, w_item):
        raise InterpreterError("unsupported append")

    def create_iter(self, space):
        raise InterpreterError("unsupported create_iter")

    def hash(self):
        raise InterpreterError("unsupported hash")

    def var_dump(self, space, indent, recursion):
        # unsupported type: use the RPython repr
        space.ec.writestr('%s%r\n' % (indent, self))

class W_NullObject(W_Root):
    def copy(self, space):
        return self

    def is_true(self, space):
        return False

    def as_number(self, space):
        return space.wrap(0)

    def as_string(self, space):
        return space.newstrconst("")

    def eq_w(self, space, other):
        return True

    def var_dump(self, space, indent, recursion):
        space.ec.writestr("%sNULL\n" % indent)
