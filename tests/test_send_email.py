import unittest
import types
import sys
from unittest.mock import patch

paper_stub = types.ModuleType("paper")
paper_stub.ArxivPaper = object
sys.modules.setdefault("paper", paper_stub)

tqdm_stub = types.ModuleType("tqdm")
tqdm_stub.tqdm = lambda iterable=None, **_: iterable if iterable is not None else []
sys.modules.setdefault("tqdm", tqdm_stub)

loguru_stub = types.ModuleType("loguru")

class StubLogger:
    def warning(self, *_):
        pass

loguru_stub.logger = StubLogger()
sys.modules.setdefault("loguru", loguru_stub)

from construct_email import send_email


class FakeSmtpServer:
    def __init__(self):
        self.logged_in = False
        self.sent = False
        self.quit_called = False
        self.starttls_called = False

    def ehlo(self):
        return None

    def starttls(self):
        self.starttls_called = True
        return None

    def login(self, *_):
        self.logged_in = True

    def sendmail(self, *_):
        self.sent = True

    def quit(self):
        self.quit_called = True


class SendEmailTests(unittest.TestCase):
    def test_send_email_with_tls(self):
        server = FakeSmtpServer()
        with patch("construct_email.smtplib.SMTP", return_value=server), patch(
            "construct_email.smtplib.SMTP_SSL"
        ) as smtp_ssl:
            send_email(
                "sender@example.com",
                "receiver@example.com",
                "x",
                "smtp.example.com",
                587,
                "<p>hello</p>",
            )

        smtp_ssl.assert_not_called()
        self.assertTrue(server.starttls_called)
        self.assertTrue(server.logged_in)
        self.assertTrue(server.sent)
        self.assertTrue(server.quit_called)

    def test_send_email_falls_back_to_ssl(self):
        tls_server = FakeSmtpServer()
        ssl_server = FakeSmtpServer()

        def _raise_on_starttls():
            raise RuntimeError("tls not supported")

        tls_server.starttls = _raise_on_starttls

        with patch("construct_email.smtplib.SMTP", return_value=tls_server), patch(
            "construct_email.smtplib.SMTP_SSL", return_value=ssl_server
        ) as smtp_ssl:
            send_email(
                "sender@example.com",
                "receiver@example.com",
                "x",
                "smtp.example.com",
                465,
                "<p>hello</p>",
            )

        smtp_ssl.assert_called_once_with("smtp.example.com", 465)
        self.assertTrue(ssl_server.logged_in)
        self.assertTrue(ssl_server.sent)
        self.assertTrue(ssl_server.quit_called)

    def test_send_email_requires_smtp_server_and_port(self):
        with self.assertRaises(ValueError):
            send_email(
                "sender@example.com",
                "receiver@example.com",
                "x",
                "",
                587,
                "<p>hello</p>",
            )
        with self.assertRaises(ValueError):
            send_email(
                "sender@example.com",
                "receiver@example.com",
                "x",
                "smtp.example.com",
                None,
                "<p>hello</p>",
            )


if __name__ == "__main__":
    unittest.main()
