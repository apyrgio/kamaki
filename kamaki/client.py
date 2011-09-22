# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import json
import logging

from base64 import b64encode
from httplib import HTTPConnection, HTTPSConnection
from urlparse import urlparse


class ClientError(Exception):
    def __init__(self, message, details=''):
        self.message = message
        self.details = details


class Client(object):
    def __init__(self, url, token=''):
        self.url = url
        self.token = token
    
    def _cmd(self, method, path, body=None, success=200):
        p = urlparse(self.url)
        path = p.path + path
        if p.scheme == 'http':
            conn = HTTPConnection(p.netloc)
        elif p.scheme == 'https':
            conn = HTTPSConnection(p.netloc)
        else:
            raise ClientError("Unknown URL scheme")
        
        headers = {'X-Auth-Token': self.token}
        if body:
            headers['Content-Type'] = 'application/json'
            headers['Content-Length'] = len(body)
        
        logging.debug('%s', '>' * 40)
        logging.debug('%s %s', method, path)

        for key, val in headers.items():
            logging.debug('%s: %s', key, val)
        logging.debug('')
        if body:
            logging.debug(body)
            logging.debug('')
        
        conn.request(method, path, body, headers)

        resp = conn.getresponse()
        logging.debug('%s', '<' * 40)
        logging.info('%d %s', resp.status, resp.reason)
        for key, val in resp.getheaders():
            logging.info('%s: %s', key.capitalize(), val)
        logging.info('')
        
        buf = resp.read()
        try:
            reply = json.loads(buf) if buf else {}
        except ValueError:
            raise ClientError('Invalid response from the server', buf)
        
        if resp.status != success:
            if len(reply) == 1:
                key = reply.keys()[0]
                val = reply[key]
                message = '%s: %s' % (key, val.get('message', ''))
                details = val.get('details', '')
                raise ClientError(message, details)
            else:
                raise ClientError('Invalid response from the server')

        return reply
    
    def _get(self, path, success=200):
        return self._cmd('GET', path, None, success)
    
    def _post(self, path, body, success=202):
        return self._cmd('POST', path, body, success)
    
    def _put(self, path, body, success=204):
        return self._cmd('PUT', path, body, success)
    
    def _delete(self, path, success=204):
        return self._cmd('DELETE', path, None, success)
    
    
    # Servers
    
    def list_servers(self, detail=False):
        path = '/servers/detail' if detail else '/servers'
        reply = self._get(path)
        return reply['servers']['values']
    
    def get_server_details(self, server_id):
        path = '/servers/%d' % server_id
        reply = self._get(path)
        return reply['server']
    
    def create_server(self, name, flavor, image, personality=None):
        """personality is a list of (path, data) tuples"""
        
        req = {'name': name, 'flavorRef': flavor, 'imageRef': image}
        if personality:
            p = []
            for path, data in personality:
                contents = b64encode(data)
                p.append({'path': path, 'contents': contents})
            req['personality'] = p
        
        body = json.dumps({'server': req})
        reply = self._post('/servers', body)
        return reply['server']
    
    def update_server_name(self, server_id, new_name):
        path = '/servers/%d' % server_id
        body = json.dumps({'server': {'name': new_name}})
        self._put(path, body)
    
    def delete_server(self, server_id):
        path = '/servers/%d' % server_id
        self._delete(path)
    
    def reboot_server(self, server_id, hard=False):
        path = '/servers/%d/action' % server_id
        type = 'HARD' if hard else 'SOFT'
        body = json.dumps({'reboot': {'type': type}})
        self._post(path, body)
    
    def start_server(self, server_id):
        path = '/servers/%d/action' % server_id
        body = json.dumps({'start': {}})
        self._post(path, body)
    
    def shutdown_server(self, server_id):
        path = '/servers/%d/action' % server_id
        body = json.dumps({'shutdown': {}})
        self._post(path, body)
    
    def get_server_console(self, server_id):
        path = '/servers/%d/action' % server_id
        body = json.dumps({'console': {'type': 'vnc'}})
        reply = self._cmd('POST', path, body, 200)
        return reply['console']
    
    def set_firewall_profile(self, server_id, profile):
        path = '/servers/%d/action' % server_id
        body = json.dumps({'firewallProfile': {'profile': profile}})
        self._cmd('POST', path, body, 202)
    
    def list_server_addresses(self, server_id, network=None):
        path = '/servers/%d/ips' % server_id
        if network:
            path += '/%s' % network
        reply = self._get(path)
        return [reply['network']] if network else reply['addresses']['values']
    
    def get_server_metadata(self, server_id, key=None):
        path = '/servers/%d/meta' % server_id
        if key:
            path += '/%s' % key
        reply = self._get(path)
        return reply['meta'] if key else reply['metadata']['values']
    
    def create_server_metadata(self, server_id, key, val):
        path = '/servers/%d/meta/%s' % (server_id, key)
        body = json.dumps({'meta': {key: val}})
        reply = self._put(path, body, 201)
        return reply['meta']
    
    def update_server_metadata(self, server_id, key, val):
        path = '/servers/%d/meta' % server_id
        body = json.dumps({'metadata': {key: val}})
        reply = self._post(path, body, 201)
        return reply['metadata']
    
    def delete_server_metadata(self, server_id, key):
        path = '/servers/%d/meta/%s' % (server_id, key)
        reply = self._delete(path)
    
    def get_server_stats(self, server_id):
        path = '/servers/%d/stats' % server_id
        reply = self._get(path)
        return reply['stats']
    
    
    # Flavors
    
    def list_flavors(self, detail=False):
        path = '/flavors/detail' if detail else '/flavors'
        reply = self._get(path)
        return reply['flavors']['values']

    def get_flavor_details(self, flavor_id):
        path = '/flavors/%d' % flavor_id
        reply = self._get(path)
        return reply['flavor']
    
    
    # Images
    
    def list_images(self, detail=False):
        path = '/images/detail' if detail else '/images'
        reply = self._get(path)
        return reply['images']['values']

    def get_image_details(self, image_id):
        path = '/images/%d' % image_id
        reply = self._get(path)
        return reply['image']

    def create_image(self, server_id, name):
        req = {'name': name, 'serverRef': server_id}
        body = json.dumps({'image': req})
        reply = self._post('/images', body)
        return reply['image']

    def delete_image(self, image_id):
        path = '/images/%d' % image_id
        self._delete(path)

    def get_image_metadata(self, image_id, key=None):
        path = '/images/%d/meta' % image_id
        if key:
            path += '/%s' % key
        reply = self._get(path)
        return reply['meta'] if key else reply['metadata']['values']
    
    def create_image_metadata(self, image_id, key, val):
        path = '/images/%d/meta/%s' % (image_id, key)
        body = json.dumps({'meta': {key: val}})
        reply = self._put(path, body, 201)
        reply['meta']

    def update_image_metadata(self, image_id, key, val):
        path = '/images/%d/meta' % image_id
        body = json.dumps({'metadata': {key: val}})
        reply = self._post(path, body, 201)
        return reply['metadata']

    def delete_image_metadata(self, image_id, key):
        path = '/images/%d/meta/%s' % (image_id, key)
        reply = self._delete(path)
    
    
    # Networks
    
    def list_networks(self, detail=False):
        path = '/networks/detail' if detail else '/networks'
        reply = self._get(path)
        return reply['networks']['values']
    
    def create_network(self, name):
        body = json.dumps({'network': {'name': name}})
        reply = self._post('/networks', body)
        return reply['network']
    
    def get_network_details(self, network_id):
        path = '/networks/%s' % network_id
        reply = self._get(path)
        return reply['network']
    
    def update_network_name(self, network_id, new_name):
        path = '/networks/%s' % network_id
        body = json.dumps({'network': {'name': new_name}})
        self._put(path, body)
    
    def delete_network(self, network_id):
        path = '/networks/%s' % network_id
        self._delete(path)

    def connect_server(self, server_id, network_id):
        path = '/networks/%s/action' % network_id
        body = json.dumps({'add': {'serverRef': server_id}})
        self._post(path, body)
    
    def disconnect_server(self, server_id, network_id):
        path = '/networks/%s/action' % network_id
        body = json.dumps({'remove': {'serverRef': server_id}})
        self._post(path, body)
