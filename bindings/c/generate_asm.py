#!/usr/bin/env python
#
# generate_asm.py
#
# This source file is part of the FoundationDB open source project
#
# Copyright 2013-2018 Apple Inc. and the FoundationDB project authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import re
import sys

(os, cpu, source, asm, h) = sys.argv[1:]

functions = {}

func_re = re.compile(
    "^\s*FDB_API_(?:CHANGED|REMOVED)\s*\(\s*([^,]*),\s*([^)]*)\).*")

with open(source, 'r') as srcfile:
    for l in srcfile:
        m = func_re.match(l)
        if m:
            func, ver = m.groups()
            if func not in functions:
                functions[func] = []
            ver = int(ver)
            if ver not in functions[func]:
                functions[func].append(ver)


def write_windows_asm(asmfile, functions):
    asmfile.write(".data\n")
    for f in functions:
        asmfile.write("\textern fdb_api_ptr_%s:qword\n" % f)

    asmfile.write("\n.code\n")

    for f in functions:
        asmfile.write("\n%s proc EXPORT\n" % f)
        asmfile.write("\tmov r11, qword ptr [fdb_api_ptr_%s]\n" % f)
        asmfile.write("\tjmp r11\n")
        asmfile.write("%s endp\n" % f)

    asmfile.write("\nEND\n")


def write_unix_asm(asmfile, functions, prefix):
    if cpu != "aarch64" and cpu!= "ppc64le":
        asmfile.write(".intel_syntax noprefix\n")

    if cpu == 'aarch64' or os == 'linux' or os == 'freebsd':
        asmfile.write("\n.data\n")
        for f in functions:
            asmfile.write("\t.extern fdb_api_ptr_%s\n" % f)
        
        if os == 'linux' or os == 'freebsd':
            asmfile.write("\n.text\n")
            for f in functions:
                asmfile.write("\t.global %s\n\t.type %s, @function\n" % (f, f))

    for f in functions:
        asmfile.write("\n.globl %s%s\n" % (prefix, f))
        asmfile.write("%s%s:\n" % (prefix, f))

        # These assembly implementations of versioned fdb c api functions must have the following properties.
        #
        # 1. Don't require dynamic relocation.
        #
        # 2. Perform a tail-call to the function pointer that works for a
        #    function with any number of arguments. For example, since registers x0-x7 are used
        #    to pass arguments in the Arm calling convention we must not use x0-x7
        #    here.
        #
        # You can compile this example c program to get a rough idea of how to
        # load the extern symbol and make a tail call.
        #
        # $ cat test.c
        # typedef int (*function)();
        # extern function f;
        # int g() { return f(); }
        # $ cc -S -O3 -fPIC test.c && grep -A 10 '^g:' test.[sS]
        # g:
        # .LFB0:
        # 	.cfi_startproc
        # 	adrp	x0, :got:f
        # 	ldr	x0, [x0, #:got_lo12:f]
        # 	ldr	x0, [x0]
        # 	br	x0
        # 	.cfi_endproc
        # .LFE0:
        # 	.size	g, .-g
        # 	.ident	"GCC: (GNU) 8.3.1 20190311 (Red Hat 8.3.1-3)"

        p = ''
        if os == 'osx':
            p = '_'
        if cpu == "aarch64":
            asmfile.write("\tldr x16, =%sfdb_api_ptr_%s\n" % (p, f))
            if os == 'osx':
                asmfile.write("\tldr x16, [x16]\n")
            else:
                asmfile.write("\tldr x8, [x8, #:got_lo12:fdb_api_ptr_%s]\n" % (f))
                asmfile.write("\tldr x8, [x8]\n")
            asmfile.write("\tbr x8\n")
        else:
            asmfile.write(
                "\tmov r11, qword ptr [%sfdb_api_ptr_%s@GOTPCREL+rip]\n" % (prefix, f))
            asmfile.write("\tmov r11, qword ptr [r11]\n")
            asmfile.write("\tjmp r11\n")


with open(asm, 'w') as asmfile:
    with open(h, 'w') as hfile:
        hfile.write(
            "void fdb_api_ptr_unimpl() { fprintf(stderr, \"UNIMPLEMENTED FDB API FUNCTION\\n\"); abort(); }\n\n")
        hfile.write(
            "void fdb_api_ptr_removed() { fprintf(stderr, \"REMOVED FDB API FUNCTION\\n\"); abort(); }\n\n")

        if os == 'linux':
            write_unix_asm(asmfile, functions, '')
        elif os == "osx":
            write_unix_asm(asmfile, functions, '_')
        elif os == "windows":
            write_windows_asm(asmfile, functions)

        for f in functions:
            if os == "windows":
                hfile.write("extern \"C\" ")
            hfile.write("void* fdb_api_ptr_%s = (void*)&fdb_api_ptr_unimpl;\n" % f)
            for v in functions[f]:
                hfile.write("#define %s_v%d_PREV %s_v%d\n" % (f, v, f, v - 1))
