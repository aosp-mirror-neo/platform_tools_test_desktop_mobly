# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Module for the data types used in the Ethernet Legion test.
"""

from __future__ import annotations
from enum import Enum

from lib.pasit.passport import passport_host
from mobly.controllers import android_device
from mobly.controllers.android_device_lib import adb

from chromiumos.test.lab.api import pasit_host_pb2
from google.protobuf import json_format

class DongleError(Exception):
    """Base exception for dongle-related errors."""
    pass

class DongleNotFoundError(DongleError):
    """Raised when a specific dongle cannot be found."""
    pass

class InterfaceNotFoundError(DongleError):
    """Raised when a network interface for a dongle's MAC is not found."""
    pass

class EthDongle:
    """Represents a single Ethernet dongle attached to a DUT.

    Attributes:
        mac: The MAC address of the dongle.
        switch_port: The port number on the parent switch.
        switch_id: The identifier of the parent switch.
        model: The model name of the dongle.
        partner: The EthDongle instance this dongle is connected to.
        dut: The Mobly AndroidDevice controller for the DUT.
    """
    mac: str
    switch_port: str
    switch_id: str
    model: str
    partner: EthDongle | None
    dut: android_device.AndroidDevice | None

    class ConnectionState(Enum):
      CONNECTED = 0
      DISCONNECTED = 1

    class EnumerationState(Enum):
      ENUMERATED = 0
      ABSENT = 1

    # Shell command templates as class constants
    _GET_ALL_ETH_MACS_CMD = 'cat /sys/class/net/eth*/address'
    _FIND_INTERFACE_BY_MAC_CMD = (
        'for iface in /sys/class/net/*; do '
        'if [ "$(cat "$iface/address")" = "{mac}" ]; then '
        'basename "$iface"; fi; done'
    )
    _GET_INTERFACE_OPERSTATE_CMD = 'cat /sys/class/net/{interface}/operstate'

    def __init__(self, mac: str, switch_port: str, switch_id: str,
                 model: str, partner: EthDongle | None = None,
                 dut: android_device.AndroidDevice | None = None):
        self.mac = mac
        self.switch_port = switch_port
        self.switch_id = switch_id
        self.model = model
        self.partner = partner
        self.dut = dut

    def __repr__(self) -> str:
        return (f"EthDongle(mac='{self.mac}', model='{self.model}', "
                f"switch='{self.switch_id}:{self.switch_port}')")

    def _shell(self, command: str) -> str:
        """Executes a shell command on the DUT, handling potential errors."""
        if not self.dut:
            raise DongleError("DUT controller not attached to this dongle.")
        try:
            return self.dut.adb.shell(command).decode("utf-8").strip()
        except adb.AdbError as e:
            # Expected when all dongles are disconnected
            if "eth*/address: No such file or directory" in e.stderr.decode("UTF-8"):
              return ""
            raise e

    @property
    def enumeration_state(self) -> EthDongle.EnumerationState:
        """Gets the enumeration state of the dongle on the DUT."""
        all_macs = self._shell(self._GET_ALL_ETH_MACS_CMD)
        return (EthDongle.EnumerationState.ENUMERATED
                if self.mac in all_macs
                else EthDongle.EnumerationState.ABSENT)

    @property
    def interface(self) -> str:
        """Finds the network interface name (e.g., 'eth0') for this dongle."""
        cmd = self._FIND_INTERFACE_BY_MAC_CMD.format(mac=self.mac)
        interface_name = self._shell(cmd)
        if not interface_name:
            raise InterfaceNotFoundError(
                f"No interface found for dongle with MAC {self.mac}"
            )
        return interface_name

    @property
    def connection_state(self) -> EthDongle.ConnectionState:
        """Gets the operational state of the interface as a ConnectionState enum."""
        cmd = self._GET_INTERFACE_OPERSTATE_CMD.format(interface=self.interface)
        state_str = self._shell(cmd)
        return (EthDongle.ConnectionState.CONNECTED
                if state_str == 'up'
                else EthDongle.ConnectionState.DISCONNECTED)

class DongleManager:
    """Manages all Ethernet dongles defined in the testbed topology.

      Attributes:
        _dongles: A dictionary mapping MAC addresses to EthDongle objects.
        dut: The Mobly AndroidDevice controller for the DUT.
        passport: The PassportHost controller for the testbed.
        swcl: The SwitchClient instance from the PassportHost.
        topology: The PasitHost topology configuration.
    """
    _dongles: dict[str, EthDongle]
    _devices: dict[str, pasit_host_pb2.PasitHost.Device]
    dut: android_device.AndroidDevice | None
    passport: passport_host.PassportHost | None
    swcl: passport_host.PassportSwitchServiceClient | None
    topology: pasit_host_pb2.PasitHost

    def __init__(self, controller_configs: dict):
        self._dongles: dict[str, EthDongle] = {}
        self.dut: android_device.AndroidDevice | None = None
        self.passport: passport_host.PassportHost | None = None
        self.swcl = None

        topology_config = controller_configs['PassportHost'][0].get('host_topology')
        self.topology = json_format.ParseDict(
            topology_config, pasit_host_pb2.PasitHost()
        )
        self._devices = {device.id: device for device in self.topology.devices}
        self._extract_dongles()

    @property
    def dongles(self) -> list[EthDongle]:
        """Returns a list of all managed dongle objects."""
        return list(self._dongles.values())

    def attach_passport(self, passport: passport_host.PassportHost) -> None:
        """Attaches the passport controller to the manager."""
        self.passport = passport
        self.swcl = self.passport._switch_client

    def attach_dut(self, dut: android_device.AndroidDevice) -> None:
        """Attaches the DUT controller and propagates it to all dongles."""
        self.dut = dut
        for dongle in self._dongles.values():
            dongle.dut = dut

    def get_dongle_by_mac(self, mac: str) -> EthDongle:
        """Finds and returns a dongle by its MAC address."""
        dongle = self._dongles.get(mac)
        if not dongle:
            raise DongleNotFoundError(f"Failed to find dongle with MAC {mac}")
        return dongle

    def set_dongle_connect_state(self, dongle: EthDongle, state: EthDongle.ConnectionState) -> None:
        """Sets the power state of a single dongle's switch port."""
        if not self.swcl:
            raise DongleError("Switch client is not available.")
        if state == EthDongle.ConnectionState.CONNECTED:
            self.swcl.enable_switch(dongle.switch_id, dongle.switch_port)
        else:
            self.swcl.disable_switch(dongle.switch_id, dongle.switch_port)

    def set_all_dongle_connect_state(self, state: EthDongle.ConnectionState) -> None:
        """Sets the power state of all managed dongles."""
        for dongle in self._dongles.values():
            self.set_dongle_connect_state(dongle, state)

    def _extract_dongles(self) -> None:
        """Parses the topology to find and create EthDongle objects."""
        network_connections = [
            conn for conn in self.topology.connections
            if (self._devices[conn.parent_id].type ==
                pasit_host_pb2.PasitHost.Device.Type.NETWORK and
                self._devices[conn.child_id].type ==
                pasit_host_pb2.PasitHost.Device.Type.NETWORK)
        ]

        for conn in network_connections:
            parent_dev = self._devices[conn.parent_id]
            child_dev = self._devices[conn.child_id]

            switch_conn_p1 = self._get_switch_connection_for_device(conn.parent_id)
            switch_conn_p2 = self._get_switch_connection_for_device(conn.child_id)

            dongle1 = EthDongle(
                mac=conn.parent_id,
                switch_port=switch_conn_p1.parent_port,
                switch_id=switch_conn_p1.parent_id,
                model=parent_dev.model
            )
            dongle2 = EthDongle(
                mac=conn.child_id,
                switch_port=switch_conn_p2.parent_port,
                switch_id=switch_conn_p2.parent_id,
                model=child_dev.model
            )

            dongle1.partner = dongle2
            dongle2.partner = dongle1

            self._dongles[dongle1.mac] = dongle1
            self._dongles[dongle2.mac] = dongle2

    def _get_switch_connection_for_device(self, device_id: str) -> pasit_host_pb2.PasitHost.Connection:
        """Finds the switch fixture connection for a given network device."""
        for conn in self.topology.connections:
            if conn.child_id == device_id:
                parent_dev = self._devices[conn.parent_id]
                if parent_dev.type == pasit_host_pb2.PasitHost.Device.Type.SWITCH_FIXTURE:
                    return conn
        raise DongleError(
            f"Failed to get parent switch connection for device {device_id}"
        )
