
import py
import subprocess
import tempfile

def source_replace(source):
    # replace all echos with var_dumps so we know what we're doing
    reslines = ["<?\n"]
    for line in source.splitlines():
        line = line.strip()
        if line.startswith("echo "):
            assert line.endswith(';')
            line = "var_dump(" + line[len("echo "):-1] + ");"
        reslines.append(line)
    reslines.append("\n?>\n")
    return "\n".join(reslines)

def parse_single(space, i, lines, output):
    line = lines[i]
    if line.startswith('int'):
        output.append(space.wrap(int(line[len('int('):-1])))
    else:
        raise Exception("unsupported line %s" % line)


def parse_result(space, stdout):
    lines = stdout.splitlines()
    output = []
    i = 0
    while i < len(lines):
        i = parse_single(space, i, lines, output)
    return output

def run_source(space, source):
    php_source = source_replace(source)
    f = tempfile.NamedTemporaryFile()
    py.path.local(f.name).write(php_source)
    pipe = subprocess.Popen(['php', f.name], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    pipe.wait()
    stderr = pipe.stderr.read()
    stdout = pipe.stdout.read()
    if pipe.returncode or stderr:
        raise Exception("Got %s %s" % (stderr, stdout))
    return parse_result(space, stdout)
