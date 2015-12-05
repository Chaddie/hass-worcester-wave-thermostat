import sys
from pprint import pprint
import json

import sleekxmpp

from utils import decode, parse_on_off

# Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input


class WaveMessageBot(sleekxmpp.ClientXMPP):
    """
    A basic SleekXMPP bot that will log in, send a message,
    and then log out.
    """
    current_temp = None
    set_point = None
    boiler_on = None

    def __init__(self):
        jid = "rrccontact_458921440@wa2-mz36-qrmzh6.bosch.de"
        password = "Ct7ZR03b_E6z5sHWaxiQYCwfU"
        recipient = "rrcgateway_458921440@wa2-mz36-qrmzh6.bosch.de"
        message = "GET /ecus/rrc/uiStatus HTTP /1.0\nUser-Agent: NefitEasy"

        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        # The message we wish to send, and the JID that
        # will receive it.
        self.recipient = recipient
        self.msg = message

        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)

    def connect(self):
        return sleekxmpp.ClientXMPP.connect(self, ('wa2-mz36-qrmzh6.bosch.de', 5222))

    def start(self, event):
        """
        Process the session_start event.

        Send a message to request the status
        """
        self.send_presence()
        self.get_roster()

        self.send_message(mto=self.recipient,
                          mbody=self.msg,
                          mtype='chat')

    def message(self, msg):
        """
        Process a message once it has been received
        """
        spl = str(msg['body']).split("\n\n")

        if len(spl) < 2:
            # Invalid message
            return
        else:
            to_decode = spl[1].strip()

            # Decode the encrypted message
            data = decode(to_decode)

            # For some reason we have a load of null characters at the end
            # of the message, so strip these out
            data = data.replace(b'\x00', b'')

            # 'decode' from bytes to str, with UTF-8 encoding
            # (a different sort of 'decode' to above!)
            data = data.decode('utf-8')
            if len(data) > 0:
                data = json.loads(data)['value']
                pprint(data)

                # Temperature set point (ie. temperature it is aiming for)
                self.set_point = float(data['TSP'])

                # Current measured temperature at thermostat
                self.current_temp = float(data['IHT'])

                # Is hot water on or off
                self.hot_water = parse_on_off(data['DHW'])

                # Program mode: 'manual' or 'clock'
                self.program_mode = data['UMD']

                # Temperature Override Duration
                self.temp_override_duration = float(data['TOD'])

                # Current Switch Point
                # TODO: No idea what this is...it was coming up as 39
                # for me...and I'm pretty sure it's not 39 degrees C!
                self.current_switch_point = float(data['CSP'])

                self.temp_override_on = parse_on_off(data['TOR'])

                self.holiday_mode = parse_on_off(data['HMD'])

                self.day_as_sunday = parse_on_off(data['DAS'])

                self.tomorrow_as_sunday = parse_on_off(data['TAS'])

                # Is the boiler on or off (ie. flame on or off)
                if data['BAI'] == 'No':
                    self.boiler_on = 0
                elif data['BAI'] == 'CH' or data['BAI'] == 'HW':
                    self.boiler_on = 1

                self.disconnect()

if __name__ == '__main__':
    wave = WaveMessageBot()

    # Connect to the Bosch XMPP server and start processing messages
    if wave.connect():
        wave.process(block=True)
        print(wave.set_point, wave.current_temp, wave.boiler_on)
    else:
        print("Unable to connect.")
