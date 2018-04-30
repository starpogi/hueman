import asyncio
import collections
import enum
import os
import sys
import datetime

from ssdp import find_bridge
import requests
import uvloop


async def poll_lights(url, user, lights, lut):
    lut, targets = lut

    while True:
        for light_id, state in fetch_status(url, user, filter=lut).items():
            target = lut.get(light_id)
            # print("[!] %s reachable: %s" % (target.name, state['reachable']))

            if target is not None:
                if state['reachable'] != target.is_reachable:
                    for group in target.groups:
                        set_state_url = "%s/api/%s/groups/%s/action" % (
                            url, user, group
                        )
                        response = requests.put(
                            set_state_url,
                            json={'on': state['reachable']}
                        )
                        print(response.text)

                    target.lights[light_id].state = LightStates.On if state['reachable'] else LightStates.Unreachable
                    # print(target.state)

                # target.lights_state[light_id] = new_state

        await asyncio.sleep(0.5)


def fetch_status(url, user, filter=None):
    filter = filter or set()

    light_request = requests.get("%s/api/%s/lights" % (url, user),
                                 headers={'Cache-Control': 'no-cache'})
    lights_json = {}

    if light_request.status_code == requests.codes.ok:
        lights_json = {
            k: v.get('state') for k, v in light_request.json().items()
            if k in filter
        }

    return lights_json


def build_lut(lights):
    lut = {}
    targets = set()

    for target, meta in lights.items():
        lights = meta.lights or []

        for light in lights:
            lut.update({
                str(light): meta
            })

            targets.add(str(light))

    return lut, targets


class LightStates(enum.Enum):
    Unreachable = 0
    On = 1
    Off = 2

class Light:
    def __init__(self, light_id, last_updated=None):
        self.light_id = light_id
        self._state = LightStates.Unreachable
        self.last_updated = last_updated or datetime.datetime.utcnow()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self.last_updated = datetime.datetime.utcnow()
        self._state = value

class Trigger:
    def __init__(self, name, lights=None, groups=None, current_state=None):
        self.name = name
        self.lights = {
            str(light): Light(str(light)) for light in lights or []
        }
        self.groups = groups or []
        self.current_state = current_state

    def get_current_state(self):
        if self.current_state is not None:
            for light_id, light in self.lights.items():
                current_light_state = current_state.get(light_id)

                if current_light_state is not None:
                    light.state = LightStates.Off

                    if current_light_state['state']['on']:
                        light.state = LightStates.On

                    if not current_light_state['state']['reachable']:
                        light.state = LightStates.Unreachable

    @property
    def state(self):
        assert len(self.lights) > 0
        states = sorted(self.lights.items(), key=lambda x: x[1].last_updated,
                        reverse=True)
        return states[0][1].state

    @property
    def is_reachable(self):
        state = self.state

        if state == LightStates.Unreachable:
            return False

        return True


if __name__ == '__main__':
    user = os.environ.get('HUE_USER', 'newdeveloper')
    host, port = find_bridge()
    url = "http://%s:%s" % (host, port)

    lights_json = fetch_status(url, user)

    # TODO: Build ID list just from specifying name for auto-detect
    lights = {
        # 'master': Trigger('Master', lights=[23, 24], groups=[1, 6, 7], current_state=lights_json)
        'master': Trigger('Master', lights=[23], groups=[1, 6, 7], current_state=lights_json),
        'bedroom': Trigger('Bedroom', lights=[25], groups=[2], current_state=lights_json)
    }

    lut = build_lut(lights)

    if host is None and port is None:
        sys.exit("No Hue Bridge found")

    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(poll_lights(url, user, lights, lut))

    try:
        print("Jarvis Automated Lights Active")
        loop.run_forever()
    finally:
        loop.close()
        print("Stopped")
