"""
Tests for the parts of jsonschema related to the :kw:`format` keyword.
"""

from unittest import TestCase

from jsonschema import FormatChecker, ValidationError
from jsonschema.exceptions import FormatError
from jsonschema.validators import Draft4Validator

BOOM = ValueError("Boom!")
BANG = ZeroDivisionError("Bang!")


def boom(thing):
    if thing == "bang":
        raise BANG
    raise BOOM


class TestFormatChecker(TestCase):
    def test_it_can_validate_no_formats(self):
        checker = FormatChecker(formats=())
        self.assertFalse(checker.checkers)

    def test_it_raises_a_key_error_for_unknown_formats(self):
        with self.assertRaises(KeyError):
            FormatChecker(formats=["o noes"])

    def test_it_can_register_cls_checkers(self):
        original = dict(FormatChecker.checkers)
        self.addCleanup(FormatChecker.checkers.pop, "boom")
        with self.assertWarns(DeprecationWarning):
            FormatChecker.cls_checks("boom")(boom)
        self.assertEqual(
            FormatChecker.checkers,
            dict(original, boom=(boom, ())),
        )

    def test_it_can_register_checkers(self):
        checker = FormatChecker()
        checker.checks("boom")(boom)
        self.assertEqual(
            checker.checkers,
            dict(FormatChecker.checkers, boom=(boom, ())),
        )

    def test_it_catches_registered_errors(self):
        checker = FormatChecker()
        checker.checks("boom", raises=type(BOOM))(boom)

        with self.assertRaises(FormatError) as cm:
            checker.check(instance=12, format="boom")

        self.assertIs(cm.exception.cause, BOOM)
        self.assertIs(cm.exception.__cause__, BOOM)
        self.assertEqual(str(cm.exception), "12 is not a 'boom'")

        # Unregistered errors should not be caught
        with self.assertRaises(type(BANG)):
            checker.check(instance="bang", format="boom")

    def test_format_error_causes_become_validation_error_causes(self):
        checker = FormatChecker()
        checker.checks("boom", raises=ValueError)(boom)
        validator = Draft4Validator({"format": "boom"}, format_checker=checker)

        with self.assertRaises(ValidationError) as cm:
            validator.validate("BOOM")

        self.assertIs(cm.exception.cause, BOOM)
        self.assertIs(cm.exception.__cause__, BOOM)

    def test_format_checkers_come_with_defaults(self):
        # This is bad :/ but relied upon.
        # The docs for quite awhile recommended people do things like
        # validate(..., format_checker=FormatChecker())
        # We should change that, but we can't without deprecation...
        checker = FormatChecker()
        with self.assertRaises(FormatError):
            checker.check(instance="not-an-ipv4", format="ipv4")


    def test_it_rejects_a_single_trailing_newline(self):
        # The validators backing these formats accept exactly one trailing
        # newline, but the format grammars do not allow one (GH#1588)
        checker = FormatChecker()
        trailing_newline = [
            ("date-time", "1985-04-12T23:20:50Z\n"),
            ("uri", "http://foo.bar/\n"),
            ("uri-reference", "http://foo.bar/\n"),
            ("iri", "http://foo.bar/\n"),
            ("iri-reference", "http://foo.bar/\n"),
            ("hostname", "example.com\n"),
        ]
        for format, instance in trailing_newline:
            if format not in checker.checkers:
                continue  # optional format dependency not installed
            with self.subTest(format=format):
                self.assertFalse(checker.conforms(instance, format))

        # the values without the trailing newline stay valid
        valid = [
            ("date-time", "1985-04-12T23:20:50Z"),
            ("uri", "http://foo.bar/"),
            ("iri", "http://foo.bar/"),
            ("hostname", "example.com"),
        ]
        for format, instance in valid:
            if format not in checker.checkers:
                continue  # optional format dependency not installed
            with self.subTest(format=format):
                self.assertTrue(checker.conforms(instance, format))

    def test_repr(self):
        checker = FormatChecker(formats=())
        checker.checks("foo")(lambda thing: True)  # pragma: no cover
        checker.checks("bar")(lambda thing: True)  # pragma: no cover
        checker.checks("baz")(lambda thing: True)  # pragma: no cover
        self.assertEqual(
            repr(checker),
            "<FormatChecker checkers=['bar', 'baz', 'foo']>",
        )
