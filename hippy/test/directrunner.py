
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

def parse_array(space, i, lines, lgt):
    pairs = []
    for k in range(lgt):
        line = lines[i].strip()
        assert line.endswith('=>')
        if line[1] == '"':
            w_key = space.newstrconst(line[2:-4])
        else:
            w_key = space.wrap(int(line[1:-3]))
        w_value, i = parse_single(space, i + 1, lines)
        pairs.append((w_key, w_value))
    return space.new_array_from_pairs(pairs), i + 1

def parse_single(space, i, lines):
    line = lines[i].strip()
    if line.startswith('int'):
        return space.wrap(int(line[len('int('):-1])), i + 1
    elif line.startswith('bool'):
        return space.wrap(line[len('bool('):-1] == 'true'), i + 1
    if line.startswith('float'):
        return space.wrap(float(line[len('float('):-1])), i + 1
    elif line == 'NULL':
        return space.w_Null, i + 1
    elif line.startswith('array'):
        lgt = int(line[len('array') + 1:line.find(')')])
        return parse_array(space, i + 1, lines, lgt)
    elif line.startswith('string'):
        lgt = int(line[len('string') + 1:line.find(')')])
        return space.newstrconst(line[line.find('"') + 1:-1]), i + 1
    else:
        raise Exception("unsupported line %s" % line)

def parse_result(space, stdout):
    lines = stdout.splitlines()
    output = []
    i = 0
    while i < len(lines):
        next, i = parse_single(space, i, lines)
        output.append(next)
    return output

def run_source(space, source):
    php_source = source_replace(source)
    stdout = run_php_source(space, php_source)
    return parse_result(space, stdout)

def run_php_source(space, php_source):
    f = tempfile.NamedTemporaryFile()
    py.path.local(f.name).write(php_source)
    pipe = subprocess.Popen(['php', f.name], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    if pipe.returncode or stderr:
        raise Exception("Got %s %s" % (stderr, stdout))
    return stdout
