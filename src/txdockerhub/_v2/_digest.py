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
Docker Hub API v2 Digest
"""

from enum import Enum, auto, unique
from string import hexdigits as _hexdigits
from typing import Any, Sequence

from attr import Attribute, attrib, attrs


__all__ = ()


# Docker Hub produces lowercase hex digits
hexdigits = _hexdigits.lower()


asHex = hex



class AutoName(Enum):
    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: Sequence[str]
    ) -> str:
        return name



@unique
class DigestAlgorithm(AutoName):
    """
    Digest Algorithm.

    Enumerated values are used in digest string representations.
    """

    sha256 = auto()



class InvalidDigestError(ValueError):
    """
    Invalid digest.
    """



@attrs(frozen=True, auto_attribs=True, kw_only=True)
class Digest(object):
    """
    Docker Hub API v2 Digest
    """

    @classmethod
    def validateAlgorithm(cls, algorithm: str) -> None:
        """
        Raise InvalidDigestError if the given algorithm is not valid.
        """
        if algorithm not in DigestAlgorithm.__members__:
            raise InvalidDigestError(
                f"unknown digest algorithm: {algorithm!r}"
            )


    @classmethod
    def normalizeHex(cls, hex: str) -> str:
        """
        Return a normalized version of the given digest hex data.
        """
        try:
            return asHex(int(hex, 16))[2:]
        except ValueError:
            raise InvalidDigestError(
                f"invalid digest hexadecimal data: {hex!r}"
            )


    @classmethod
    def validateHex(cls, hex: str) -> None:
        """
        Raise InvalidDigestError if the given hex data is not valid.
        """
        hex = cls.normalizeHex(hex)


    @classmethod
    def fromText(cls, text: str) -> "Digest":
        try:
            algorithmName, hex = text.split(":", 1)
        except ValueError:
            raise InvalidDigestError(
                f"digest must include separator: {text!r}"
            )

        try:
            algorithm = DigestAlgorithm[algorithmName]
        except KeyError:
            raise InvalidDigestError(
                f"unknown digest algorithm {algorithmName!r} "
                f"in digest {text!r}"
            )

        return Digest(algorithm=algorithm, hex=hex)


    #
    # Instance attributes
    #

    algorithm: DigestAlgorithm = DigestAlgorithm.sha256
    hex: str = attrib()


    @hex.validator
    def _validateHex(self, attribute: Attribute, value: Any) -> None:
        self.validateHex(self.hex)


    def asText(self) -> str:
        return f"{self.algorithm.name}:{self.hex}"
