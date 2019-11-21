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
from string import hexdigits as upperCaseHexDigits
from typing import Sequence

from attr import attrs


__all__ = ()


# Docker Hub produces lowercase hex digits
lowerCaseHexDigits = upperCaseHexDigits.lower()
hexDigits = "".join(frozenset(lowerCaseHexDigits + upperCaseHexDigits))


asHex = hex


class AutoName(str, Enum):
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

    #
    # Class attributes
    #

    @classmethod
    def fromText(cls, text: str) -> "Digest":
        try:
            algorithmName, hexData = text.split(":", 1)
        except ValueError:
            raise InvalidDigestError(f"digest must include separator: {text!r}")

        try:
            algorithm = DigestAlgorithm[algorithmName]
        except KeyError:
            raise InvalidDigestError(
                f"unknown digest algorithm {algorithmName!r} "
                f"in digest {text!r}"
            )

        if any((digit not in hexDigits) for digit in hexData):
            raise InvalidDigestError(
                f"invalid hexadecimal data {hexData!r} " f"in digest {text!r}"
            )

        hex = int(hexData, 16)

        return Digest(algorithm=algorithm, hex=hex)

    #
    # Instance attributes
    #

    algorithm: DigestAlgorithm = DigestAlgorithm.sha256
    hex: int

    def asText(self) -> str:
        return f"{self.algorithm.value}:{asHex(self.hex)[2:]}"
