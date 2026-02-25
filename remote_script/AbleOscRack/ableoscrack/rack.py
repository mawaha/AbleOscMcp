from typing import Tuple, Any
from .handler import AbletonOSCHandler


class RackHandler(AbletonOSCHandler):
    """OSC handler for Rack chain traversal.

    Exposes OSC addresses for navigating into Instrument Racks, Audio Effect
    Racks, and Drum Racks — structures that AbletonOSC's DeviceHandler does
    not reach.

    Address conventions (mirrors AbletonOSC):

        /live/rack/get/...                  — rack-level  (track_idx, device_idx)
        /live/rack/get/chain/...            — chain-level (track_idx, device_idx, chain_idx)
        /live/rack/get/chain/device/...     — nested dev  (track_idx, device_idx, chain_idx, nested_dev_idx)
        /live/rack/set/chain/device/...     — set nested  (... + param_idx + value)

    All responses are prefixed with the same index tuple used in the request,
    matching AbletonOSC's convention (e.g. device-level responses are prefixed
    with track_index and device_index).
    """

    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "rack"

    def init_api(self):

        # ----------------------------------------------------------------
        # Callback factories
        # ----------------------------------------------------------------

        def create_rack_callback(func, *args):
            """Factory for rack-level callbacks: params = (track_idx, device_idx, ...)."""
            def callback(params: Tuple[Any]):
                track_index = int(params[0])
                device_index = int(params[1])
                device = self.song.tracks[track_index].devices[device_index]
                rv = func(device, *args, params[2:])
                if rv is not None:
                    return (track_index, device_index, *rv)
            return callback

        def create_chain_callback(func, *args):
            """Factory for chain-level callbacks: params = (track_idx, device_idx, chain_idx, ...)."""
            def callback(params: Tuple[Any]):
                track_index = int(params[0])
                device_index = int(params[1])
                chain_index = int(params[2])
                device = self.song.tracks[track_index].devices[device_index]
                chain = device.chains[chain_index]
                rv = func(chain, *args, params[3:])
                if rv is not None:
                    return (track_index, device_index, chain_index, *rv)
            return callback

        def create_chain_device_callback(func, *args):
            """Factory for nested-device callbacks: params = (track_idx, device_idx, chain_idx, dev_idx, ...)."""
            def callback(params: Tuple[Any]):
                track_index = int(params[0])
                device_index = int(params[1])
                chain_index = int(params[2])
                nested_device_index = int(params[3])
                device = self.song.tracks[track_index].devices[device_index]
                nested_device = device.chains[chain_index].devices[nested_device_index]
                rv = func(nested_device, *args, params[4:])
                if rv is not None:
                    return (track_index, device_index, chain_index, nested_device_index, *rv)
            return callback

        # ----------------------------------------------------------------
        # Rack-level handlers
        # ----------------------------------------------------------------

        def rack_get_num_chains(device, params=()):
            return len(device.chains),

        def rack_get_chains_name(device, params=()):
            return tuple(chain.name for chain in device.chains)

        def rack_get_chains_color(device, params=()):
            return tuple(chain.color for chain in device.chains)

        def rack_get_chains_mute(device, params=()):
            return tuple(int(chain.mute) for chain in device.chains)

        def rack_get_chains_can_have_chains(device, params=()):
            """Returns whether each device in the chain is itself a rack."""
            result = []
            for chain in device.chains:
                for nested in chain.devices:
                    result.append(int(nested.can_have_chains))
            return tuple(result)

        self.osc_server.add_handler("/live/rack/get/num_chains",
                                    create_rack_callback(rack_get_num_chains))
        self.osc_server.add_handler("/live/rack/get/chains/name",
                                    create_rack_callback(rack_get_chains_name))
        self.osc_server.add_handler("/live/rack/get/chains/color",
                                    create_rack_callback(rack_get_chains_color))
        self.osc_server.add_handler("/live/rack/get/chains/mute",
                                    create_rack_callback(rack_get_chains_mute))

        # ----------------------------------------------------------------
        # Chain-level handlers
        # ----------------------------------------------------------------

        def chain_get_num_devices(chain, params=()):
            return len(chain.devices),

        def chain_get_devices_name(chain, params=()):
            return tuple(device.name for device in chain.devices)

        def chain_get_devices_type(chain, params=()):
            return tuple(device.type for device in chain.devices)

        def chain_get_devices_class_name(chain, params=()):
            return tuple(device.class_name for device in chain.devices)

        def chain_get_devices_can_have_chains(chain, params=()):
            return tuple(int(device.can_have_chains) for device in chain.devices)

        self.osc_server.add_handler("/live/rack/get/chain/num_devices",
                                    create_chain_callback(chain_get_num_devices))
        self.osc_server.add_handler("/live/rack/get/chain/devices/name",
                                    create_chain_callback(chain_get_devices_name))
        self.osc_server.add_handler("/live/rack/get/chain/devices/type",
                                    create_chain_callback(chain_get_devices_type))
        self.osc_server.add_handler("/live/rack/get/chain/devices/class_name",
                                    create_chain_callback(chain_get_devices_class_name))
        self.osc_server.add_handler("/live/rack/get/chain/devices/can_have_chains",
                                    create_chain_callback(chain_get_devices_can_have_chains))

        # ----------------------------------------------------------------
        # Chain-device handlers (nested device inside a chain)
        # ----------------------------------------------------------------

        def chain_device_get_name(device, params=()):
            return device.name,

        def chain_device_get_class_name(device, params=()):
            return device.class_name,

        def chain_device_get_type(device, params=()):
            return device.type,

        def chain_device_get_can_have_chains(device, params=()):
            return int(device.can_have_chains),

        def chain_device_get_num_parameters(device, params=()):
            return len(device.parameters),

        def chain_device_get_parameters_name(device, params=()):
            return tuple(p.name for p in device.parameters)

        def chain_device_get_parameters_value(device, params=()):
            return tuple(p.value for p in device.parameters)

        def chain_device_get_parameters_min(device, params=()):
            return tuple(p.min for p in device.parameters)

        def chain_device_get_parameters_max(device, params=()):
            return tuple(p.max for p in device.parameters)

        def chain_device_get_parameters_is_quantized(device, params=()):
            return tuple(p.is_quantized for p in device.parameters)

        def chain_device_get_parameter_value(device, params=()):
            param_index = int(params[0])
            return param_index, device.parameters[param_index].value

        def chain_device_get_parameter_value_string(device, params=()):
            param_index = int(params[0])
            return param_index, device.parameters[param_index].str_for_value(
                device.parameters[param_index].value
            )

        def chain_device_set_parameter_value(device, params=()):
            param_index = int(params[0])
            param_value = params[1]
            device.parameters[param_index].value = param_value

        self.osc_server.add_handler("/live/rack/get/chain/device/name",
                                    create_chain_device_callback(chain_device_get_name))
        self.osc_server.add_handler("/live/rack/get/chain/device/class_name",
                                    create_chain_device_callback(chain_device_get_class_name))
        self.osc_server.add_handler("/live/rack/get/chain/device/type",
                                    create_chain_device_callback(chain_device_get_type))
        self.osc_server.add_handler("/live/rack/get/chain/device/can_have_chains",
                                    create_chain_device_callback(chain_device_get_can_have_chains))
        self.osc_server.add_handler("/live/rack/get/chain/device/num_parameters",
                                    create_chain_device_callback(chain_device_get_num_parameters))
        self.osc_server.add_handler("/live/rack/get/chain/device/parameters/name",
                                    create_chain_device_callback(chain_device_get_parameters_name))
        self.osc_server.add_handler("/live/rack/get/chain/device/parameters/value",
                                    create_chain_device_callback(chain_device_get_parameters_value))
        self.osc_server.add_handler("/live/rack/get/chain/device/parameters/min",
                                    create_chain_device_callback(chain_device_get_parameters_min))
        self.osc_server.add_handler("/live/rack/get/chain/device/parameters/max",
                                    create_chain_device_callback(chain_device_get_parameters_max))
        self.osc_server.add_handler("/live/rack/get/chain/device/parameters/is_quantized",
                                    create_chain_device_callback(chain_device_get_parameters_is_quantized))
        self.osc_server.add_handler("/live/rack/get/chain/device/parameter/value",
                                    create_chain_device_callback(chain_device_get_parameter_value))
        self.osc_server.add_handler("/live/rack/get/chain/device/parameter/value_string",
                                    create_chain_device_callback(chain_device_get_parameter_value_string))
        self.osc_server.add_handler("/live/rack/set/chain/device/parameter/value",
                                    create_chain_device_callback(chain_device_set_parameter_value))
