# Copyright (c) 2013 - 2015 EMC Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import urllib

import six

from cinder import context
from cinder import exception
from cinder.tests.unit.fake_volume import fake_volume_obj
from cinder.tests.unit.volume.drivers.emc import scaleio
from cinder.tests.unit.volume.drivers.emc.scaleio import mocks


class TestExtendVolume(scaleio.TestScaleIODriver):
    """Test cases for ``ScaleIODriver.extend_volume()``"""
    STORAGE_POOL_ID = six.text_type('1')
    STORAGE_POOL_NAME = 'SP1'

    PROT_DOMAIN_ID = six.text_type('1')
    PROT_DOMAIN_NAME = 'PD1'

    """ New sizes for the volume.
    Since ScaleIO has a granularity of 8 GB, multiples of 8 always work.
    The 7 size should be either rounded up to 8 or raise an exception
    based on the round_volume_capacity config setting.
    """
    NEW_SIZE = 8
    BAD_SIZE = 7

    def setUp(self):
        """Setup a test case environment.

        Creates fake volume object and sets up the required API responses.
        """
        super(TestExtendVolume, self).setUp()
        ctx = context.RequestContext('fake', 'fake', auth_token=True)

        self.volume = fake_volume_obj(ctx, **{'id': 'fake_volume'})
        self.volume_name_2x_enc = urllib.quote(
            urllib.quote(self.driver.id_to_base64(self.volume.id))
        )

        self.HTTPS_MOCK_RESPONSES = {
            self.RESPONSE_MODE.Valid: {
                'types/Volume/instances/getByName::' +
                self.volume_name_2x_enc: '"{}"'.format(self.volume.id),
                'instances/Volume::{}/action/setVolumeSize'.format(
                    self.volume.id
                ): 'OK',
            },
            self.RESPONSE_MODE.BadStatus: {
                'types/Volume/instances/getByName::' +
                self.volume_name_2x_enc: self.BAD_STATUS_RESPONSE,
                'types/Volume/instances/getByName::' +
                self.volume_name_2x_enc: mocks.MockHTTPSResponse(
                    {
                        'errorCode': 401,
                        'message': 'BadStatus Extend Volume Test',
                    }, 401
                ),
            },
            self.RESPONSE_MODE.Invalid: {
                'types/Volume/instances/getByName::' +
                self.volume_name_2x_enc: None,
            },
        }

    def test_bad_login(self):
        self.set_https_response_mode(self.RESPONSE_MODE.BadStatus)
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.extend_volume,
                          self.volume,
                          self.NEW_SIZE)

    def test_invalid_volume(self):
        self.set_https_response_mode(self.RESPONSE_MODE.Invalid)
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.extend_volume,
                          self.volume,
                          self.NEW_SIZE)

    def test_extend_volume_bad_size_no_round(self):
        self.driver.configuration.set_override('sio_round_volume_capacity',
                                               override=False)
        self.set_https_response_mode(self.RESPONSE_MODE.Valid)
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.driver.extend_volume,
                          self.volume,
                          self.BAD_SIZE)

    def test_extend_volume_bad_size_round(self):
        self.driver.configuration.set_override('sio_round_volume_capacity',
                                               override=True)
        self.driver.extend_volume(self.volume, self.BAD_SIZE)

    def test_extend_volume(self):
        self.set_https_response_mode(self.RESPONSE_MODE.Valid)
        self.driver.extend_volume(self.volume, self.NEW_SIZE)
