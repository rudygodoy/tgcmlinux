#!/usr/bin/env python
# Copyright (C) 2009 Martin Vidner
# 
# 
# Authors:
#   Martin Vidner <martin at vidnet.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
# USA

"Convenience wrappers around dbus-python"

import dbus
import functools

# TODO rename to adaptors
from func import Adaptor, MethodAdaptor, PropertyAdaptor, SignalAdaptor

def object_path(o):
    """Return the object path of o.

    If o is a proxy object, use its appropriate attribute.
    Otherwise assume that o already is an object path.
    """
    if isinstance(o, dbus.proxies.ProxyObject):
        return o.object_path
    # hope it is ok
    return o

class DBusMio(dbus.proxies.ProxyObject):
    """Multi-interface object.

    Will look into introspection data to find which interface
    to use for a method or a property, obviating the need for
    dbus.proxies.Interface.
    If introspection is not available, provide default_interface
    to the constructor.

    BUGS: 1st method call will block with introspection"""

    def __init__(self, conn=None, bus_name=None, object_path=None, introspect=True, follow_name_owner_changes=False, **kwargs):
        """Constructor.

        kwargs may contain default_interface, to be used
        if introspection does not provide it for a method/property
        """

        self.__default_interface = kwargs.pop("default_interface", None)

        super(DBusMio, self).__init__(conn, bus_name, object_path, introspect, follow_name_owner_changes, **kwargs)

    def set_base_iface(self, iface):
	self.__base_interface = iface

    def __getattr__(self, name):
        """Proxied DBus methods.

        Uses introspection or default_interface to find the interface.
        """
        # TODO cache
#        iface = self._interface_cache.get(name)
 #       if iface == None:
        iface = self.__default_interface
        # _introspect_method_map comes from ProxyObject
        # But it will be empty until the async introspection finishes
        self._introspect_block() # FIXME makeit work with async methods
        methods = self._introspect_method_map.keys()
        for im in methods:
            (i, m) = im.rsplit(".", 1)
            if m == name:
                iface = i
#        print "METHOD %s INTERFACE %s" %(name, iface)
        callable = super(DBusMio, self).__getattr__(name)
        return functools.partial(callable, dbus_interface=iface, byte_arrays=True)

    # properties
    def __getitem__(self, key):
        """Proxies DBus properties as dictionary items.

        a = DBusMio(...)
        p = a["Prop"]

        Uses default_interface (because dbus.proxies.ProxyObject
        does not store introspection data for properties, boo. TODO.)
        """

        iface = self.__default_interface # TODO cache
	base_iface = self.__base_interface
        # TODO _introspect_property_map
        pmi = dbus.Interface(self, "org.freedesktop.DBus.Properties")
        try:
            return pmi.Get(iface, key, byte_arrays=True)
        except dbus.exceptions.DBusException, e:
            if "AccessDenied" in e.get_dbus_name():
                return pmi.Get(base_iface, key, byte_arrays=True)

    def __setitem__(self, key, value):
        """Proxies DBus properties as dictionary items.

        a = DBusMio(...)
        a["Prop"] = "Hello"

        Uses default_interface (because dbus.proxies.ProxyObject
        does not store introspection data for properties, boo. TODO.)
        """

        iface = self.__default_interface # TODO cache
        # TODO _introspect_property_map
        pmi = dbus.Interface(self, "org.freedesktop.DBus.Properties")
        pmi_res = pmi.Set(iface, key, value, byte_arrays=True)
        if not pmi_res:
            return pmi.Set(base_iface, key, value, byte_arrays=True)

def _mklist(x):
    """Return a list.

    Tuples are made into lists, everything else a singleton list.
    """
    if isinstance(x, list):
        return x
    elif isinstance(x, tuple):
        return [i for i in x]
    else:
        return [x]

class DBusClient(DBusMio):
    """
    """
    _adaptors = {
        "methods": {},
        "signals": {},
        "properties": {},
        }

    def set_base_iface(self, iface):
        super(DBusClient, self).set_base_iface(iface)
    
    @classmethod
    def _get_adaptor(cls, kind, name):
#        print "GET", cls, kind, name
        try:
            a = cls._adaptors[kind][name]
#            print ">", a
# TODO cache somehow?
            return a
        except KeyError:
            scls = cls.__mro__[1] # can use "super"? how?
            try:
                return scls._get_adaptor(kind, name)
            except AttributeError: # no _get_adaptor there
                raise KeyError(":".join((kind, name)))

    @classmethod
    def _add_adaptor(cls, kind, name, adaptor):
#        print "ADD", cls, kind, name, adaptor
        assert(isinstance(adaptor, Adaptor))
        cls._adaptors[kind][name] = adaptor

    @classmethod
    def _add_adaptors_dict(cls, andict):
        """
        a nested dictionary of kind:name:adaptor,
        """
        if not cls.__dict__.has_key("_adaptors"):
            # do not use inherited attribute
            cls._adaptors = {"methods":{}, "properties":{}, "signals":{}}

        for section in cls._adaptors.keys():
            secsource = andict.pop(section, {})
            for name, adaptor in secsource.iteritems():
                cls._add_adaptor(section, name, adaptor)
        assert len(andict) == 0
#        print "AA", cls, cls._adaptors

    @classmethod
    def _add_adaptors(cls, **kwargs):
        """kwargs: a *flat* dictionary of name: adaptor"""
        adict = {"methods":{}, "properties":{}, "signals":{}}
        for k, v in kwargs.iteritems():
            kind = v.kind()
            adict[kind][k] = v
        cls._add_adaptors_dict(adict)

    def __getattr__(self, name):
        "Wrap return values"

        callable = super(DBusClient, self).__getattr__(name)
        try:
            adaptor = self._get_adaptor("methods", name)
            return adaptor.adapt(callable)
        except KeyError:
            return callable

    # properties
    def __getitem__(self, key):
        value = super(DBusClient, self).__getitem__(key)
        try:
            adaptor = self._get_adaptor("properties", key)
            return adaptor.adapt(value)
        except KeyError:
            return value

    def __setitem__(self, key, value):
        try:
            adaptor = self._get_adaptor("properties", key)
            value = adaptor.adapt_write(value)
        except KeyError:
            pass
        return super(DBusClient, self).__setitem__(key, value)


    # signals
    # overrides a ProxyObject method
    def _connect_to_signal(self, signame, handler, interface=None, **kwargs):
        "Wrap signal handler, with arg adaptors"

        # TODO also demarshal kwargs
        adaptor = self._get_adaptor("signals", signame)
        wrap_handler = adaptor.adapt(handler)
        return self.connect_to_signal(signame, wrap_handler, interface, **kwargs)
