#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Authors : Roberto Majadas <roberto.majadas@openshine.com>
#
# Copyright (c) 2010, Telefonica Móviles España S.A.U.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#

import os
import sys

from freedesktopnet.networkmanager.utils.tool import Command, make_option
from freedesktopnet.networkmanager.networkmanager import NetworkManager

class Devices(Command):

    def config_cmd(self):
        self.name = "devices"
        self.description = "List Network Manager devices"
        self.description_full = "List Network Manager devices"
        
        self.options_list = [
            make_option("-v", "--verbose",
                        action="store_true", dest="verbose", default=False)
            ]

    def run_cmd(self):
        nm = NetworkManager()

        if self.options.verbose == False :
            for dev in nm.GetDevices() :
                print "%s" % dev["Interface"]
        else:
            props = ["Udi", "Interface", "Driver", "Capabilities", 
                     "State", "Managed", "DeviceType"]
            
            for dev in nm.GetDevices() :
                print "%s |" % dev["Interface"]
                print "-" * len(dev["Interface"]) + "-+"
                for p in props:
                    print "%s : %s" % (p.upper(), dev[p])
                print "\n"
                
                
