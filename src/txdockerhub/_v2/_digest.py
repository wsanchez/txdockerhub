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
from typing import Sequence

from attr import attrs


__all__ = ()


# Docker Hub produces lowercase hex digits
hexdigits = _hexdigits.lower()



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
        return hex.lower()


    @classmethod
    def validateHex(cls, hex: str, algorithm: DigestAlgorithm) -> None:
        """
        Raise InvalidDigestError if the given hex data is not valid.
        """
        if cls.normalizeHex(hex).strip(hexdigits):
            raise InvalidDigestError(
                f"digest hex data may only contain hexadecimal numbers: "
                f"{hex!r}"
            )

        if algorithm is DigestAlgorithm.sha256:
            if len(hex) != 64:
                raise InvalidDigestError(
                    f"SHA-256 digest hex data must contain 64 digits: {hex!r}"
                )

        else:
            raise AssertionError(f"unknown digest algorithm: {algorithm!r}")


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

    algorithm: DigestAlgorithm
    hex: str


    def __attr_post_init__(self) -> None:
        self.validateHex(self.hex, self.algorithm)


    def asText(self) -> str:
        return f"{self.algorithm.name}:{self.hex}"
