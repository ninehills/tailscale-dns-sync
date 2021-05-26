#!/usr/bin/env python3
#coding=utf8

import sys
from typing import List, Tuple, Dict
from collections import defaultdict

import requests

from config import *

class Device(object):
    def __init__(self, name: str, ip: str):
        self.name = name
        self.ip = ip
    
    def __str__(self):
        return f"{self.name}[{self.ip}]"


def get_tailscale_devices(tailnet: str, api_key: str) -> Tuple[str, List[Device]]:
    """ Get tailscale devices 
    API docs: https://github.com/tailscale/tailscale/blob/main/api.md

    Args:
        tailnet: A tailnet is the name of your Tailscale network. 
            You can find it in the top left corner of the Admin 
            Panel beside the Tailscale logo.
        api_key:  Visit the admin panel and navigate to the Keys page,
            then generate an API Key. That keys expire after 90 days and
            need to be regenerated.
    Returns:
        err, devices:
            err: Error message if not None.
            devices: List of Device.  
    """
    r = requests.get(
        f'https://api.tailscale.com/api/v2/tailnet/{tailnet}/devices',
        auth=(api_key, ''),
        timeout=30,
    )
    try:
        r.raise_for_status()
        ret = r.json()   
    except requests.RequestException as e:
        return f'Call Tailscale API failed: {e}', None
    except ValueError:
        return f'Tailscale API response json decode failed.', None
    
    devices: List[Device] = []
    # remove `.swulling.gmail.com` in yangtaodeimac.swulling.gmail.com
    domain = tailnet.replace('@', '.')
    for d in ret.get('devices', []):
        name = d['name'].replace(f'.{domain}', '')
        ip = d['addresses'][0]
        devices.append(Device(name, ip))

    return None, devices


class Dnspod(object):

    def __init__(self, api_id: str, api_token: str):
        self.login_token = f'{api_id},{api_token}'

    
    def _request(self, path: str, params: Dict) -> Tuple[str, Dict]:
        """See: https://docs.dnspod.cn/api/5f561f9ee75cf42d25bf6720/
        """
        data = dict(
            login_token=self.login_token,
            format='json',
            lang='en',
            error_on_empty='yes'
        )
        data.update(params)
        r = requests.post(
            f'https://dnsapi.cn/{path}',
            data=data,
            timeout=30,
        )
        try:
            r.raise_for_status()
            ret = r.json()   
        except requests.RequestException as e:
            return f'Call Dnspod API failed: {e}', None
        except ValueError:
            return f'Dnspod API response json decode failed.', None
        err_code = ret.get('status', {}).get('code')
        if err_code != '1':
            err_msg = ret.get('status', {}).get('message')
            return f'Dnspod API response status != 1: {err_code}/{err_msg}', None
        return None, ret

    def get_domain_records(self, domain: str, sub_domain: str = None) -> Tuple[str, Dict]:
        params = dict(domain=domain)
        if sub_domain:
            params['sub_domain'] = sub_domain
        err, r = self._request('Record.List', params=params)
        if err:
            return err, None
        records = defaultdict(list)
        for r in r.get('records', []):
            records[r['name']].append(r)
        return None, records

    def add_record_a(self, ip:str, domain: str, sub_domain: str) -> str:
        params = dict(
            domain=domain,
            sub_domain=sub_domain,
            record_type='A',
            record_line='默认',
            value=ip,
        )
        err, r = self._request('Record.Create', params=params)
        if err:
            return err

    def modify_record_a(self, ip:str, domain: str, sub_domain: str, record_id: str) -> str:
        params = dict(
            domain=domain,
            sub_domain=sub_domain,
            record_id=record_id,
            record_type='A',
            record_line='默认',
            value=ip,
        )
        err, r = self._request('Record.Modify', params=params)
        if err:
            return err

    def sync_devices_to_domain(self, devices: List[Device], domain: str, sub_domain: str = None) -> str:
        err, records = self.get_domain_records(domain, sub_domain)
        if err:
            return err

        for device in devices:
            # 判断对应的records是否存在
            record_name = f'{device.name}.{sub_domain}' if sub_domain else device.name
            if record_name not in records:
                print(f'Record {record_name}.{domain} not exist, set to {device.ip}')
                err = self.add_record_a(device.ip, domain, record_name)
                if err:
                    return err
                continue
            
            # 如果存在且默认线路的解析相等，跳过
            default_record = [r for r in records[record_name] if r['line'] == '默认']
            if not default_record:
                print(f'Record {record_name}.{domain} default line not exist, set to {device.ip}')
                err = self.add_record_a(ip, domain, record_name)
                if err:
                    return err
                continue

            modify_record = default_record[0]
            if modify_record['type'] == 'A' and modify_record['value'] == device.ip:
                print(f'Record {record_name}.{domain} is already point to {device.ip}, do nothing')
            else:
                old_value = modify_record['value']
                print(f'Record {record_name}.{domain} from {old_value} change to {device.ip}')
                err = self.modify_record_a(device.ip, domain, record_name, modify_record['id'])
                if err:
                    return err


def main():
    err, devices = get_tailscale_devices(TAILSCALE_TAILNET, TAILSCALE_API_KEY)
    if err:
        print(f'Get tailscale devices failed: {err}', file=sys.stderr)
        sys.exit(1)
    
    dnspod = Dnspod(DNSPOD_API_ID, DNSPOD_API_TOKEN)
    err = dnspod.sync_devices_to_domain(devices, DNSPOD_DOMAIN, DNSPOD_SUB_DOMAIN)
    if err:
        print(f'Dnspod sync records failed: {err}', file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
