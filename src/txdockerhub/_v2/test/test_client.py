##
# See the file COPYRIGHT for copyright information.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##

"""
Tests for L{txdockerhub._v2._client}.
"""

from hypothesis import given

from twisted.trial.unittest import SynchronousTestCase

from .test_repository import repositoryNames
from .._client import Client


__all__ = ()



#
# Tests
#

class ClientTests(SynchronousTestCase):
    """
    Tests for Client.
    """

    @given(repositoryNames())
    def test_repositoryBaseURL(self, name: str) -> None:
        """
        Client.repositoryBaseURL() returns the expected base URL for the
        given repository name.
        """
        url = Client.repositoryBaseURL(name)
        self.assertEqual(url.asText(), f"/v2/{name}/")
