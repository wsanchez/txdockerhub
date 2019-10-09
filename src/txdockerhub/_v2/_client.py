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

See: https://docs.docker.com/registry/spec/api/
"""

from string import ascii_lowercase, digits
from typing import ClassVar, List, Sequence

from attr import attrs

from hyperlink import DecodedURL


__all__ = ()



class InvalidRepositoryNameError(ValueError):
    """
    Invalid repository name.
    """



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Client(object):
    """
    Docker Hub API v2 Client
    """

    apiBaseURL: ClassVar[DecodedURL] = DecodedURL.fromText("/v2/")

    componentCharacters: ClassVar[str] = ascii_lowercase + digits
    componentSeparators: ClassVar[str] = ".-_"
    componentAlphabet: ClassVar[str] = (
        componentCharacters + componentSeparators
    )
    maxComponentLength: ClassVar[int] = 30

    repositoryNameSeparator: ClassVar[str] = "/"
    maxRepositoryNameLength: ClassVar[int] = 256


    @classmethod
    def repositoryNameComponents(cls, name: str) -> Sequence[str]:
        """
        Split a repository name into its path components and return a sequence
        of those components.
        """
        if not name:
            raise InvalidRepositoryNameError(
                f"repository name may not be empty"
            )
        return name.split(cls.repositoryNameSeparator)


    @classmethod
    def validateRepositoryNameComponent(cls, component: str) -> None:
        """
        Raise InvalidRepositoryNameError if the given path component is not
        valid.
        """
        if not component:
            raise InvalidRepositoryNameError(
                f"repository name path component may not be empty"
            )

        if len(component) > cls.maxComponentLength:
            raise InvalidRepositoryNameError(
                f"repository name path component may not exceed "
                f"{Client.maxComponentLength} characters"
            )

        if component[0] not in cls.componentCharacters:
            raise InvalidRepositoryNameError(
                f"repository name path component must start with a "
                f"lowercase alphanumeric character: {component!r}"
            )

        if component[-1] not in cls.componentCharacters:
            raise InvalidRepositoryNameError(
                f"repository name path component must end with a "
                f"lowercase alphanumeric character: {component!r}"
            )

        if component[1:].strip(cls.componentAlphabet):
            raise InvalidRepositoryNameError(
                f"repository name path component may only contain "
                f"lowercase alphanumeric characters and "
                f"{cls.componentSeparators!r}: {component!r}"
            )

        indexes: List[int] = []
        for separator in cls.componentSeparators:
            indexes.extend(
                i for i, c in enumerate(component) if c == separator
            )
        indexes.sort()
        if indexes:
            last = indexes[0]
            for i in indexes[1:]:
                if (i - last) == 1:
                    raise InvalidRepositoryNameError(
                        f"repository name path component may not contain more "
                        f"than one component separator characters "
                        f"({cls.componentSeparators}) in a row: {component!r}"
                    )
                last = i


    @classmethod
    def validateRepositoryName(cls, name: str) -> None:
        if not name:
            raise InvalidRepositoryNameError(
                f"repository name may not be empty"
            )

        if len(name) > cls.maxRepositoryNameLength:
            raise InvalidRepositoryNameError(
                f"repository name may not exceed "
                f"{Client.maxRepositoryNameLength} characters"
            )

        components = cls.repositoryNameComponents(name)

        for component in components:
            cls.validateRepositoryNameComponent(component)


    @classmethod
    def repositoryBaseURL(cls, name: str) -> DecodedURL:
        """
        Build and return the base URL for endpoints that operate on a given
        repository.
        """
        url = cls.apiBaseURL
        for component in cls.repositoryNameComponents(name):
            url = url.child(component)
        url = url.child("")

        return url
