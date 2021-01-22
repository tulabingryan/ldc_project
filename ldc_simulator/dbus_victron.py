#! /usr/bin/python
# by: http://en.opensuse.org/User:Mvidner
# license: http://creativecommons.org/licenses/by/3.0/
#
# Portions Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Distributed under the Creative Commons CCPL-Attribution-3.0 License.
#
# original can be found at:
# http://vidner.net/martin/software/dbus-spy/dbus-spy-0.1.py
# based on http://alban.apinc.org/blog/dbusmessagesboxpy/
VERSION = "0.1-cros"
print "dbus-spy %s: monitor, recorder, chart generator" % VERSION
norpm = False
import sys
import os
import time
from optparse import OptionParser
try:
    import dbus
    import dbus.service
    import _dbus_bindings
except:
    print "Install dbus-1-python.rpm"
    norpm = True
try:
    import gobject
except:
    print "Install python-gobject2.rpm"
    norpm = True
# python-gnome.rpm has gconf for nm-applet...
if norpm:
    sys.exit(1)
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)
# distinguish msgo: message object, and msgd: message dictionary (made from the object)
class Output:
    def start(self):
        pass
    def msgd_handler(self, msgd):
        pass
    def stop(self):
        pass
# now unused
def msgo_dumper(m):
    print "MSG -------"
    print "type", m.get_type()
    print "destination", m.get_destination()
    print "sender", m.get_sender()
    print "path", m.get_path()
    print "interface", m.get_interface()
    print "member", m.get_member()
    print "signature", m.get_signature()
    print "args_list", m.get_args_list()
    print "auto_start", m.get_auto_start()
    print "error_name", m.get_error_name()
    print "no_reply", m.get_no_reply()
    print "reply_serial", m.get_reply_serial()
    print "serial", m.get_serial()
def msgd_dumper(m):
    print "MSG -------", m["TIME"]
    print "type", m["type"]
    print "destination", m["destination"]
    print "sender", m["sender"]
    print "path", m["path"]
    print "interface", m["interface"]
    print "member", m["member"]
    print "signature", m["signature"]
    print "args_list", m["args_list"]
    print "auto_start", m["auto_start"]
    print "error_name", m["error_name"]
    print "no_reply", m["no_reply"]
    print "reply_serial", m["reply_serial"]
    print "serial", m["serial"]
TYPE = ["-", "Call", "Return", "Error", "Signal",]
ARROW = ["?", "=>", ">>", "=>>", "=>*",]
def default(abbr, val, defval):
    if (val != defval):
        return "%s: %s" % (abbr, val)
    else:
        return ""
    
def msgd_printer(m):
    print m["TIME"], TYPE[m["type"]], default("S", m["serial"], 0), default("RS", m["reply_serial"], 0), default("NR", m["no_reply"], False), \
        m["sender"], "->", m["destination"], default("AS", m["auto_start"], True), default("ERR", m["error_name"], None)
    print "  ", m["path"], "%s.%s(%s) ((%s))" % (m["interface"], m["member"], ",".join(map(str, m["args_list"])), m["signature"])
class Handler(Output):
    def __init__(self, msgd_handler):
        """msgd_handler: callable"""
        self.msgd_handler = msgd_handler
class Chart(Output):
    def __init__(self, fname):
        self.fname = fname
    def start(self):
        self.seen = {}
        self.names = {}
        self.serials = {}
        self.msgs = []
        self.lines = []
    def sniff(self, m):
        """infer more info about bus traffic"""
        src = m["sender"]
        dest = m["destination"]
        serial = m["serial"]
        rserial = m["reply_serial"]
        ifc = m["interface"]
        call =  m["member"]
        args = m["args_list"]
        if ifc == "org.freedesktop.DBus":
            if TYPE[m["type"]] == "Signal":
                if call == "NameOwnerChanged":
                    (nname, nfrom, nto) = args
                    #print "NOC '%s'\t%s->%s" % (nname, nfrom, nto)
                elif call == "NameAcquired":
                    nname = args[0]
                    #print "NA '%s'" % nname
            # TODO get replies to
            # calls GetNameOwner, RequestName, NameHasOwner
            elif TYPE[m["type"]] == "Call":
                if call == "GetNameOwner":
                    #print "GNO", args
                    pass
                elif call == "RequestName":
                    #print "RN", args
                    self.names[src] = args[0]
        # remember serial number if name is interesting
        if TYPE[m["type"]] == "Call":
            if serial != 0 and self.interesting_name(dest):
                self.serials.setdefault(src, {})
                self.serials[src][serial] = dest
                #print "INTERESTING:", src, serial, dest
        # match by reply serial numbers
        if rserial != 0:
            try:
                self.names[src] = self.serials[dest][rserial]
            except:
                print "REPLY?! %s = (%s,%d)" % (src, dest, rserial)
    def interesting_name(self, conn):
        return not self.names.has_key(conn) and conn[0] != ":"
    def name(self, conn):
        return self.names.get(conn, conn)
    def msgd_handler(self, m):
        self.msgs.append(m)          # store because the names will only be known later
        #print ".",
        self.sniff(m)
    def post_msgd_handler(self, m):
        src = self.name(m["sender"])
        dest = self.name(m["destination"])
        self.seen[src] = True
        if dest != None:
            self.seen[dest] = True
        arrow = ARROW[m["type"]]
        T = TYPE[m["type"]]
        if T == "Signal":
            dest = ""
        else:
            dest = '"%s"' % dest
        label = m["member"]
        if T == "Error":
            label = m["error_name"]
        elif T == "Return":
            r = m["args_list"]
            if len(r) == 0:
                label = "."
            else:
                label = repr(r[0]).replace('"', '||')
        label = label[:333]
        line = '"%s" %s %s [ label = "%s" ];\n' % (src, arrow, dest, label)
        self.lines.append(line)
    def stop(self):
        for m in self.msgs:
            self.post_msgd_handler(m)
        self.f = open(self.fname, "w")
        # TODO comment inside f
        self.f.write("msc {\n")
#        names = map(lambda s: s.replace(".", "\\n"), sorted(self.seen.keys()))
        names = self.seen.keys()
        self.f.write("  %s;\n" % ",".join('"%s"' % d for d in names))
        for l in self.lines:
            self.f.write(l)
        self.f.write("}\n")
        self.f.close()
        
class Recorder(Output):
    def __init__(self, fname):
        self.fname = fname
    def start(self):
        self.f = open(self.fname, "a")
        # TODO comment inside f
    def msgd_handler(self, msgd):
        self.f.write(str(msgd)+",\n")
    def stop(self):
        self.f.close()

class Filter(Output):
    def __init__(self, filter, out):
        self.filter = filter
        self.out = out
    def start(self):
        self.out.start()
    def msgd_handler(self, msgd):
        if self.match(msgd):
            self.out.msgd_handler(msgd)
    def stop(self):
        self.out.stop()
    def match(self, msgd):
        # quick and dirty: match substring in msgd python representation
        return repr(msgd).find(self.filter) != -1

class NotFilter(Filter):
    def msgd_handler(self, msgd):
        if not self.match(msgd):
            self.out.msgd_handler(msgd)

class Input:
    def start(self):
        pass
    def run(self):
        #print self.__class__
        self.start()
        self.out.start()
        self.run_inner()
        self.out.stop()
        self.stop()
    def run_inner(self):
        pass
    def stop(self):
        pass

class Monitor(Input):
    def __init__(self, which_bus, out):
        """which_bus: "system" or "session"
        out: Output"""
        if which_bus == "system":
            self.bus = dbus.SystemBus()
        else:
            self.bus = dbus.SessionBus()
        self.out = out
    def start(self):
        self.bus.add_match_string("")
        self.bus.add_message_filter(self.msg_filter)
    def stop(self):
        self.bus.remove_message_filter(self.msg_filter)
        self.bus.remove_match_string("")
    def msgd_maker(self, m):
        items = ["args_list", "auto_start", "destination", "error_name",
                 "interface", "member", "no_reply", "path", "reply_serial",
                 "sender", "serial", "signature", "type",]
        # TODO make more efficient by compile()
        c = "{\n"
        for i in items:
            c = c + " '%s': m.get_%s(),\n" % (i, i)
        c = c + "}\n"
        try:
            dump = eval(c)
        except Exception, e:
            print c
            print e
        dump["TIME"] = time.time()
        return dump    
    # msg is dbus.lowlevel.Message
    def msg_filter(self, abus, msg):
        try:
            msgd = self.msgd_maker(msg)
            self.out.msgd_handler(msgd)
        # exceptions in signal handlers are eaten by the bindings,
        # so we better do something ourselves
        # http://bugs.freedesktop.org/show_bug.cgi?id=9980
        except Exception, e:
            print e
    def run_inner(self):
        loop = gobject.MainLoop()
        print "Press Ctrl-C to stop."
        try:
            loop.run()
        except:
            print " Loop exited"

DBUS_MESSAGE_TYPE_METHOD_CALL = 1
DBUS_MESSAGE_TYPE_METHOD_RETURN = 2
DBUS_MESSAGE_TYPE_ERROR = 3
DBUS_MESSAGE_TYPE_SIGNAL = 4

class Reader(Input):
    def __init__(self, fname, out):
        self.f = open(fname, "r")
        self.out = out
        try:
            slurp = self.f.read()
            self.messages = eval("[%s]" % slurp) # TODO! protect from evil code
        except Exception, e:
            print e
            self.messages = []
    # reconstructing messages is too hard. let's work with dicts instead
    @staticmethod
    def newmsg(msg_d):
        print repr(msg_d)
        print msg_d.__class__
        t = msg_d["type"]
        if t == DBUS_MESSAGE_TYPE_METHOD_CALL:
            msg = dbus.lowlevel.MethodCallMessage(**msg_d)
        elif t == DBUS_MESSAGE_TYPE_METHOD_RETURN:
            msg = dbus.lowlevel.MethodReturnMessage(**msg_d)
        elif t == DBUS_MESSAGE_TYPE_ERROR:
            msg = dbus.lowlevel.ErrorMessage(**msg_d)
        elif t == DBUS_MESSAGE_TYPE_SIGNAL:
            msg = dbus.lowlevel.SignalMessage(path=msg_d["path"],
                                              interface=msg_d["interface"],
                                              method=msg_d["member"])
        for k, v in msg_d.iteritems():
            eval("msg.set_%s(v)" % k)
        return msg
    def run_inner(self):
        for msg_d in self.messages:
            self.out.msgd_handler(msg_d)

op = OptionParser()
# INPUT
op.add_option("-b", "--bus", dest="bus",
              help="monitor messages from the bus")
op.add_option("-r", "--read", dest="read",
              help="read messages from file")
# OUTPUT
op.add_option("-d", "--dump", dest="dump", action="store_true", default=False,
              help="dump seen messages")
op.add_option("-p", "--print", dest="printer", action="store_true", default=False,
              help="print seen messages")
op.add_option("-w", "--write", dest="writeto",
              help="write seen messages to file")
op.add_option("-c", "--chart", dest="chart",
              help="write MSC chart to file")
# FILTERS - TODO
op.add_option("-f", "--filter", dest="filter",
              help="pass only matching messages")
op.add_option("-F", "--notfilter", dest="notfilter",
              help="pass only nonmatching messages")
(options, args) = op.parse_args()

# TODO multiple outputs: multiplexer(fork)
if options.dump:
    out = Handler(msgd_dumper)
elif options.chart != None:
    out = Chart(options.chart)
elif options.writeto != None:
    out = Recorder(options.writeto)
elif options.printer:
    out = Handler(msgd_printer)
else:
    print "Default output: pretty printer"
    out = Handler(msgd_printer)

# TODO better chaining, multiple filters of same kind
if options.filter != None:
    out = Filter(options.filter, out)
if options.notfilter != None:
    out = NotFilter(options.notfilter, out)
if options.bus != None:
    input = Monitor(options.bus, out)
elif options.read != None:
    input = Reader(options.read, out)
else:
    print "Default input: system monitor"
    input = Monitor("system", out)
input.run()