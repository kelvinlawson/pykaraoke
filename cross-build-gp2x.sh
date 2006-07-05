#! /bin/sh

export PATH=/gp2xsdk/Tools/bin:$PATH
export LD_LIBRARY_PATH=/gp2xsdk/Tools/lib:$LD_LIBRARY_PATH

test -d build/temp.arm-gp2x-linux || mkdir build/temp.arm-gp2x-linux
test -d build/lib.arm-gp2x-linux || mkdir build/lib.arm-gp2x-linux

arm-gp2x-linux-gcc -pthread -fno-strict-aliasing -DNDEBUG -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -D_GNU_SOURCE -fPIC -I/usr/include/python2.4 -I/gp2xsdk/installed/include/SDL -c _pycdgAux.c -o build/temp.arm-gp2x-linux/_pycdgAux.o || exit

arm-gp2x-linux-gcc -pthread -shared -L/gp2xsdk/installed/lib build/temp.arm-gp2x-linux/_pycdgAux.o -o build/lib.arm-gp2x-linux/_pycdgAux.so -lSDL || exit

