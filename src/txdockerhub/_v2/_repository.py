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
Docker Hub API v2 Repository
"""

from string import ascii_lowercase, digits
from typing import Any, ClassVar, List, Sequence

from attr import Attribute, attrib, attrs


__all__ = ()



class InvalidRepositoryNameError(ValueError):
    """
    Invalid repository name.
    """



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Repository(object):
    """
    Docker Hub API v2 Repository
    """

    #
    # Class attributes
    #

    pathComponentCharacters: ClassVar[str] = ascii_lowercase + digits
    pathComponentSeparators: ClassVar[str] = ".-_"
    pathComponentAlphabet: ClassVar[str] = (
        pathComponentCharacters + pathComponentSeparators
    )
    maxPathComponentLength: ClassVar[int] = 30

    nameSeparator: ClassVar[str] = "/"
    maxNameLength: ClassVar[int] = 256


    @classmethod
    def namePathComponents(cls, name: str) -> Sequence[str]:
        """
        Split a repository name into its path components and return a sequence
        of those components.
        """
        if not name:
            raise InvalidRepositoryNameError(
                f"repository name may not be empty"
            )
        return name.split(cls.nameSeparator)


    @classmethod
    def validateNamePathComponent(cls, component: str) -> None:
        """
        Raise InvalidRepositoryNameError if the given path component is not
        valid.
        """
        if not component:
            raise InvalidRepositoryNameError(
                f"repository name path component may not be empty"
            )

        if len(component) > cls.maxPathComponentLength:
            raise InvalidRepositoryNameError(
                f"repository name path component may not exceed "
                f"{cls.maxPathComponentLength} characters"
            )

        if component[0] not in cls.pathComponentCharacters:
            raise InvalidRepositoryNameError(
                f"repository name path component must start with a "
                f"lowercase alphanumeric character: {component!r}"
            )

        if component[-1] not in cls.pathComponentCharacters:
            raise InvalidRepositoryNameError(
                f"repository name path component must end with a "
                f"lowercase alphanumeric character: {component!r}"
            )

        if component[1:].strip(cls.pathComponentAlphabet):
            raise InvalidRepositoryNameError(
                f"repository name path component may only contain "
                f"lowercase alphanumeric characters and "
                f"{cls.pathComponentSeparators!r}: {component!r}"
            )

        indexes: List[int] = []
        for separator in cls.pathComponentSeparators:
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
                        f"({cls.pathComponentSeparators}) in a row: "
                        f"{component!r}"
                    )
                last = i


    @classmethod
    def validateName(cls, name: str) -> None:
        """
        Raise InvalidRepositoryNameError if the given repository name is not
        valid.
        """
        if not name:
            raise InvalidRepositoryNameError(
                f"repository name may not be empty"
            )

        if len(name) > cls.maxNameLength:
            raise InvalidRepositoryNameError(
                f"repository name may not exceed {cls.maxNameLength} "
                f"characters"
            )

        components = cls.namePathComponents(name)

        for component in components:
            cls.validateNamePathComponent(component)


    #
    # Instance attributes
    #

    name: str = attrib()

    @name.validator
    def _validateName(self, attribute: Attribute, value: Any) -> None:
        self.validateName(value)
