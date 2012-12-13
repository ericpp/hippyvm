
import sys

class FatalError(Exception):
    pass

class Logger(object):    
    def log(self, interp, level, msg):
        tb = []
        interp.gather_traceback(self.log_traceback, tb)
        tb.reverse()
        for fname, line, source in tb:
            self._log_traceback(fname, line, source)
        self._log(level, msg)

    def log_traceback(self, tb, frame):
        code = frame.bytecode
        fname = code.name
        line = code.bc_mapping[frame.next_instr]
        source = code.sourcelines[line]
        tb.append((fname, line, source))

    def _log_traceback(self, fname, line, source):
        print >>sys.stderr, fname, line, source

    def _log(self, level, msg):
        print >>sys.stderr, level, msg
    
    def fatal(self, interpreter, msg):
        self.log(interpreter, "FATAL", msg)
        raise FatalError
