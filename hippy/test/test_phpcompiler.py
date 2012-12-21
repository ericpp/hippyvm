from hippy.test.test_interpreter import BaseTestInterpreter
from hippy.phpcompiler import compile_php
from hippy.test.directrunner import run_php_source


class BaseTestPHP(BaseTestInterpreter):

    def run(self, source):
        output = BaseTestInterpreter.run(self, source)
        return ''.join(output)

    def compile(self, source):
        return compile_php('<input>', source, self.space)

    def run_direct(self, source):
        return run_php_source(self.space, source)


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
