# -*- coding: utf-8 -*-
import logging
import commands
import simplejson
import os
import os.path
import openerp
import time
import random
import subprocess
import simplejson
import werkzeug
import werkzeug.wrappers
_logger = logging.getLogger(__name__)


from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import manifest_list, module_boot, html_template


# drivers modules must add to drivers an object with a get_status() method 
# so that 'status' can return the status of all active drivers
drivers = {}

class Proxy(http.Controller):
    def __init__(self):
        self.scale = 'closed'
        self.scale_weight = 0.0

    def get_status(self):
        statuses = {}
        for driver in drivers:
            statuses[driver] = drivers[driver].get_status()
        return statuses

    @http.route('/hw_proxy/hello', type='http', auth='none', cors='*')
    def hello(self):
        return "ping"

    @http.route('/hw_proxy/handshake', type='json', auth='none', cors='*')
    def handshake(self):
        return True

    @http.route('/hw_proxy/status', type='http', auth='none', cors='*')
    def status_http(self):
        resp = """
<!DOCTYPE HTML>
<html>
    <head>
        <title>OpenERP's PosBox</title>
        <style>
        body {
            width: 480px;
            margin: 60px auto;
            font-family: sans-serif;
            text-align: justify;
            color: #6B6B6B;
        }
        .device {
            border-bottom: solid 1px rgb(216,216,216);
            padding: 9px;
        }
        .device:nth-child(2n) {
            background:rgb(240,240,240);
        }
        </style>
    </head>
    <body>
        <h1>Hardware Status</h1>
        <p>The list of enabled drivers and their status</p>
"""
        statuses = self.get_status()
        for driver in statuses:

            status = statuses[driver]

            if status['status'] == 'connecting':
                color = 'black'
            elif status['status'] == 'connected':
                color = 'green'
            else:
                color = 'red'

            resp += "<h3 style='color:"+color+";'>"+driver+' : '+status['status']+"</h3>\n"
            resp += "<ul>\n"
            for msg in status['messages']:
                resp += '<li>'+msg+'</li>\n'
            resp += "</ul>\n"
        resp += """
            <h2>Connected Devices</h2>
            <p>The list of connected USB devices as seen by the posbox</p>
        """
        devices = commands.getoutput("lsusb").split('\n')
        resp += "<div class='devices'>\n"
        for device in devices:
            device_name = device[device.find('ID')+2:]
            resp+= "<div class='device' data-device='"+device+"'>"+device_name+"</div>\n"
        resp += "</div>\n"
        resp += """
            <h2>Add New Printer</h2>
            <p>
            Copy and paste your printer's device description in the form below. You can find
            your printer's description in the device list above. If you find that your printer works
            well, please send your printer's description to <a href='mailto:support@openerp.com'>
            support@openerp.com</a> so that we can add it to the default list of supported devices.
            </p>
            <form action='/hw_proxy/escpos/add_supported_device' method='GET'>
                <input type='text' style='width:400px' name='device_string' placeholder='123a:b456 Sample Device description' />
                <input type='submit' value='submit' />
            </form>
            <h2>Reset To Defaults</h2>
            <p>If the added devices cause problems, you can <a href='/hw_proxy/escpos/reset_supported_devices'>Reset the
            device list to factory default.</a> This operation cannot be undone.</p>
        """
        resp += "</body>\n</html>\n\n"

        return request.make_response(resp,{
            'Cache-Control': 'no-cache', 
            'Content-Type': 'text/html; charset=utf-8',
            'Access-Control-Allow-Origin':  '*',
            'Access-Control-Allow-Methods': 'GET',
            })

    @http.route('/hw_proxy/status_json', type='json', auth='none', cors='*')
    def status_json(self):
        return self.get_status()

    @http.route('/hw_proxy/weighting_start', type='json', auth='none', cors='*')
    def weighting_start(self):
        if self.scale == 'closed':
            print "Opening (Fake) Connection to Scale..."
            self.scale = 'open'
            self.scale_weight = 0.0
            time.sleep(0.1)
            print "... Scale Open."
        else:
            print "WARNING: Scale already Connected !!!"

    @http.route('/hw_proxy/weighting_read_kg', type='json', auth='none', cors='*')
    def weighting_read_kg(self):
        if self.scale == 'open':
            print "Reading Scale..."
            time.sleep(0.025)
            self.scale_weight += 0.01
            print "... Done."
            return self.scale_weight
        else:
            print "WARNING: Reading closed scale !!!"
            return 0.0

    @http.route('/hw_proxy/weighting_end', type='json', auth='none', cors='*')
    def weighting_end(self):
        if self.scale == 'open':
            print "Closing Connection to Scale ..."
            self.scale = 'closed'
            self.scale_weight = 0.0
            time.sleep(0.1)
            print "... Scale Closed."
        else:
            print "WARNING: Scale already Closed !!!"

    @http.route('/hw_proxy/log', type='json', auth='none', cors='*')
    def log(self, arguments):
        _logger.info(' '.join(str(v) for v in arguments))

