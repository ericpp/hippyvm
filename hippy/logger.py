
import sys, os

class InterpreterError(Exception):
    pass

class FatalError(InterpreterError):
    pass

class Logger(object):    
    def log(self, interp, level, msg):
        tb = []
        interp.gather_traceback(self.log_traceback, tb)
        tb.reverse()
        for filename, funcname, line, source in tb:
            self._log_traceback(filename, funcname, line, source)
        self._log(level, msg)

    def log_traceback(self, tb, frame):
        code = frame.bytecode
        funcname = code.name
        filename = code.filename
        line = code.bc_mapping[frame.next_instr]
        source = code.getline(line)
        tb.append((filename, funcname, line, source))

    def _log_traceback(self, filename, funcname, line, source):
        os.write(2, "In function %s, file %s, line %d\n" %
                 (funcname, filename, line))
        os.write(2, "  " + source + "\n")

    def _log(self, level, msg):
        os.write(2, level + " " + msg + "\n")
    
    def fatal(self, interpreter, msg):
        self.log(interpreter, "FATAL", msg)
        raise FatalError

    def notice(self, interpreter, msg):
        self.log(interpreter, "NOTICE", msg)
