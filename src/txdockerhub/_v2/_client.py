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

from attr import attrs

from hyperlink import DecodedURL

from ._repository import Repository


__all__ = ()



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Client(object):
    """
    Docker Hub API v2 Client
    """

    apiVersion: ClassVar[str] = "2"
    apiBaseURL: ClassVar[DecodedURL] = DecodedURL.fromText(f"/v{apiVersion}/")


    @classmethod
    def repositoryBaseURL(cls, name: str) -> DecodedURL:
        """
        Build and return the base URL for endpoints that operate on a given
        repository.
        """
        url = cls.apiBaseURL
        for component in Repository.namePathComponents(name):
            url = url.child(component)
        url = url.child("")

        return url
