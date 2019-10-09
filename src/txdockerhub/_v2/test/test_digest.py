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
Tests for L{txdockerhub._v2._digest}.
"""

from string import hexdigits as lowerCaseHexdigits
from typing import Any, Callable

from hypothesis import given
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import (
    characters, composite, data, sampled_from, text
)

from twisted.trial.unittest import SynchronousTestCase

from .._digest import Digest, DigestAlgorithm, InvalidDigestError

# FIXME: Not publicly available from hypothesis
DataStrategy = Any


__all__ = ()


#
# Strategies
#

mixedCaseHexdigits = "".join(
    frozenset(lowerCaseHexdigits + lowerCaseHexdigits.upper())
)


def algorithms() -> SearchStrategy:  # DigestAlgorithm
    """
    Strategy that generates digest algorithms.
    """
    return sampled_from(DigestAlgorithm)


def hexes(
    algorithm: DigestAlgorithm, lowerCase: bool = False
) -> SearchStrategy:  # str
    """
    Strategy that generates digest hex data.
    """
    assert algorithm is DigestAlgorithm.sha256

    if lowerCase:
        alphabet = lowerCaseHexdigits
    else:
        alphabet = mixedCaseHexdigits

    return text(alphabet=alphabet, min_size=64, max_size=64)


@composite
def digests(draw: Callable) -> Digest:
    """
    Strategy that generates digests.
    """
    algorithm = draw(algorithms())
    hex = draw(hexes(algorithm))

    return Digest(algorithm=algorithm, hex=hex)



class StrategyTests(SynchronousTestCase):
    """
    Tests for test strategies.
    """

    @given(algorithms())
    def test_algorithms(self, algorithm: DigestAlgorithm) -> None:
        """
        Generated algorithms are in the DigestAlgorithm enumeration.
        """
        self.assertIn(algorithm, DigestAlgorithm)


    @given(data())
    def test_hexes(self, data: DataStrategy) -> None:
        """
        Generated hex data are valid.
        """
        algorithm = data.draw(algorithms())
        hex = data.draw(hexes(algorithm=algorithm))

        try:
            Digest.validateHex(hex, algorithm)
        except InvalidDigestError as e:  # pragma: no cover
            self.fail(
                f"invalid hex data {hex!r} for algorithm {algorithm}: {e}"
            )


    @given(data())
    def test_hexes_lower(self, data: DataStrategy) -> None:
        """
        Generated hex data are lowercase if so specified.
        """
        algorithm = data.draw(algorithms())
        hex = data.draw(hexes(algorithm=algorithm, lowerCase=True))

        if hex.strip(lowerCaseHexdigits):  # pragma: no cover
            self.fail(
                f"hex data is not using lower case alphabet: {hex!r}"
            )


    @given(digests())
    def test_digests(self, digest: Digest) -> None:
        """
        Generated digests are valid.
        """
        self.assertIsInstance(digest, Digest)



#
# Tests
#

class DigestTests(SynchronousTestCase):
    """
    Tests for Digest.
    """

    @given(algorithms())
    def test_validateAlgorithm(self, algorithm: DigestAlgorithm) -> None:
        """
        Digest.validateAlgorithm() does not raise InvalidDigestError for
        valid digest algorithm names.
        """
        try:
            Digest.validateAlgorithm(algorithm.value)
        except InvalidDigestError as e:  # pragma: no cover
            self.fail(
                f"unexpected InvalidDigestError for algorithm {algorithm!r}: "
                f"{e}"
            )


    def test_validateAlgorithm_bogus(self) -> None:
        """
        Digest.validateAlgorithm() raises InvalidDigestError for unknown
        algorithms.
        """
        algorithm = "XYZZY"
        e = self.assertRaises(
            InvalidDigestError, Digest.validateAlgorithm, algorithm
        )
        self.assertEqual(str(e), f"unknown digest algorithm: {algorithm!r}")


    @given(digests())
    def test_normalizeHex(self, digest: Digest) -> None:
        """
        Digest.normalizeHex() lowercases the given hex data.
        """
        hex = digest.hex
        self.assertEqual(Digest.normalizeHex(hex), hex.lower())


    @given(
        text(min_size=1).filter(lambda hex: hex.strip(mixedCaseHexdigits)),
        algorithms(),
    )
    def test_validateHex_badCharacters(
        self, hex: str, algorithm: DigestAlgorithm
    ) -> None:
        """
        Digest.validateHex() raises InvalidDigestError if non-hexadecimal
        characters are in the given hex data.
        """
        e = self.assertRaises(
            InvalidDigestError, Digest.validateHex, hex, algorithm
        )
        self.assertEqual(
            str(e), (
                f"digest hex data may only contain hexadecimal numbers: "
                f"{hex!r}"
            ),
        )


    @given(
        text(alphabet=mixedCaseHexdigits, min_size=1).filter(
            lambda hex: len(hex) != 64
        ),
        algorithms(),
    )
    def test_validateHex_badLength(
        self, hex: str, algorithm: DigestAlgorithm
    ) -> None:
        """
        Digest.validateHex() raises InvalidDigestError if non-hexadecimal
        characters are in the given hex data.
        """
        e = self.assertRaises(
            InvalidDigestError, Digest.validateHex, hex, algorithm
        )
        self.assertEqual(
            str(e),
            f"SHA-256 digest hex data must contain 64 digits: {hex!r}",
        )


    def test_validateHex_bogus(self) -> None:
        """
        Digest.validateHex() raises AssertionError for unknown algorithms.
        """
        algorithm = "XYZZY"
        e = self.assertRaises(
            AssertionError, Digest.validateHex, "0" * 64, algorithm
        )
        self.assertEqual(str(e), f"unknown digest algorithm: {algorithm!r}")


    @given(digests())
    def test_fromText(self, digestIn: Digest) -> None:
        """
        Digest.fromText() returns a digest from a text representation.
        """
        digestOut = Digest.fromText(
            f"{digestIn.algorithm.name}:{digestIn.hex}"
        )
        self.assertEqual(digestOut, digestIn)


    @given(text(alphabet=characters(blacklist_characters=":")))
    def test_fromText_noColon(self, text: str) -> None:
        """
        Digest.fromText() raises InvalidDigestError if given a string with no
        ":" character.
        """
        e = self.assertRaises(InvalidDigestError, Digest.fromText, text)
        self.assertEqual(str(e), f"digest must include separator: {text!r}")


    @given(text(), text(), text())
    def test_fromText_noColonpalooza(
        self, prefix: str, middle: str, suffix: str
    ) -> None:
        """
        Digest.fromText() raises InvalidDigestError if given a string with
        multiple ":" characters.
        """
        text = f"{prefix}:{middle}:{suffix}"
        self.assertRaises(InvalidDigestError, Digest.fromText, text)
        # Not checking message, since different errors could happen here.


    @given(
        text(alphabet=characters(blacklist_characters=":")).filter(
            lambda a: a not in DigestAlgorithm.__members__.values()
        ),
        text(alphabet=characters(blacklist_characters=":")),
    )
    def test_fromText_badAlgorithm(self, algorithm: str, hex: str) -> None:
        """
        Digest.fromText() raises InvalidDigestError if given a string with an
        unknown algorithm
        """
        text = f"{algorithm}:{hex}"
        e = self.assertRaises(InvalidDigestError, Digest.fromText, text)
        self.assertEqual(
            str(e),
            f"unknown digest algorithm {algorithm!r} in digest {text!r}",
        )
