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

from contextlib import contextmanager
from functools import partial
from string import ascii_letters
from typing import (
    Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Type, Union
)
from unittest.mock import patch

from attr import attrs

from hyperlink import URL

from hypothesis import given
from hypothesis.strategies import (
    characters, composite, integers, lists, sampled_from, text
)

from treq.testing import RequestSequence, StringStubbingResource, StubTreq

from twisted.internet.defer import Deferred, ensureDeferred
from twisted.python.failure import Failure
from twisted.trial.unittest import SynchronousTestCase as _SynchronousTestCase
from twisted.web.http import UNAUTHORIZED
from twisted.web.http_headers import Headers

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
# Helpers for mocking treq
# treq.testing uses janky tuples for test data. See:
# https://treq.readthedocs.io/en/release-17.8.0/api.html#treq.testing.RequestSequence
#
TreqExpectedRequest = Tuple[
    bytes,                            # method
    str,                              # url
    Dict[bytes, List[bytes]],         # params
    Dict[bytes, List[bytes]],         # headers
    bytes,                            # data
]
TreqCannedResponse = Tuple[
    int,                                     # code
    Dict[bytes, Union[bytes, List[bytes]]],  # headers
    bytes,                                   # body
]
TreqExpectedRequestsAndResponses = Sequence[
    Tuple[TreqExpectedRequest, TreqCannedResponse]
]



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class ExpectedRequest(Exception):
    """
    Expected request.
    """

    method: str
    url: URL
    headers: Headers
    body: bytes


    def asTreqExpectedRequest(self) -> TreqExpectedRequest:
        """
        Return a corresponding TreqExpectedRequest.
        """
        def params() -> Dict[bytes, List[bytes]]:
            params: Dict[bytes, List[bytes]] = {}
            for key, value in self.url.query:
                values = params.setdefault(key, [])
                values.append(value)
            return params

        return (
            self.method.lower().encode("ascii"),
            self.url.replace(query=()).asText(), params(),
            {k: v for k, v in self.headers.getAllRawHeaders()},
            self.body,
        )



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class CannedResponse(Exception):
    """
    Expected response.
    """

    code: int
    headers: Headers
    body: bytes


    def asTreqCannedResponse(self) -> TreqCannedResponse:
        """
        Return a corresponding TreqCannedResponse.
        """
        return (
            self.code,
            {k: v for k, v in self.headers.getAllRawHeaders()},
            self.body,
        )



@attrs(frozen=True, auto_attribs=True)
class ExpectedRequestsAndResponses(Exception):
    """
    Expected request and response sequence.
    """

    requestsAndResponses: Sequence[
        Tuple[ExpectedRequest, CannedResponse]
    ]

    exceptionClass: Type = AssertionError


    def asTreqExpectedRequestsAndResponses(
        self
    ) -> TreqExpectedRequestsAndResponses:
        return tuple(
            (
                request.asTreqExpectedRequest(),
                response.asTreqCannedResponse(),
            )
            for request, response in self.requestsAndResponses
        )


    def _fail(self, error: Any) -> None:
        raise self.exceptionClass(error)


    @contextmanager
    def testing(self) -> Iterator[None]:
        failures: List[Failure] = []

        requestSequence = RequestSequence(
            self.asTreqExpectedRequestsAndResponses(), failures.append
        )
        stubTreq = StubTreq(StringStubbingResource(requestSequence))

        with patch("txdockerhub.v2._client.httpGET", stubTreq.get):
            with requestSequence.consume(self._fail):
                yield

        if failures:
            self._fail(failures)



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
def urls(draw: Callable, collection: Optional[bool] = None) -> str:
    """
    Strategy that generates URLs.
    """
    urlPathText = partial(
        text, alphabet=characters(blacklist_characters="/?#"), max_size=32
    )

    segments = draw(lists(urlPathText(), max_size=16))

    url = URL(
        scheme=draw(sampled_from(("http", "https"))),
        # FIXME: wimpy host name alphabet
        host=draw(text(alphabet=ascii_letters, min_size=1)),
        port=draw(integers(min_value=1, max_value=65535)),
        path=segments,
    )

    if collection:
        url = url.child("")
    else:
        if collection is not None:
            url = url.child(draw(urlPathText(min_size=1)))

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


    @given(urls(collection=False))
    def test_urls_notCollections(self, url: URL) -> None:
        """
        Generated URLs are not collections.
        """
        self.assertTrue(url.path and url.path[-1])


#
# Tests
#

class EndpointTests(SynchronousTestCase):
    """
    Tests for Endpoint.
    """

    @given(versions(), urls(collection=True))
    def test_root_collection(self, version: str, url: URL) -> None:
        """
        Root URL ending in "/" does not raise ValueError.
        """
        try:
            Endpoint(apiVersion=version, root=url)
        except ValueError:
            self.fail(str(url))


    @given(versions(), urls(collection=False))
    def test_root_notCollection(self, version: str, url: URL) -> None:
        """
        Root URL not ending in "/" raises ValueError.
        """
        self.assertRaises(ValueError, Endpoint, apiVersion=version, root=url)


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

    @given(urls(collection=True))
    def test_root_collection(self, url: URL) -> None:
        """
        Root URL ending in "/" does not raise ValueError.
        """
        try:
            Client(rootURL=url)
        except ValueError:
            self.fail(str(url))


    @given(urls(collection=False))
    def test_root_notCollection(self, url: URL) -> None:
        """
        Root URL not ending in "/" raises ValueError.
        """
        self.assertRaises(ValueError, Client, rootURL=url)


    def test_ping_noToken(self) -> None:
        """
        Ping when a token is not present does not send an Authorization header.
        """
        client = Client()
        expectedRequestsAndResponses = ExpectedRequestsAndResponses(
            (
                (
                    ExpectedRequest(
                        method="GET",
                        url=client._endpoint.api,
                        headers=Headers({
                            "Connection": ["close"],
                            "Accept-Encoding": ["gzip"],
                            "Host": ["registry-1.docker.io"],
                        }),
                        body=b"",
                    ),
                    CannedResponse(
                        code=UNAUTHORIZED,
                        headers=Headers({
                            "WWW-Authenticate": [
                                'Bearer realm="foo",service="bar"'
                            ],
                        }),
                        body=b"",
                    ),
                ),
            ),
            exceptionClass=self.failureException,
        )
        with expectedRequestsAndResponses.testing():
            self.successResultOf(client.ping())
