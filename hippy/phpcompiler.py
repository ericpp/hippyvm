from hippy.sourceparser import parse
from hippy.astcompiler import CompilerContext
from hippy import consts


def compile_php(filename, source, space):
    """Parse and compile a PHP file, starting in literal mode (i.e.
    dumping all input directly) until the first '<?' or '<?php'.
    Supports a mixture of blocks of code between the blocks of texts."""
    #
    XXX
    c = CompilerContext(filename, source.split("\n"), 0, space)
    startindex = 0
    while True:
        tagindex = source.find('<?', startindex)
        if tagindex == -1:
            break
        if tagindex > startindex:
            block_of_text = source[startindex:tagindex]
            c.emit(consts.LOAD_NAME, ctx.create_name(block_of_text))
            c.emit(consts.ECHO, 1)
        #
        if source[tagindex:tagindex+5].lower() == '<?php':
            startindex = tagindex + 5
        else:
            startindex = tagindex + 2
        #
        #...
