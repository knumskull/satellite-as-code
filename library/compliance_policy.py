#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) 2026 satellite.crazy.lab contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
---
module: compliance_policy
version_added: 5.8.0
short_description: Manage OpenSCAP Compliance Policies
description:
  - Create, update, and delete OpenSCAP Compliance Policies on a Red Hat Satellite.
  - Resolves SCAP content, profiles, organizations, locations, and hostgroups by name.
author:
  - "satellite.crazy.lab contributors"
options:
  name:
    description:
      - Name of the compliance policy.
    required: true
    type: str
  description:
    description:
      - Description of the compliance policy.
    type: str
  scap_content:
    description:
      - Title of the SCAP content to use.
    required: true
    type: str
  scap_content_profile:
    description:
      - The profile ID within the SCAP content (e.g. C(xccdf_org.ssgproject.content_profile_cis)).
    required: true
    type: str
  deploy_by:
    description:
      - Method used to deploy the policy to hosts.
    required: true
    type: str
    choices:
      - ansible
      - puppet
      - manual
  period:
    description:
      - How often the scan should run.
    required: true
    type: str
    choices:
      - weekly
      - monthly
      - custom
  weekday:
    description:
      - Day of the week for weekly scans.
      - Required when I(period=weekly).
    type: str
    choices:
      - monday
      - tuesday
      - wednesday
      - thursday
      - friday
      - saturday
      - sunday
  day_of_month:
    description:
      - Day of the month for monthly scans (1-31).
      - Required when I(period=monthly).
    type: int
  cron_line:
    description:
      - Cron expression for custom scan schedules.
      - Required when I(period=custom).
    type: str
  organizations:
    description:
      - List of organization names to assign to the policy.
    required: true
    type: list
    elements: str
  locations:
    description:
      - List of location names to assign to the policy.
    required: true
    type: list
    elements: str
  hostgroups:
    description:
      - List of hostgroup titles to assign to the policy.
      - Use the full hierarchical title (e.g. C(hg-base/hg-rhel-9)).
    type: list
    elements: str
    default: []
  state:
    description:
      - Whether the policy should exist or not.
    type: str
    choices:
      - present
      - absent
    default: present
extends_documentation_fragment:
  - redhat.satellite.foreman
notes:
  - Requires the OpenSCAP plugin to be installed on the Satellite server.
'''

EXAMPLES = '''
- name: "Create a CIS compliance policy"
  redhat.satellite.compliance_policy:
    username: "admin"
    password: "changeme"
    server_url: "https://satellite.example.com"
    name: "CIS-Server-L1-RHEL9-Policy"
    description: "CIS Server Level 1 for RHEL 9"
    scap_content: "Red Hat rhel9 default content"
    scap_content_profile: "xccdf_org.ssgproject.content_profile_cis_server_l1"
    deploy_by: "ansible"
    period: "custom"
    cron_line: "0 9 * * *"
    organizations:
      - "ACME"
    locations:
      - "Default Location"
    hostgroups:
      - "hg-base/hg-rhel-9"
    state: present

- name: "Remove a compliance policy"
  redhat.satellite.compliance_policy:
    username: "admin"
    password: "changeme"
    server_url: "https://satellite.example.com"
    name: "CIS-Server-L1-RHEL9-Policy"
    state: absent
'''

RETURN = '''
entity:
  description: Final state of the affected entities grouped by their type.
  returned: success
  type: dict
  contains:
    compliance_policies:
      description: List of compliance policies.
      type: list
      elements: dict
'''

import json

from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible.module_utils.urls import fetch_url


class SatelliteCompliancePolicyModule(object):
    """Manage OpenSCAP compliance policies via the Satellite API."""

    def __init__(self):
        self.module = AnsibleModule(
            argument_spec=dict(
                server_url=dict(required=True, fallback=(env_fallback, ['SATELLITE_SERVER_URL', 'SATELLITE_SERVER', 'FOREMAN_SERVER_URL', 'FOREMAN_SERVER'])),
                username=dict(required=True, fallback=(env_fallback, ['SATELLITE_USERNAME', 'SATELLITE_USER', 'FOREMAN_USERNAME', 'FOREMAN_USER'])),
                password=dict(required=True, no_log=True, fallback=(env_fallback, ['SATELLITE_PASSWORD', 'FOREMAN_PASSWORD'])),
                validate_certs=dict(type='bool', default=True, fallback=(env_fallback, ['SATELLITE_VALIDATE_CERTS', 'FOREMAN_VALIDATE_CERTS'])),
                name=dict(required=True),
                description=dict(default=''),
                scap_content=dict(),
                scap_content_profile=dict(),
                deploy_by=dict(choices=['ansible', 'puppet', 'manual']),
                period=dict(choices=['weekly', 'monthly', 'custom']),
                weekday=dict(choices=['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']),
                day_of_month=dict(type='int'),
                cron_line=dict(),
                organizations=dict(type='list', elements='str'),
                locations=dict(type='list', elements='str'),
                hostgroups=dict(type='list', elements='str', default=[]),
                state=dict(choices=['present', 'absent'], default='present'),
            ),
            required_if=[
                ('state', 'present', ['scap_content', 'scap_content_profile', 'deploy_by', 'period', 'organizations', 'locations']),
                ('period', 'weekly', ['weekday']),
                ('period', 'monthly', ['day_of_month']),
                ('period', 'custom', ['cron_line']),
            ],
            supports_check_mode=True,
        )

        self.server_url = self.module.params['server_url'].rstrip('/')
        self.username = self.module.params['username']
        self.password = self.module.params['password']
        self.validate_certs = self.module.params['validate_certs']

    def _api_request(self, method, endpoint, data=None):
        """Make an authenticated API request to Satellite."""
        url = '{0}{1}'.format(self.server_url, endpoint)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

        body = None
        if data is not None:
            body = json.dumps(data)

        resp, info = fetch_url(
            self.module, url, method=method, data=body, headers=headers,
            url_username=self.username, url_password=self.password,
            validate_certs=self.validate_certs, force_basic_auth=True,
        )

        status = info['status']
        if status == -1:
            self.module.fail_json(msg="Connection to {0} failed: {1}".format(url, info.get('msg', 'unknown error')))

        response_body = resp.read() if resp else info.get('body', '')
        try:
            result = json.loads(response_body) if response_body else {}
        except (ValueError, TypeError):
            result = {}

        return status, result

    def _get_all(self, endpoint):
        """Retrieve all results from a paginated API endpoint."""
        status, result = self._api_request('GET', '{0}?per_page=1000'.format(endpoint))
        if status != 200:
            self.module.fail_json(msg="Failed to query {0}: HTTP {1}".format(endpoint, status))
        return result.get('results', [])

    def _resolve_ids(self, resource_endpoint, names, key='name'):
        """Resolve a list of names/titles to IDs."""
        results = self._get_all(resource_endpoint)
        lookup = {item[key]: item['id'] for item in results}
        ids = []
        for name in names:
            if name not in lookup:
                self.module.fail_json(msg="Could not find {0} '{1}' at {2}".format(key, name, resource_endpoint))
            ids.append(lookup[name])
        return ids

    def _find_policy(self, name):
        """Find an existing policy by name."""
        policies = self._get_all('/api/v2/compliance/policies')
        for policy in policies:
            if policy['name'] == name:
                return policy
        return None

    def _resolve_scap_content(self, title):
        """Resolve SCAP content title to ID."""
        contents = self._get_all('/api/v2/compliance/scap_contents')
        for content in contents:
            if content['title'] == title:
                return content['id']
        self.module.fail_json(msg="SCAP content '{0}' not found".format(title))

    def _resolve_scap_profile(self, scap_content_title, profile_id):
        """Resolve a SCAP content profile by content title and profile_id string."""
        profiles = self._get_all('/api/v2/compliance/scap_content_profiles')
        for profile in profiles:
            if (profile.get('scap_content', {}).get('title') == scap_content_title
                    and profile.get('profile_id') == profile_id):
                return profile['id']
        self.module.fail_json(
            msg="SCAP profile '{0}' not found in content '{1}'".format(profile_id, scap_content_title)
        )

    def _build_policy_payload(self):
        """Build the API request body for create/update."""
        p = self.module.params

        scap_content_id = self._resolve_scap_content(p['scap_content'])
        scap_content_profile_id = self._resolve_scap_profile(p['scap_content'], p['scap_content_profile'])
        organization_ids = self._resolve_ids('/api/v2/organizations', p['organizations'])
        location_ids = self._resolve_ids('/api/v2/locations', p['locations'])
        hostgroup_ids = self._resolve_ids('/api/v2/hostgroups', p['hostgroups'], key='title') if p['hostgroups'] else []

        policy = {
            'name': p['name'],
            'description': p.get('description') or '',
            'scap_content_id': scap_content_id,
            'scap_content_profile_id': scap_content_profile_id,
            'period': p['period'],
            'deploy_by': p['deploy_by'],
            'organization_ids': organization_ids,
            'location_ids': location_ids,
            'hostgroup_ids': hostgroup_ids,
        }

        if p['period'] == 'weekly' and p.get('weekday'):
            policy['weekday'] = p['weekday']
        elif p['period'] == 'monthly' and p.get('day_of_month'):
            policy['day_of_month'] = p['day_of_month']
        elif p['period'] == 'custom' and p.get('cron_line'):
            policy['cron_line'] = p['cron_line']

        return {'policy': policy}

    def _needs_update(self, existing, desired_policy):
        """Check if the existing policy differs from the desired state."""
        desired = desired_policy['policy']
        checks = [
            existing.get('description', '') != desired.get('description', ''),
            existing.get('scap_content_id') != desired.get('scap_content_id'),
            existing.get('scap_content_profile_id') != desired.get('scap_content_profile_id'),
            existing.get('period') != desired.get('period'),
            existing.get('deploy_by') != desired.get('deploy_by'),
        ]

        if desired.get('period') == 'weekly':
            checks.append(existing.get('weekday') != desired.get('weekday'))
        elif desired.get('period') == 'monthly':
            checks.append(existing.get('day_of_month') != desired.get('day_of_month'))
        elif desired.get('period') == 'custom':
            checks.append(existing.get('cron_line') != desired.get('cron_line'))

        existing_org_ids = sorted([o['id'] for o in existing.get('organizations', [])])
        existing_loc_ids = sorted([l['id'] for l in existing.get('locations', [])])
        existing_hg_ids = sorted([h['id'] for h in existing.get('hostgroups', [])])

        checks.append(existing_org_ids != sorted(desired.get('organization_ids', [])))
        checks.append(existing_loc_ids != sorted(desired.get('location_ids', [])))
        checks.append(existing_hg_ids != sorted(desired.get('hostgroup_ids', [])))

        return any(checks)

    def run(self):
        p = self.module.params
        name = p['name']
        state = p['state']

        existing = self._find_policy(name)

        if state == 'absent':
            if existing is None:
                self.module.exit_json(changed=False, entity={'compliance_policies': []})
            if self.module.check_mode:
                self.module.exit_json(changed=True, entity={'compliance_policies': []})
            status, result = self._api_request('DELETE', '/api/v2/compliance/policies/{0}'.format(existing['id']))
            if status not in (200, 204):
                self.module.fail_json(msg="Failed to delete policy '{0}': HTTP {1}".format(name, status))
            self.module.exit_json(changed=True, entity={'compliance_policies': []})

        payload = self._build_policy_payload()

        if existing is None:
            if self.module.check_mode:
                self.module.exit_json(changed=True, entity={'compliance_policies': [payload['policy']]})
            status, result = self._api_request('POST', '/api/v2/compliance/policies', payload)
            if status != 201:
                self.module.fail_json(msg="Failed to create policy '{0}': HTTP {1} - {2}".format(
                    name, status, result.get('error', {}).get('message', result)))
            self.module.exit_json(changed=True, entity={'compliance_policies': [result]})

        if not self._needs_update(existing, payload):
            self.module.exit_json(changed=False, entity={'compliance_policies': [existing]})

        if self.module.check_mode:
            self.module.exit_json(changed=True, entity={'compliance_policies': [payload['policy']]})

        status, result = self._api_request('PUT', '/api/v2/compliance/policies/{0}'.format(existing['id']), payload)
        if status != 200:
            self.module.fail_json(msg="Failed to update policy '{0}': HTTP {1} - {2}".format(
                name, status, result.get('error', {}).get('message', result)))
        self.module.exit_json(changed=True, entity={'compliance_policies': [result]})


def main():
    SatelliteCompliancePolicyModule().run()


if __name__ == '__main__':
    main()
