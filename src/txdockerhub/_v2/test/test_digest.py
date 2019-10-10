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
from hypothesis.strategies import characters, composite, sampled_from, text

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


def hexes() -> SearchStrategy:  # str
    """
    Strategy that generates digest hex data.
    """
    return text(min_size=1, alphabet=mixedCaseHexdigits)


def notHexes() -> SearchStrategy:  # str
    """
    Strategy that generates digest non-hex data.
    """
    return text(min_size=1).filter(
        lambda s: not any((c in mixedCaseHexdigits) for c in s)
    )


@composite
def digests(draw: Callable) -> Digest:
    """
    Strategy that generates digests.
    """
    return Digest(algorithm=draw(algorithms()), hex=draw(hexes()))



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


    @given(hexes())
    def test_hexes(self, hex: str) -> None:
        """
        Generated hex data are valid.
        """
        try:
            int(hex, 16)
        except ValueError as e:  # pragma: no cover
            self.fail(
                f"invalid hex data {hex!r}: {e}"
            )


    @given(notHexes())
    def test_notHexes(self, notHex: str) -> None:
        """
        Generated non-hex data are not hex data.
        """
        self.assertRaises(
            ValueError, int, notHex, 16
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


    @given(hexes())
    def test_normalizeHex(self, hexIn: str) -> None:
        """
        Digest.normalizeHex() lowercases the given hex data.
        """
        hexOut = Digest.normalizeHex(hexIn)
        self.assertEqual(int(hexOut, 16), int(hexIn, 16))


    @given(notHexes())
    def test_validateHex_badCharacters(self, notHex: str) -> None:
        """
        Digest.validateHex() raises InvalidDigestError if non-hexadecimal
        characters are in the given hex data.
        """
        e = self.assertRaises(
            InvalidDigestError, Digest.validateHex, notHex
        )
        self.assertEqual(
            str(e), f"invalid digest hexadecimal data: {notHex!r}"
        )


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
        unknown algorithm.
        """
        text = f"{algorithm}:{hex}"
        e = self.assertRaises(InvalidDigestError, Digest.fromText, text)
        self.assertEqual(
            str(e),
            f"unknown digest algorithm {algorithm!r} in digest {text!r}",
        )


    @given(digests())
    def test_init(self, digestIn: Digest) -> None:
        """
        Digest() captures the given algorithm and hex data.
        """
        digestOut = Digest(algorithm=digestIn.algorithm, hex=digestIn.hex)
        self.assertEqual(digestOut, digestIn)


    @given(notHexes())
    def test_init_badHex(self, hex: str) -> None:
        """
        Digest() raises InvalidDigestError if given an invalid hex data value.
        """
        self.assertRaises(InvalidDigestError, Digest, hex=hex)
        # Not checking message, since different errors could happen here.


    @given(digests())
    def test_asText(self, digestIn: Digest) -> None:
        digestOut = Digest(algorithm=digestIn.algorithm, hex=digestIn.hex)
        self.assertEqual(
            digestOut.asText(), f"{digestIn.algorithm.value}:{digestIn.hex}"
        )
