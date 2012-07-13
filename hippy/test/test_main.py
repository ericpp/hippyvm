
import py
from hippy.main import entry_point

class TestMain(object):
    def setup_method(self, meth):
        self.tmpname = meth.im_func.func_name

    def run(self, code, capfd):
        tmpdir = py.path.local.make_numbered_dir('hippy')
        phpfile = tmpdir.join(self.tmpname + '.php')
        phpfile.write(code)        
        r = entry_point(['hippy', str(phpfile)])
        out, err = capfd.readouterr()
        assert not r
        assert not err
        return out

    def test_running(self, capfd):
        out = self.run("""<?php
        $x = 3;
        echo $x;
        ?>
        """, capfd)
        assert out == "3"

    def test_running2(self, capfd):
        out = self.run("""<?php
        $x = 3;
        echo $x;
        ?>""", capfd)
        assert out == "3"        

    def test_running3(self, capfd):
        out = self.run("""<?
        $x = 3;
        echo $x;
        ?>""", capfd)
        assert out == "3"

    def test_running4(self, capfd):
        out = self.run('''
        <?php
        $n = 20;
        while ($n-- > 0) {
          echo $n;
        }
        ?>
        ''', capfd)
        assert out == '191817161514131211109876543210'
