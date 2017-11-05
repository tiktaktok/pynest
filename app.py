#!/usr/bin/env python3

import json
import logging
import os.path
import requests
import sys

CLIENT_ID = '797003a0-272b-462d-a739-ee365674be34'
CLIENT_SECRET = '03Cwjo7Tiy7hieo0AWbAvxnTb'

class Nest:
    def __init__(self, code=None, access_token=None):
        if code:
            logging.debug('Init using code ' + code)
            self.access_token = self.get_access_token(code)
            logging.info('Access token: ' + self.access_token)
        elif access_token:
            logging.debug('Init using access_token ' + access_token)
            self.access_token = access_token
        else:
            raise Exception('Must provide either code or access token')


    def get_access_token(self, code):
        url = "https://api.home.nest.com/oauth2/access_token"
        payload = (("client_id", CLIENT_ID),
                   ('client_secret', CLIENT_SECRET),
                   ('grant_type', 'authorization_code'),
                   ('code', code))
        #headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        headers = {}
        
        r = requests.post(url, data=payload, headers=headers)
        json = r.json()
        if 'error' in json:
            raise Exception('Could not authenticate')
        return json['access_token']


    def get_thermostat_ids(self):
        r = self.request('GET', 'https://developer-api.nest.com/devices/thermostats/')
        return list(r.json().keys())


    def get_thermostat(self):
        thermostat_ids = nest.get_thermostat_ids()
        if len(thermostat_ids) > 1:
            raise Exception("More than one thermostat on this account.")
        thermostat_id = thermostat_ids[0]

        return Thermostat(self, thermostat_id)


    def request(self, verb, url, data=None, json=None):
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + self.access_token}
        r = requests.request(verb, url, data=data, json=json, headers=headers, allow_redirects=False)
        logging.debug('status code: ' + str(r.status_code))
        while r.status_code == 307: # redirect
            logging.debug('redirected, trying again')
            r = requests.request(verb, r.headers['Location'], data=data, json=json, headers=headers, allow_redirects=False)
            logging.debug('status code: ' + str(r.status_code))
        return r


class Thermostat:
    def __init__(self, nest, device_id):
        self.nest = nest
        self.device_id = device_id
        self.url = 'https://developer-api.nest.com/devices/thermostats/' + device_id


    @property
    def ambient_temperature(self):
        return float(self.nest.request('GET', self.url + '/ambient_temperature_c').text)


    @property
    def target_temperature(self):
        return float(self.nest.request('GET', self.url + '/target_temperature_c').text)


    @target_temperature.setter
    def target_temperature(self, value):
        r = self.nest.request('PUT', self.url, json={'target_temperature_c': value})
        if r.status_code != 200:
            raise Exception(r.text)


class ConfigFile:
    filename = None

    def __init__(self, filename='config.json'):
        self.filename = filename


    def read(self):
        with open(self.filename) as data_file:
            return json.load(data_file)


    def write(self, data):
        with open(self.filename, 'w') as data_file:
            json.dump(data, data_file)


    def exists(self):
        return os.path.exists(self.filename)


if __name__ == '__main__':
    cfg_file = ConfigFile()
    config = None
    if cfg_file.exists():
        config = cfg_file.read()


    nest = None
    if len(sys.argv) > 1:
        nest = Nest(access_token=sys.argv[1])
    elif config and 'access_token' in config:
        nest = Nest(access_token=config['access_token'])
    else:
        import webbrowser; webbrowser.open('https://home.nest.com/login/oauth2?client_id=' + CLIENT_ID + '&state=STATE', new=2)
        code = input("Enter code: ")
        nest = Nest(code=code)
        config = {'access_token': nest.access_token}
        cfg_file.write(config)

    thermostat = nest.get_thermostat()
    print('Ambient temperature:', thermostat.ambient_temperature)

    t = thermostat.target_temperature
    print('Target temperature:', t)
    if t < 25:
        thermostat.target_temperature = t + 10
    else:
        thermostat.target_temperature = t - 10

    print('Target temperature:', thermostat.target_temperature)
