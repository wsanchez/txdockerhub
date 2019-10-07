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
Tests for L{txdockerhub._clientv2}.
"""

from re import compile as regexCompile
from typing import Callable, Optional, Sequence

from hypothesis import assume, given, note
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.strategies import (
    characters, composite, just, lists, one_of, sampled_from, text, tuples
)

from twisted.trial.unittest import SynchronousTestCase

from .._clientv2 import InvalidRepositoryNameError, V2Client


__all__ = ()


componentRegex = regexCompile("^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


#
# Strategies
#

def componentText(
    min_size: int = 1, max_size: Optional[int] = None
) -> SearchStrategy:  # str
    """
    Strategy that generates repository name path components without separators.
    """
    return text(
        alphabet=V2Client.componentCharacters,
        min_size=min_size, max_size=max_size,
    )


def componentSeparators() -> SearchStrategy:  # str
    """
    Strategy that generates repository name path component separators.
    """
    return sampled_from(V2Client.componentSeparators)


@composite
def components(
    draw: Callable, max_size: int = V2Client.maxComponentLength
) -> str:
    """
    Strategy that generates repository name path components.
    """
    # Must start with one or more characters
    component: str = draw(componentText(max_size=max_size))

    # Add a separator and one or more characters up to max_size
    while True:
        maxLength = max_size - len(component)
        if maxLength < 2:
            # No room left
            break

        rest: str = draw(
            one_of(
                just(""),
                tuples(
                    componentSeparators(),
                    componentText(max_size=(maxLength - 1)),
                ),
            )
        )
        if not rest:
            break

        component += "".join(rest)

    return component


@composite
def repositoryNames(draw: Callable) -> str:
    """
    Strategy that generates repository names.
    """
    maxNameLength = V2Client.maxRepositoryNameLength

    name: str = draw(components())

    while True:
        component: str = draw(one_of(just(""), components()))
        if not component:
            break

        separator = draw(sampled_from(V2Client.repositoryNameSeparator))

        if len(name) + len(component) + 1 > maxNameLength:
            # Not enough room left
            break

        name += f"{separator}{component}"

    return name



class StrategyTests(SynchronousTestCase):
    """
    Tests for test strategies.
    """

    @given(components())
    def test_components_length(self, component: str) -> None:
        """
        Generated repository name path components may not be empty or exceed
        the maximum size.
        """
        self.assertGreater(len(component), 0)
        self.assertLessEqual(len(component), V2Client.maxComponentLength)


    @given(components())
    def test_components_regex(self, component: str) -> None:
        """
        Generated repository name path components match the required regular
        expression.
        """
        self.assertRegex(component, componentRegex)


    @given(repositoryNames())
    def test_repositoryNames_length(self, name: str) -> None:
        """
        Generated repository names may not be empty or exceed the maximum size.
        """
        self.assertGreater(len(name), 0)
        self.assertLessEqual(len(name), V2Client.maxRepositoryNameLength)


    @given(repositoryNames())
    def test_repositoryNames_validComponents(self, name: str) -> None:
        """
        Generated repository names are composed of valid components.
        """
        for component in name.split(V2Client.repositoryNameSeparator):
            try:
                V2Client.validateRepositoryNameComponent(component)
            except InvalidRepositoryNameError as e:
                self.fail(
                    f"Invalid path component {component!r} "
                    f"in repository name {name!r}: {e}"
                )



#
# Tests
#

class V2ClientTests(SynchronousTestCase):
    """
    Tests for V2Client.
    """

    @given(lists(components(), min_size=1))
    def test_repositoryNameComponents(
        self, componentsIn: Sequence[str]
    ) -> None:
        """
        V2Client.repositoryNameComponents() properly splits a repository name
        into its path components.
        """
        name = V2Client.repositoryNameSeparator.join(componentsIn)
        componentsOut = V2Client.repositoryNameComponents(name)
        self.assertSequenceEqual(componentsIn, componentsOut)


    def test_repositoryNameComponents_empty(self) -> None:
        """
        V2Client.repositoryNameComponents() raises InvalidRepositoryNameError
        if given an empty repository name.
        """
        e = self.assertRaises(
            InvalidRepositoryNameError,
            V2Client.repositoryNameComponents, "",
        )
        self.assertEqual(str(e), "repository name may not be empty")


    @given(components())
    def test_validateRepositoryNameComponent(self, component: str) -> None:
        """
        V2Client.repositoryNameComponents() does not raise
        InvalidRepositoryNameError for valid repository name path components.
        """
        try:
            V2Client.validateRepositoryNameComponent(component)
        except InvalidRepositoryNameError as e:
            self.fail(f"Unexpected InvalidRepositoryNameError: {e}")


    def test_validateRepositoryNameComponent_empty(self) -> None:
        """
        V2Client.repositoryNameComponents() raises InvalidRepositoryNameError
        if given an empty repository name path component.
        """
        e = self.assertRaises(
            InvalidRepositoryNameError,
            V2Client.validateRepositoryNameComponent, "",
        )
        self.assertEqual(
            str(e), "repository name path component may not be empty"
        )


    @given(
        sampled_from(V2Client.componentCharacters),
        text(
            alphabet=V2Client.componentCharacters,
            min_size=(V2Client.maxComponentLength - 1),
        ),
        sampled_from(V2Client.componentCharacters),
    )
    def test_validateRepositoryNameComponent_tooLong(
        self, first: str, middle: str, last: str
    ) -> None:
        """
        V2Client.repositoryNameComponents() raises InvalidRepositoryNameError
        if given an empty repository name path component.
        """
        component = f"{first}{middle}{last}"

        e = self.assertRaises(
            InvalidRepositoryNameError,
            V2Client.validateRepositoryNameComponent, component,
        )
        self.assertEqual(
            str(e), (
                f"repository name path component may not exceed "
                f"{V2Client.maxComponentLength} characters"
            ),
        )


    @given(
        text(
            alphabet=characters(
                blacklist_characters=V2Client.componentCharacters
            ),
            min_size=1, max_size=1,
        ),
        one_of(
            just(""), components(max_size=(V2Client.maxComponentLength - 1))
        ),
    )
    def test_validateRepositoryNameComponent_leading(
        self, prefix: str, suffix: str
    ) -> None:
        """
        V2Client.repositoryNameComponents() raises InvalidRepositoryNameError
        if given an empty repository name path component beginning with
        a character that is not a lowercase alphanumeric character.
        """
        component = f"{prefix}{suffix}"
        note(f"Component is {component!r}")

        e = self.assertRaises(
            InvalidRepositoryNameError,
            V2Client.validateRepositoryNameComponent, component,
        )
        self.assertEqual(
            str(e), (
                f"repository name path component must start with a "
                f"lowercase alphanumeric character: {component!r}"
            )
        )


    @given(
        componentText(),
        text(
            alphabet=characters(
                blacklist_characters=V2Client.componentAlphabet
            ),
            min_size=1,
        ),
        sampled_from(V2Client.componentCharacters),
    )
    def test_validateRepositoryNameComponent_rest(
        self, prefix: str, junk: str, last: str
    ) -> None:
        """
        V2Client.repositoryNameComponents() raises InvalidRepositoryNameError
        if given an empty repository name path component containing invalid
        characters.
        """
        component = f"{prefix}{junk}{last}"
        assume(len(component) < V2Client.maxComponentLength)
        note(f"Component is {component!r}")

        e = self.assertRaises(
            InvalidRepositoryNameError,
            V2Client.validateRepositoryNameComponent, component,
        )
        self.assertEqual(
            str(e), (
                f"repository name path component may only contain lowercase "
                f"alphanumeric characters and '.-_': {component!r}"
            )
        )


    @given(
        componentText(max_size=(V2Client.maxComponentLength - 1)),
        sampled_from(V2Client.componentSeparators),
    )
    def test_validateRepositoryNameComponent_trailingSeparator(
        self, prefix: str, last: str
    ) -> None:
        """
        V2Client.repositoryNameComponents() raises InvalidRepositoryNameError
        if given an empty repository name path component ending with
        a character that is not a lowercase alphanumeric character.
        """
        component = f"{prefix}{last}"
        note(f"Component is {component!r}")

        e = self.assertRaises(
            InvalidRepositoryNameError,
            V2Client.validateRepositoryNameComponent, component,
        )
        self.assertEqual(
            str(e), (
                f"repository name path component must end with a "
                f"lowercase alphanumeric character: {component!r}"
            )
        )


    @given(
        sampled_from(V2Client.componentCharacters),
        text(alphabet=V2Client.componentAlphabet),
        text(alphabet=V2Client.componentSeparators, min_size=2),
        text(alphabet=V2Client.componentAlphabet),
        sampled_from(V2Client.componentCharacters),
    )
    def test_validateRepositoryNameComponent_separatorRun(
        self, first: str, prefix: str, separators: str, suffix: str, last: str
    ) -> None:
        """
        V2Client.repositoryNameComponents() raises InvalidRepositoryNameError
        if given an empty repository name path component containing a run of
        more than one component separator character.
        """
        component = f"{first}{prefix}{separators}{suffix}{last}"
        assume(len(component) < V2Client.maxComponentLength)
        note(f"Component is {component!r}")

        e = self.assertRaises(
            InvalidRepositoryNameError,
            V2Client.validateRepositoryNameComponent, component,
        )
        self.assertEqual(
            str(e), (
                f"repository name path component may not contain more than "
                f"one component separator characters "
                f"({V2Client.componentSeparators}) in a row: {component!r}"
            )
        )


    @given(text(min_size=1))
    def test_validateRepositoryNameComponent_regex(
        self, component: str
    ) -> None:
        """
        V2Client.repositoryNameComponents() raises InvalidRepositoryNameError
        if given an empty repository name path that does not match the
        required regular expression.
        """
        # This is a simpler test than the above component tests and should
        # cover them all, but without testing specific error messages.
        # Conversely, the others should catch anything this catches, but the
        # simpler expression here may catch additional cases.
        try:
            V2Client.validateRepositoryNameComponent(component)
        except InvalidRepositoryNameError as e:
            self.assertNotRegex(
                component, componentRegex, (
                    f"{component!r} matches {componentRegex!r} but raised"
                    f"InvalidRepositoryNameError: {e}"
                )
            )
        else:
            self.assertRegex(component, componentRegex)


    @given(repositoryNames())
    def test_repositoryBaseURL(self, name: str) -> None:
        """
        V2Client.repositoryBaseURL() returns the expected base URL for the
        given repository name.
        """
        url = V2Client.repositoryBaseURL(name)
        self.assertEqual(url.asText(), f"/v2/{name}/")