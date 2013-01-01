import py
from hippy.test.test_interpreter import BaseTestInterpreter
from hippy.test.directrunner import run_php_source
from hippy.phpcompiler import compile_php, PHPLexerWrapper
from hippy.objspace import ObjSpace


class BaseTestPHP(BaseTestInterpreter):

    def run(self, source):
        output_w = BaseTestInterpreter.run(self, source)
        space = self.space
        output = [space.str_w(space.as_string(v)) for v in output_w]
        return ''.join(output)

    def compile(self, source):
        return compile_php('<input>', source, self.space)

    def run_direct(self, source):
        space = self.space
        s = run_php_source(space, source)
        return [space.newstr(s)]


def test_phplexerwrapper():
    phplexerwrapper = PHPLexerWrapper(
        'Foo\n<?php echo 5 ?>\nBar\nBaz\n<? echo')
    for expected in [('B_LITERAL_BLOCK', 'Foo\n', 1),
                     ('T_ECHO', 'echo', 2),
                     ('T_LNUMBER', '5', 2),
                     (';', ';', 2),
                     ('B_LITERAL_BLOCK', 'Bar\nBaz\n', 3),
                     ('T_ECHO', 'echo', 5)]:
        tok = phplexerwrapper.next()
        assert (tok.name, tok.value, tok.getsourcepos()) == expected
    tok = phplexerwrapper.next()
    assert tok is None

def test_line_start_offset():
    bc = compile_php('<input>', 'Hi there\n', ObjSpace())
    assert bc.startlineno == 1


class TestPHPCompiler(BaseTestPHP):

    def test_simple(self):
        output = self.run('Foo <?php echo 5; ?> Bar')
        assert output == 'Foo 5 Bar'

    def test_simple_2(self):
        output = self.run('Foo <? echo 5; ?> Bar')
        assert output == 'Foo 5 Bar'
        output = self.run('Foo<?echo 5;?>Bar')
        assert output == 'Foo5Bar'

    def test_case_insensitive(self):
        output = self.run('Foo <?phP echo 5; ?> Bar')
        assert output == 'Foo 5 Bar'

    def test_no_php_code(self):
        output = self.run('Foo\n')
        assert output == 'Foo\n'
        output = self.run('\nFoo')
        assert output == '\nFoo'

    def test_eol_after_closing_tag(self):
        output = self.run('Foo <?phP echo 5; ?>\nBar')
        assert output == 'Foo 5Bar'
        output = self.run('Foo <?phP echo 5; ?> \nBar')
        assert output == 'Foo 5 \nBar'
        output = self.run('Foo <?phP echo 5; ?>\n')
        assert output == 'Foo 5'
        output = self.run('Foo <?phP echo 5; ?>\n\n')
        assert output == 'Foo 5\n'
        output = self.run('Foo <?phP echo 5; ?> \n')
        assert output == 'Foo 5 \n'

    def test_end_in_comment_ignored_1(self):
        output = self.run('Foo <? echo 5; /* ?> */ echo 6; ?> Bar')
        assert output == 'Foo 56 Bar'

    def test_end_in_comment_not_ignored_1(self):
        output = self.run('Foo <? echo 5; //?>\necho 6; ?> Bar')
        assert output == 'Foo 5echo 6; ?> Bar'

    def test_end_in_comment_not_ignored_2(self):
        output = self.run('Foo <? echo 5; #?>\necho 6; ?> Bar')
        assert output == 'Foo 5echo 6; ?> Bar'

    def test_double_end(self):
        output = self.run('<?php echo 5; ?> echo 6; ?>\n')
        assert output == '5 echo 6; ?>\n'

    def test_multiple_blocks(self):
        output = self.run('-<?echo 5;?>+<?echo 6;?>*')
        assert output == '-5+6*'

    def test_non_closing_last_block_of_code(self):
        output = self.run('-<?echo 5;?>+<?echo 6;')
        assert output == '-5+6'

    def test_missing_semicolon_before_end(self):
        output = self.run('-<?echo 5?>+')
        assert output == '-5+'

    def test_reuse_var(self):
        output = self.run('<?$x=5?>----<?echo $x;')
        assert output == '----5'

    def test_multiple_use_of_block_of_text(self):
        output = self.run('<?for($x=0; $x<5; $x++){?>-+-+-\n<?}')
        assert output == '-+-+-\n' * 5

    def test_automatic_echo_1(self):
        output = self.run('abc<?=2+3?>def')
        assert output == 'abc5def'

    def test_automatic_echo_2(self):
        output = self.run('abc<?=2+3,7-1?>def')
        assert output == 'abc56def'

    def test_automatic_echo_3(self):
        output = self.run('abc<?=2+3,7-1; echo 8+1;?>def')
        assert output == 'abc569def'

    def test_automatic_echo_4(self):
        output = self.run('abc<?=2+3?><?=6*7?>def')
        assert output == 'abc542def'

    def test_automatic_echo_5(self):
        py.test.raises(Exception, self.run, 'abc<? =2+3?>def')

    def test_automatic_echo_6(self):
        output = self.run('abc<?=2+3?>\ndef<?=6*7?> \nghi')
        assert output == 'abc5def42 \nghi'

    def test_automatic_echo_7(self):
        output = self.run('abc<?=2+3;')
        assert output == 'abc5'
        py.test.raises(Exception, self.run, 'abc<?=2+3')
