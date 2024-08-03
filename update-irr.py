#!/usr/bin/env python3

import argparse
import getpass
import os
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path

import requests

REGISTRY = 'https://reg.arin.net/rest/irr'


class BaseResource(ABC):
    type: str

    def __init__(self, name, rpsl):
        self.name = name
        self.rpsl = rpsl

    @abstractmethod
    def validate(self): ...

    @abstractmethod
    def get_create_url(self): ...

    @abstractmethod
    def get_update_url(self): ...


class AsSetResource(BaseResource):
    def __init__(self, name, rpsl):
        self.type = 'as-set'
        super().__init__(name, rpsl)

    def validate(self):
        if not re.match(fr'^as-set:\s+{re.escape(self.name)}$', self.rpsl, re.M):
            raise ValueError(f'Expected aut-num: {self.name} in RPSL')

    def get_create_url(self):
        return f'{REGISTRY}/as-set'

    def get_update_url(self):
        return f'{REGISTRY}/as-set/{self.name}'


class AutNumResource(BaseResource):
    def __init__(self, name, rpsl):
        self.type = 'aut-num'
        super().__init__(name, rpsl)

    def validate(self):
        if not re.match(fr'^aut-num:\s+{re.escape(self.name)}$', self.rpsl, re.M):
            raise ValueError(f'Expected aut-num: {self.name} in RPSL')

    def get_create_url(self):
        return f'{REGISTRY}/aut-num/{self.name}'

    def get_update_url(self):
        return f'{REGISTRY}/aut-num/{self.name}'


def get_resource(path, rpsl):
    if (m := re.match(r'^(AS\d+)\.rpsl$', path)):
        return AutNumResource(m.group(1), rpsl)
    elif (m := re.match(r'^((?:AS\d+@)?(AS-[A-Z0-9-]+@)*AS-[A-Z0-9-]+)\.rpsl$', path)):
        return AsSetResource(m.group(1).replace('@', ':'), rpsl)


def get_api_key():
    key_file = Path(__file__).parent / '.api-key'
    if key_file.exists():
        with open(key_file) as f:
            return f.read().strip()

    return getpass.getpass('ARIN api key: ')


def main():
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='Updates the ARIN IRR database with RPSL files'
    )
    parser.add_argument('filename', type=argparse.FileType('r'))
    parser.add_argument('-c', '--create', action='store_true')
    parser.add_argument(
        '-o', '--org',
        help='Organization handle (e.g. when creating an as-set)'
    )

    args = parser.parse_args()

    with args.filename as f:
        rpsl = f.read()

    resource = get_resource(args.filename.name, rpsl)
    if not resource:
        print(f"Can't identify resource type from {args.filename.name}")
        raise SystemExit(1)

    resource.validate()

    params = {'apikey': get_api_key()}
    if args.org:
        params['orgHandle'] = args.org

    if args.create:
        verb = 'POST'
        url = resource.get_create_url()
    else:
        verb = 'PUT'
        url = resource.get_update_url()

    r = requests.request(verb, url=url, params=params, data=resource.rpsl, headers={
        'Accept': 'application/rpsl',
        'Content-Type': 'application/rpsl',
    })

    print(r.content.decode('utf-8', 'replace'))

if __name__ == '__main__':
    main()
