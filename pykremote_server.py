#******************************************************************************
#****                                                                      ****
#**** Copyright (C) 2007  Kelvin Lawson (kelvinl@users.sourceforge.net)    ****
#**** Copyright (C) 2009  PyKaraoke Development Team                       ****
#****                                                                      ****
#**** This library is free software; you can redistribute it and/or        ****
#**** modify it under the terms of the GNU Lesser General Public           ****
#**** License as published by the Free Software Foundation; either         ****
#**** version 2.1 of the License, or (at your option) any later version.   ****
#****                                                                      ****
#**** This library is distributed in the hope that it will be useful,      ****
#**** but WITHOUT ANY WARRANTY; without even the implied warranty of       ****
#**** MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU    ****
#**** Lesser General Public License for more details.                      ****
#****                                                                      ****
#**** You should have received a copy of the GNU Lesser General Public     ****
#**** License along with this library; if not, write to the                ****
#**** Free Software Foundation, Inc.                                       ****
#**** 59 Temple Place, Suite 330                                           ****
#**** Boston, MA  02111-1307  USA                                          ****
#******************************************************************************

""" This module provides the server implementation for PyKaraoke
remote communications.  This is intended to be used as a mix-in class
(for instance, for pykaraoke_mini) to add functionality to allow
some other client to control this instance's PyKaraoke window.

This "server" implementation provides the slave functionality: the
server can be controlled by the client, who is the master. """

import socket
import threading
import struct
import cPickle
import pykdb
from pykconstants import *

class RemoteSong(pykdb.SongStruct):

    def setup(self, sout):
        self.remoteSout = sout
        self.player = None

    def MakePlayer(self, *args, **kw):
        self.player = pykdb.SongStruct.MakePlayer(self, *args, **kw)
        return self.player

    def remoteClose(self):
        """ Called when the song is closed (stopped) remotely. """
        print "remoteClose"
        if self.player:
            self.player.Close()

    def doStuff(self):
        if self.player:
            self.sendRemoteCommand('setPos', self.player.GetPos(), self.player.GetLength())
    
    def doPlay(self):
        print "doPlay"
        self.sendRemoteCommand('doPlay')

    def doPause(self): 
        self.sendRemoteCommand('doPause')

    def doUnpause(self):
        self.sendRemoteCommand('doUnpause')

    def doRewind(self):
        self.sendRemoteCommand('doRewind')

    def doClose(self):
        self.sendRemoteCommand('doClose')
        self.player = None

    def sendRemoteCommand(self, command, *args):
        """ Sends the indicated command and its matching args to the
        connected client. """

        data = cPickle.dumps((command, args))
        length = len(data)
        header = struct.pack('L', length)
        self.remoteSout.write(header)
        self.remoteSout.write(data)
        self.remoteSout.flush()

class pykServer:
    def __init__(self):
        self.serverRunning = True
        self.rendezvous = None
        self.serverThread = None
        self.clientThreads = {}

        self.pendingSongs = []

    def activateServer(self, manager):
        """ Opens a socket to listen for connections from clients.
        Returns None on success, or an error message on failure. """
        
        assert not self.rendezvous
        assert not self.serverThread

        print "activateServer: %s" % (socket.gethostname())
        self.rendezvous = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rendezvous.bind(('', manager.options.remote_port))
        except socket.error, e:
            print e
            return e.strerror
        
        self.rendezvous.listen(5)

        self.serverThread = threading.Thread(target = self.__serverThread)
        self.serverThread.daemon = True
        self.serverThread.start()

        return None

    def closeServer(self):
        self.serverRunning = False
        if self.rendezvous:
            self.rendezvous.close()
            self.rendezvous = None
        self.clientThreads = {}
            
    def checkRemoteSongs(self):
        """ Call this when idle to see if a song request has been
        received from a client.  Returns a SongStruct if so, or None
        if there are no songs ready. """

        if self.pendingSongs:
            song = self.pendingSongs[0]
            del self.pendingSongs[0]
            return song
        return None

    def __serverThread(self):
        while self.serverRunning:
            (sock, address) = self.rendezvous.accept()
            print "Got connection from %s" % (address,)
            thread = threading.Thread(target = self.__clientThread,
                                      args = (sock,))
            thread.daemon = True
            self.clientThreads[socket] = thread
            thread.start()
        self.rendezvous.close()

    def __clientThread(self, sock):
        # Open the socket as a pair of I/O streams.
        sin = sock.makefile('rb')
        sout = sock.makefile('wb')

        rsong = None
        while self.serverRunning:
            try:
                header = sin.read(4)
            except socket.error:
                break
            
            if not header:
                break
            
            length = struct.unpack('L', header)[0]
            try:
                data = sin.read(length)
            except socket.error:
                break

            # Yeah, we blindly trust the received data and unpack it
            # as a pickle stream.  Foolish, yeah, yeah.  This is
            # temporary.
            command, args = cPickle.loads(data)
            if command == 'play' or command == 'close':
                if rsong:
                    rsong.remoteClose()
                    try:
                        self.pendingSongs.remove(rsong)
                    except ValueError:
                        pass
                    rsong = None

            if command == 'play':
                rsong = args[0]
                # Cheesy hack: change the songfile's class
                rsong.__class__ = RemoteSong
                rsong.setup(sout)
                self.pendingSongs.append(rsong)

        # Exit the client.
        try:
            del self.clientThreads[sock]
        except KeyError:
            pass
        
