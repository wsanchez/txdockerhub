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
from typing import Any, Callable, ClassVar

from attr import Attribute, attrib, attrs

from click import (
    group as commandGroup,
    option as commandOption, version_option as versionOption,
)

from hyperlink import URL

from treq import get

from twisted.application.runner._runner import Runner
from twisted.internet.defer import ensureDeferred
from twisted.logger import Logger

from ._repository import Repository


__all__ = ()


dockerHubRegistryURL = "https://registry.hub.docker.com/"



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Endpoint(object):
    """
    API Endpoint URL.
    """

    apiVersion: str
    root: URL = attrib()


    @root.validator
    def _validateRoot(self, attribute: Attribute, value: URL) -> None:
        if value.path and value.path[-1]:
            raise ValueError(f"""Root URL must end in "/": {value!r}""")


    @property
    def api(self) -> URL:
        return self.root.click(f"v{self.apiVersion}/")


    def repository(self, repository: Repository) -> URL:
        url = self.api
        for component in repository.namePathComponents(repository.name):
            url = url.child(component)
        url = url.child("")

        return url



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


    def __attrs_post_init__(self) -> None:
        object.__setattr__(
            self, "_endpoint",
            Endpoint(apiVersion=self.apiVersion, root=self.rootURL),
        )


    async def ping(self) -> bool:
        """
        Check whether the registry host supports the API version in use by
        the client.
        """
        await self.get(self._endpoint.api)

        return True



#
# Command line
#

def run(methodName: str, **kwargs: Any) -> None:
    """
    Run the application service.
    """
    from twisted.internet import reactor

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
