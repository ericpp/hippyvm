Prototype PHP interpreter using the PyPy toolchain - Hippy VM
=============================================================

Hello everyone.

I'm proud to release the result of a Facebook-sponsored study on feasibility of
using the RPython toolchain to produce a PHP interpreter. The rules were
simple: two months, one person, get as close to PHP as possible, implementing
enough warts and corner cases to be reasonably sure that it answers hard
problems in the PHP language. The outcome is called ``Hippy VM`` and implements
most of the PHP 1.0 language (functions, arrays, ints, floats and strings).
This should be considered an alpha release.

The resulting interpreter is obviously incomplete – it does not support all
modern PHP constructs (classes are completely unimplemented), builtin functions,
grammar productions, web server integration, builtin libraries
etc., etc.. It's **just** enough to be able to reasonably
say that given some engineering effort, it's possibly to provide a rock-solid
and fast PHP VM using PyPy technologies.

The results is available in a `bitbucket repo`_ and is available under MIT
license.

.. _`bitbucket repo`: https://bitbucket.org/fijal/hippyvm


Performance
-----------

Below is a table comparing a few benchmarks on `Zend`_ 5.3.2
(Zend Enginve v2.3.0), a standard PHP interpreter available on Linux releases,
`HipHop VM`_, a php-to-C++
optimizing compiler developed by Facebook,
as of heads/vm-0-ga4fbb08028493df0f5e44f2bf7c042e859e245ab (note that you need
to check out the ``vm`` branch to get the newest version).
The run was performed on a 64-bit Linux running on Xeon W3580 with 8M of
L2 cache, which was otherwise unoccupied. Hippy version is marked in the
repository as ``release-0.1``.

Unfortunately, I was not able to run it on the jitted version of HHVM, the new effort by Facebook,
but people involved with the project told me it's usually slower or comparable with the compiled HipHop.
Their JITted VM is still alpha software, so I'll update it as soon as I have the info.

.. _`Zend`: http://www.zend.com
.. _`HipHop VM`: https://github.com/facebook/hiphop-php

  +---------------+--------+-----------+-----------+--------------+----------------+
  | benchmark     | zend   | HipHop VM | hippy VM  | hippy / zend | hippy / HipHop |
  +---------------+--------+-----------+-----------+--------------+----------------+
  | arr           | 2.771  | 0.508+-0% | 0.274+-0% | 10.1x        | 1.8x           |
  +---------------+--------+-----------+-----------+--------------+----------------+
  | fannkuch      | 21.239 | 7.248+-0% | 1.377+-0% | 15.4x        | 5.3x           |
  +---------------+--------+-----------+-----------+--------------+----------------+
  | heapsort      | 1.739  | 0.507+-0% | 0.192+-0% | 9.1x         | 2.6x           |
  +---------------+--------+-----------+-----------+--------------+----------------+
  | binary_trees  | 3.223  | 0.641+-0% | 0.460+-0% | 7.0x         | 1.4x           |
  +---------------+--------+-----------+-----------+--------------+----------------+
  | cache_get_scb | 3.350  | 0.614+-0% | 0.267+-2% | 12.6x        | 2.3x           |
  +---------------+--------+-----------+-----------+--------------+----------------+
  | fib           | 2.357  | 0.497+-0% | 0.021+-0% | 111.6x       | 23.5x          |
  +---------------+--------+-----------+-----------+--------------+----------------+
  | fasta         | 1.499  | 0.233+-4% | 0.177+-0% | 8.5x         | 1.3x           |
  +---------------+--------+-----------+-----------+--------------+----------------+

The PyPy compiler toolchain provides a way to implement a dynamic
language interpreter in a high level language called RPython. This is
a language that's lower level that Python, but still higher level than
C or C++, for example RPython is a garbage collected language. The killer
feature is that the toolchain will generate a JIT for the interpreter
written in RPython, which is able to leverage most of the work that has been
done on speeding up Python in the PyPy project. The resulting JIT is generated for
your interpreter and it's not Python-specific. This is was one of the
original design decisions, unlike say JVM, which was primarily used to
interpret only Java and later adjusted to serve as a platform for
dynamic languages. Another important difference is that there is no common
bytecode to which you compile your language and Python, so you don't inherit
problems presented when implementing language X on top of, say, `Parrot VM`_ or the JVM.
You have still to implement your interpreter, however in a high level language
that gives you such features as Garbage Collection and Just in Time
compiliation, without sacrificing language decisions to fit more in the
Python (or Parrot or JVM) landscape.

To read more about creating your own interpreters using the PyPy toolchain,
read `more`_ `blog posts`_ or an `excellent article`_ by Laurence Tratt.

.. _`more`: http://morepypy.blogspot.com/2011/04/tutorial-writing-interpreter-with-pypy.html
.. _`blog posts`: http://morepypy.blogspot.com/2011/04/tutorial-part-2-adding-jit.html
.. _`excellent article`: http://tratt.net/laurie/tech_articles/articles/fast_enough_vms_in_fast_enough_time
.. _`Parrot VM`: http://www.parrot.org/

PHP deviations
--------------

Probably the biggest deviation from this project and the PHP specification is
that GC is no longer reference counting. That means that the object finalizer, when
implemented, will not be called directly at the moment of object death, but
at some later point. There are possible future developments to alleviate that
problem, by providing "refcounted" objects when leaving the current scope.
Research has to be done in order to achieve that.

Assessment
----------

The RPython toolchain seems to be a cost-effective choice for writing
dynamic language VMs.  It provides both a fast JIT and gives you
access to low level primitives when you need them. A good example is
in the directory ``hippy/rpython`` which contains the implementation
of an ordered dictionary. An ordered dictionary is not a primitive
that RPython provides – it's not necessary for the goal of
implementing Python.  Now implementing it on top of normal dictionary
is possible, but inefficient. RPython provides a way to go and play
directly with low level, if you desire so.

Things that require improvements in RPython:

* Lack of mutable string on the RPython level ended up being a problem.
  I ended up using lists of characters which are efficient, but inconvinient,
  since they don't support any string methods.

* Frame handling is too conservative and too Python specific, especially around
  the calls. It's possible to implement less-general, but simpler and faster
  frame handling implementation in RPython.

Status of the implementation
----------------------------

Don't use it! It's a research prototype intended to asses the feasibility
of using RPython to create dynamic language VMs. The most notable
feature that's missing is a reasonable error reporting. That said, I'm
confident it implements enough of PHP language to prove that the full
implementation will present the same performance characteristics.

Benchmarks
----------

The benchmarks are a selection of computer language shootout benchmarks as well
as ``cache_get_scb`` which is a part of old Facebook code . Other than this one
(which is not open source, but definitely the most interesting one :(), they're
available in the ``bench`` directory. The Python program to run them is called
``runner.py`` in the same directory. It runs them 10 times, cutting of the first
3 runs (ignoring the JIT warmup time) and averaging the rest. As you can see
the standard deviation is fairly minimal for all interpreters and runs, in case
it's ommited it means it's below 0.5%.

The benchmark selection is not what's easy to optimize, but the optimizations
in the interpreter were written specifically for the set of benchmarks. There
were no special JIT optimizations added and barring what's mentioned below
vanilla pypy 1.9 checkout was used for compilation.


So, how fast will my website run if this is complete?
-----------------------------------------------------

The truth is - I lack benchmarks to be able to prove it right now. The core
of the PHP language is implemented up to the point where I'm confident
the performance will not change as we get more of the PHP going.

How do I run it?
----------------

Get a `pypy checkout`_, apply the `diff`_ if you want to squeeze last
bits of performance and run ``pypy-checkout/bin/rpython -Ojit targethippy.py`` to
get an executable that resembles a php interpreter. You can also run directly
``python targethippy.py file.php``, but this will be about 2000x slower.

RPython modifications
-----------------------

There were a modification that I did to the pypy source code, the `diff`_
is available. It's trivial and should be made simply optional in the
RPython JIT generator, but it was easier to just do it, given the very constrained time
frame.

* ``gen_store_back_in_virtualizable`` was disabled. This feature is
  necessary for Python frames but not for PHP frames. PHP frames
  do not have to be kept alive after we exit a function.

.. _`diff`: https://gist.github.com/2923845

Future
------

Hippy is a cool prototype that presents a very interesting path towards a fast
PHP VM.  However, at the moment I have too many other open source commitments
to take on the task of completing it in my spare time.  I do think this project
has a lot of potential, but I will not commit to any further development at
this time.  If you send pull requests I'll try to review them.  I'm also open
to having further development on this project funded, so if you're interested
in this project and the potential of a fast PHP interpreter, please get in
touch.

Cheers,
fijal
