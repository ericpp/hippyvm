
from hippy.test.test_interpreter import BaseTestInterpreter


class TestStrObject(BaseTestInterpreter):

    def test_uplusplus(self):
        output = self.run('$a = "189"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newint(190))

        output = self.run('$a = "  -01"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newint(0))

        output = self.run('$a = " 0x10"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newint(0x11))

        output = self.run('$a = " 0x 10"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst(" 0x 11"))

        output = self.run('$a = "017"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newint(18))

        output = self.run('$a = "1z8"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("1z9"))

        output = self.run('$a = "1y9"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("1z0"))

        output = self.run('$a = "1y39"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("1y40"))

        output = self.run('$a = "a"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("b"))

        output = self.run('$a = "?"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("?"))

        output = self.run('$a = "y99"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("z00"))

        output = self.run('$a = "1z9"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("2a0"))

        output = self.run('$a = "z99"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("aa00"))

        output = self.run('$a = "Y99"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("Z00"))

        output = self.run('$a = "1Z9"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("2A0"))

        output = self.run('$a = "9Z"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("10A"))

        output = self.run('$a = "*9Z"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("*0A"))

        output = self.run('$a = "Z99"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("AA00"))

        output = self.run('$a = "Cz9Z99"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("Da0A00"))

        output = self.run('$a = "  - 99"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("  - 00"))

        output = self.run('$a = "  - 99 "; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("  - 99 "))

        output = self.run('$a = "4.5"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newfloat(5.5))

        output = self.run('$a = ""; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("1"))

        output = self.run('$a = " "; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst(" "))

        output = self.run('$a = "9D9"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("9E0"))
        output = self.run('$a = "9E0"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newfloat(10.0))   # argh
        output = self.run('$a = "9E2"; echo ++$a;')
        assert self.space.is_w(output[0], self.space.newfloat(901.0))

    def test_uminusminus(self):
        output = self.run('$a = "190"; echo --$a;')
        assert self.space.is_w(output[0], self.space.newint(189))

        output = self.run('$a = "  -01"; echo --$a;')
        assert self.space.is_w(output[0], self.space.newint(-2))

        output = self.run('$a = "1z8"; echo --$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("1z8"))
        # no change

        output = self.run('$a = "c"; echo --$a;')
        assert self.space.is_w(output[0], self.space.newstrconst("c"))
        # no change

        output = self.run('$a = "4.5"; echo --$a;')
        assert self.space.is_w(output[0], self.space.newfloat(3.5))

        output = self.run('$a = NULL; echo --$a;')
        assert self.space.is_w(output[0], self.space.w_Null)

    def test_is_true(self):
        output = self.run('if("") echo "yes"; else echo "no";')
        assert self.space.is_w(output[0], self.space.newstrconst("no"))

        output = self.run('if("0") echo "yes"; else echo "no";')
        assert self.space.is_w(output[0], self.space.newstrconst("no"))

        output = self.run('if("1") echo "yes"; else echo "no";')
        assert self.space.is_w(output[0], self.space.newstrconst("yes"))

        output = self.run('if("00") echo "yes"; else echo "no";')
        assert self.space.is_w(output[0], self.space.newstrconst("yes"))
