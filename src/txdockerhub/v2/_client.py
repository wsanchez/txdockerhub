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

from typing import ClassVar

from attr import Attribute, attrib, attrs

from hyperlink import URL

from treq import get

from ._repository import Repository


__all__ = ()



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Endpoint(object):
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

    apiVersion: ClassVar[str] = "2"

    defaultRootURL = URL.fromText("https://registry.hub.docker.com/")


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
        # breakpoint()
        respose = await get(self._endpoint.api.asText())
        respose
        return True
