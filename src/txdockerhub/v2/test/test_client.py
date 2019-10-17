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
Tests for L{txdockerhub.v2._client}.
"""

from string import ascii_letters
from typing import Any, Callable, Type

from hyperlink import URL

from hypothesis import given
from hypothesis.strategies import (
    characters, composite, integers, lists, sampled_from, text
)

from twisted.internet.defer import Deferred, ensureDeferred
from twisted.python.failure import Failure
from twisted.trial.unittest import SynchronousTestCase as _SynchronousTestCase

from .test_repository import repositories
from .._client import Client, Endpoint
from .._repository import Repository


__all__ = ()



# Can get rid of this in Twisted > 19.7
class SynchronousTestCase(_SynchronousTestCase):

    def successResultOf(self, deferred: Deferred) -> Any:
        deferred = ensureDeferred(deferred)
        return super().successResultOf(deferred)


    def failureResultOf(
        self, deferred: Deferred, *expectedExceptionTypes: Type[BaseException]
    ) -> Failure:
        deferred = ensureDeferred(deferred)
        return super().failureResultOf(deferred, *expectedExceptionTypes)



#
# Strategies
#

@composite
def versions(draw: Callable) -> str:
    """
    Strategy that generates API versions.
    """
    return str(draw(integers()))


@composite
def urls(draw: Callable, collection: bool = False) -> str:
    """
    Strategy that generates URLs.
    """
    segments = draw(
        lists(
            text(
                alphabet=characters(blacklist_characters="/?#"), max_size=32,
            ),
            max_size=16,
        )
    )

    url = URL(
        scheme=draw(sampled_from(("http", "https"))),
        host=draw(text(alphabet=ascii_letters)),  # FIXME: wimpy alphabet
        port=draw(integers(min_value=1, max_value=65535)),
        path=segments,
    )

    if collection:
        url = url.child("")

    return url


@composite
def endpoints(draw: Callable) -> Endpoint:
    """
    Strategy that generates Endpoints.
    """
    return Endpoint(
        apiVersion=draw(versions()), root=draw(urls(collection=True))
    )



class StrategyTests(SynchronousTestCase):
    """
    Tests for test strategies.
    """

    @given(versions())
    def test_versions(self, version: str) -> None:
        """
        Generated versions are valid.
        """
        self.assertIsInstance(version, str)


    @given(urls())
    def test_urls(self, url: URL) -> None:
        """
        Generated URLs are valid.
        """
        self.assertIsInstance(url, URL)


    @given(urls(collection=True))
    def test_urls_collections(self, url: URL) -> None:
        """
        Generated URLs are collections.
        """
        self.assertFalse(url.path and url.path[-1])


#
# Tests
#

class EndpointTests(SynchronousTestCase):
    """
    Tests for Endpoint.
    """

    @given(endpoints())
    def test_api(self, endpoint: Endpoint) -> None:
        """
        Endpoint.api equals the API version URL.
        """
        self.assertEqual(
            endpoint.api, endpoint.root.click(f"v{endpoint.apiVersion}/")
        )


    @given(endpoints(), repositories())
    def test_repository(
        self, endpoint: Endpoint, repository: Repository
    ) -> None:
        """
        Endpoint.repository() returns the URL for the given repository name.
        """
        self.assertEqual(
            endpoint.repository(repository),
            endpoint.root.click(f"v{endpoint.apiVersion}/{repository.name}/")
        )



class ClientTests(SynchronousTestCase):
    """
    Tests for Client.
    """

    def test_ping(self) -> None:
        client = Client()
        result = self.successResultOf(client.ping())
        self.assertTrue(result)
