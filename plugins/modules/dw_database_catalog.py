#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2021 Cloudera, Inc. All Rights Reserved.
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

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cloudera.cloud.plugins.module_utils.cdp_common import CdpModule

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: dw_database_catalog
short_description: Create CDP Data Warehouse Database Catalog
description:
    - Create CDP Database Catalog
author:
  - "Webster Mudge (@wmudge)"
  - "Dan Chaffelson (@chaffelson)"
  - "Saravanan Raju (@raju-saravanan)"
requirements:
  - cdpy
options:
  id:
    description:
      - If an ID is provided, that Database Catalog will be deleted if C(state=absent)
    type: str
    required: When state is absent
  cluster_id:
    description: ID of cluster where Database Catalog should be created.
    type: str
    required: True
  name:
    description: Name of the Database Catalog.
    type: str
    required: True
  load_demo_data:
    description: Set this to true if you demo data should be loaded into the Database Catalog.
    type: str
    required: False
  wait:
    description:
      - Flag to enable internal polling to wait for the Data Catalog to achieve the declared state.
      - If set to FALSE, the module will return immediately.
    type: bool
    required: False
    default: True
  delay:
    description:
      - The internal polling interval (in seconds) while the module waits for the Data Catalog to achieve the declared
        state.
    type: int
    required: False
    default: 15
    aliases:
      - polling_delay
  timeout:
    description:
      - The internal polling timeout (in seconds) while the module waits for the Data Catalog to achieve the declared
        state.
    type: int
    required: False
    default: 3600
    aliases:
      - polling_timeout  
extends_documentation_fragment:
  - cloudera.cloud.cdp_sdk_options
  - cloudera.cloud.cdp_auth_options
'''

EXAMPLES = r'''
# Note: These examples do not set authentication details.

# Create Database Catalog
- cloudera.cloud.dw_database_catalog:
    name: "example-database-catalog-name"
    cluster_id: "example-cluster-id"
    
# Delete Database Catalog
- cloudera.cloud.dw_database_catalog:
    id: "example-database-id"
    cluster_id: "example-cluster-id"  
    state: "absent"   
'''

RETURN = r'''
---
database_catalogs:
  description: The information about the named Database Catalog.
  type: list
  returned: always
  elements: complex
  suboptions:
    id:
      description: The id of the Database Catalog.
      returned: always
      type: str
    name:
      description: The name of the Database Catalog.
      returned: always
      type: str
    status:
      description: The status of the Database Catalog.
      returned: always
      type: str
sdk_out:
  description: Returns the captured CDP SDK log.
  returned: when supported
  type: str
sdk_out_lines:
  description: Returns a list of each line of the captured CDP SDK log.
  returned: when supported
  type: list
  elements: str
'''


class DwDbc(CdpModule):
    def __init__(self, module):
        super(DwDbc, self).__init__(module)

        # Set variables
        self.id = self._get_param('id')
        self.cluster_id = self._get_param('cluster_id')
        self.name = self._get_param('name')
        self.load_demo_data = self._get_param('load_demo_data')
        self.state = self._get_param('state')
        self.wait = self._get_param('wait')
        self.delay = self._get_param('delay')
        self.timeout = self._get_param('timeout')

        # Initialize return values
        self.database_catalogs = []

        # Initialize internal values
        self.target = None
        self.changed = False

        # Execute logic process
        self.process()

    @CdpModule._Decorators.process_debug
    def process(self):
        if self.id is None:
            dbcs = self.cdpy.dw.list_dbcs(cluster_id=self.cluster_id)
            for dbc in dbcs:
                if self.name is not None and dbc['name'] == self.name:
                    self.target = self.cdpy.dw.describe_dbc(cluster_id=self.cluster_id, dbc_id=dbc['id'])
                elif self.id is not None and dbc['id'] == self.id:
                    self.target = self.cdpy.dw.describe_dbc(cluster_id=self.cluster_id, dbc_id=self.id)
        # If Database Catalog exists
        if self.target is not None:
            if self.state == 'absent':
                if self.module.check_mode:
                    self.database_catalogs.append(self.target)
                else:
                    if self.target['status'] not in self.cdpy.sdk.REMOVABLE_STATES:
                        self.module.warn(
                            "DW Database Catalog not in valid state for Delete operation: %s" % self.target['status'])
                    else:
                        _ = self.cdpy.dw.delete_dbc(cluster_id=self.cluster_id, dbc_id=self.target['id'])
                        self.changed = True
                    if self.wait:
                        self.cdpy.sdk.wait_for_state(
                            describe_func=self.cdpy.dw.describe_dbc,
                            params=dict(cluster_id=self.cluster_id, dbc_id=self.target['id']),
                            field=None, delay=self.delay, timeout=self.timeout
                        )
                    else:
                        self.cdpy.sdk.sleep(self.delay)  # Wait for consistency sync
                        self.target = self.cdpy.dw.describe_dbc(cluster_id=self.cluster_id, dbc_id=self.target['id'])
                        self.database_catalogs.append(self.target)
                    # Drop Done
            elif self.state == 'present':
                # Begin Config check
                self.module.warn("DW Database Catalog already present and config validation is not implemented")
                if self.wait:
                    self.target = self.cdpy.sdk.wait_for_state(
                        describe_func=self.cdpy.dw.describe_dbc,
                        params=dict(cluster_id=self.cluster_id, dbc_id=self.target['id']),
                        state=self.cdpy.sdk.STARTED_STATES, delay=self.delay, timeout=self.timeout
                    )
                    self.database_catalogs.append(self.target)
                    # End Config check
            else:
                self.module.fail_json(msg="State %s is not valid for this module" % self.state)
            # End handling Database Catalog exists
        else:
            # Begin handling Database Catalog not found
            if self.state == 'absent':
                self.module.warn("DW Database Catalog %s already absent in Cluster %s" % (self.name, self.cluster_id))
            elif self.state == 'present':
                if self.module.check_mode:
                    pass
                else:
                    dbc_id = self.cdpy.dw.create_dbc(cluster_id=self.cluster_id, name=self.name,
                                                     load_demo_data=self.load_demo_data)
                    self.changed = True
                    if self.wait:
                        self.target = self.cdpy.sdk.wait_for_state(
                            describe_func=self.cdpy.dw.describe_dbc,
                            params=dict(cluster_id=self.cluster_id, dbc_id=dbc_id),
                            state=self.cdpy.sdk.STARTED_STATES, delay=self.delay, timeout=self.timeout
                        )
                    else:
                        self.target = self.cdpy.dw.describe_dbc(cluster_id=self.cluster_id, dbc_id=dbc_id)
                    self.database_catalogs.append(self.target)
            else:
                self.module.fail_json(msg="State %s is not valid for this module" % self.state)


def main():
    module = AnsibleModule(
        argument_spec=CdpModule.argument_spec(
            id=dict(type='str'),
            cluster_id=dict(required=True, type='str'),
            name = dict(type='str'),
            load_demo_data=dict(type='bool'),
            state=dict(type='str', choices=['present', 'absent'], default='present'),
            wait = dict(type='bool', default=True),
            delay = dict(type='int', aliases=['polling_delay'], default=15),
            timeout = dict(type='int', aliases=['polling_timeout'], default=3600)
        ),
        supports_check_mode=True
    )

    result = DwDbc(module)
    output = dict(changed=result.changed, database_catalogs=result.database_catalogs)

    if result.debug:
        output.update(sdk_out=result.log_out, sdk_out_lines=result.log_lines)

    module.exit_json(**output)


if __name__ == '__main__':
    main()