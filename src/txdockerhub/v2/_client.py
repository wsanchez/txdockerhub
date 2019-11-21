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
Docker Hub API v2 Client
"""

from sys import stdout
from typing import Any, ClassVar, Optional

from attr import Attribute, attrib, attrs

from click import (
    group as commandGroup,
    option as commandOption, version_option as versionOption,
)

from hyperlink import URL

from treq import get as httpGET

from twisted.application.runner._runner import Runner
from twisted.internet.defer import ensureDeferred
from twisted.internet.protocol import Factory
from twisted.logger import Logger
from twisted.python.failure import Failure
from twisted.web.http import NOT_FOUND, OK, UNAUTHORIZED
from twisted.web.http_headers import Headers
from twisted.web.iweb import IResponse

from ._error import Error, ErrorCode
from ._repository import Repository


__all__ = ()


dockerHubRegistryURL = "https://registry-1.docker.io/"



@attrs(auto_attribs=True, auto_exc=True)
class ProtocolError(Exception):
    """
    API protocol error.
    """

    url: URL
    message: str



@attrs(auto_attribs=True, auto_exc=True)
class ProtocolNotSupportedError(ProtocolError):
    """
    API protocol error.
    """



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Endpoint(object):
    """
    Computes API Endpoint URLs.
    """

    apiVersion: str
    root: URL = attrib()


    @root.validator
    def _validateRoot(self, attribute: Attribute, value: URL) -> None:
        if value.path and value.path[-1]:
            raise ValueError(f'root URL must end in "/": {value!r}')


    @property
    def api(self) -> URL:
        return self.root.click(f"v{self.apiVersion}/")


    def repository(self, repository: Repository) -> URL:
        url = self.api
        for component in repository.namePathComponents(repository.name):
            url = url.child(component)
        url = url.child("")

        return url



@attrs(frozen=False, auto_attribs=True, kw_only=True, eq=False)
class Authorization(object):
    """
    Authorization state.
    """

    token: Optional[str] = None



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Client(object):
    """
    Docker Hub API v2 Client
    """

    #
    # Class attributes
    #

    log: ClassVar[Logger] = Logger()

    apiVersion: ClassVar[str] = "2"

    defaultRootURL = URL.fromText(dockerHubRegistryURL)


    @classmethod
    def main(cls) -> None:
        """
        Command line entry point.
        """
        main()


    #
    # Instance attributes
    #

    rootURL: URL = attrib(default=defaultRootURL)

    _endpoint: Endpoint = attrib(init=False)
    _auth: Authorization = attrib(factory=Authorization, init=False)


    def __attrs_post_init__(self) -> None:
        object.__setattr__(
            self, "_endpoint",
            Endpoint(apiVersion=self.apiVersion, root=self.rootURL)
        )


    async def get(self, url: URL) -> IResponse:
        """
        Send a GET request.
        """
        async def get() -> IResponse:
            headers = Headers({})
            if self._auth.token:
                headers.setRawHeaders(
                    "Authorization", [f"Bearer {self._auth.token}"]
                )

            self.log.info(
                "GET: {url}\nHeaders: {headers}", url=url, headers=headers
            )

            response = await httpGET(url.asText(), headers=headers)

            self.log.info(
                "Response: {response}\nHeaders: {response.headers}",
                response=response,
            )

            return response

        response = await(get())

        if response.code == UNAUTHORIZED:
            await self.handleUnauthorizedResponse(url, response)
            response = await(get())

        return response


    async def handleUnauthorizedResponse(
        self, url: URL, response: IResponse
    ) -> None:
        """
        Handle an UNAUTHORIZED response.
        """
        challengeValues = response.headers.getRawHeaders("WWW-Authenticate")

        if not challengeValues:
            raise ProtocolError(
                url, "UNAUTHORIZED response with no WWW-Authenticate header"
            )

        challengeValue = challengeValues[-1]

        if challengeValue.startswith("Bearer "):
            challengeParams = {
                k: v[1:-1] if v.startswith('"') and v.endswith('"') else v
                for k, v in
                (token.split("=") for token in challengeValue[7:].split(","))
            }

            try:
                realmText = challengeParams["realm"]
            except KeyError:
                raise ProtocolError(
                    url, "WWW-Authenticate header with no realm"
                )

            realm = URL.fromText(realmText)

            try:
                service = challengeParams["service"]
            except KeyError:
                raise ProtocolError(
                    url, "WWW-Authenticate header with no service"
                )

            error = challengeParams.get("error", None)
            if error is not None:
                message = await response.text()
                self.log.error(
                    "got error ({error}) in auth challenge: {message}",
                    error=error, message=message,
                )

        else:
            raise ProtocolError(
                url,
                f"WWW-Authenticate header with unknown mechanism: "
                f"{challengeValue}"
            )

        await self.getAuthToken(realm, service)


    async def getAuthToken(self, realm: URL, service: str) -> None:
        """
        Obtain an authorization token from the registry.
        """
        # See https://docs.docker.com/registry/spec/auth/token/

        url = realm.set("service", service)

        self.log.info("Authenticating at {url}...", url=url)

        response = await httpGET(url.asText())
        json = await response.json()

        try:
            self._auth.token = json["token"]
        except KeyError:
            raise ProtocolError(realm, "got auth response with no token")

        # Not captured:
        #   expires_in -> int
        #   issued_at -> date


    async def ping(self) -> None:
        """
        Check whether the registry host supports the API version in use by
        the client.
        """
        url = self._endpoint.api

        self.log.info("Pinging API server at {url}...", url=url)

        response = await self.get(url)

        if response.code == OK:
            return

        if response.code == NOT_FOUND:
            raise ProtocolNotSupportedError(
                url, "server does not support Docker Registry HTTP API V2"
            )

        if response.code == UNAUTHORIZED:
            json = await response.json()
            message = "authorization failed"
            for error in (Error.fromJSON(e) for e in json.get("errors", [])):
                self.log.error(
                    "Error ({error.code.name}): {error.message}", error=error
                )
                if error.code is ErrorCode.UNAUTHORIZED:
                    message = f"{message}: {error.message}"
            raise ProtocolError(url, message)

#
# Command line
#

def run(methodName: str, **kwargs: Any) -> None:
    """
    Run the application service.
    """
    from twisted.internet import reactor

    # Keep Factory from logging every new protocol object
    Factory.noisy = False

    client = Client()
    method = getattr(client, methodName)

    def whenRunning(**kwargs: Any) -> None:
        def success(value: Any) -> None:
            reactor.stop()

        def error(failure: Failure) -> None:
            client.log.failure(
                "While running {methodName}({args()})",
                failure=failure, methodName=methodName,
                args=lambda: ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
            )
            reactor.stop()

        d = ensureDeferred(method(**kwargs))
        d.addCallbacks(success, error)

    runner = Runner(
        reactor=reactor,
        logFile=stdout,
        whenRunning=whenRunning,
        whenRunningArguments=kwargs,
    )
    runner.run()


@commandGroup()
@versionOption()
def main() -> None:
    """
    Docker Hub client.
    """


@main.command()
@commandOption(
    "--root", show_default=True, show_envvar=True,
    help="URL for the repository API base endpoint",
)
def ping(root: str = dockerHubRegistryURL) -> None:
    """
    Check Docker Hub service for availability and compatibility.
    """
    run("ping")


if __name__ == "__main__":
    main()
