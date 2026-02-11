"""Integration tests for OTPEmailReader (#43).

Verifies:
- IMAP connection / disconnection
- OTP extraction from email subject and body patterns
- Timeout when no new email arrives
- New email detection (ignores pre-existing emails)
"""

import email
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch, call
import pytest

OTP_MODULE = "utils.otp_email_reader"


def _build_email_message(subject="Test", body="", from_addr="noreply@secudium.com"):
    """Build a mock email.message.Message."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    return msg


def _make_imap_mock(emails=None, search_ids=None):
    """Create a mock IMAP4_SSL with configurable email store."""
    mock_imap = MagicMock()
    mock_imap.login.return_value = ("OK", [b"Logged in"])
    mock_imap.select.return_value = ("OK", [b"1"])

    if search_ids is not None:
        mock_imap.search.return_value = ("OK", [b" ".join(str(i).encode() for i in search_ids)])
    else:
        mock_imap.search.return_value = ("OK", [b""])

    if emails:

        def fetch_side_effect(msg_id, fmt):
            idx = int(msg_id) - 1
            if 0 <= idx < len(emails):
                return ("OK", [(b"1", emails[idx].as_bytes())])
            return ("OK", [(b"1", b"")])

        mock_imap.fetch.side_effect = fetch_side_effect
    else:
        mock_imap.fetch.return_value = ("OK", [(b"1", b"")])

    mock_imap.close.return_value = ("OK", [])
    mock_imap.logout.return_value = ("BYE", [])

    return mock_imap


@pytest.mark.unit
class TestOTPEmailReaderConnect:
    """Tests for IMAP connection lifecycle."""

    def test_connect_success(self):
        """Successful IMAP login returns True."""
        mock_imap = _make_imap_mock()
        with patch(f"{OTP_MODULE}.imaplib.IMAP4_SSL", return_value=mock_imap):
            from utils.otp_email_reader import OTPEmailReader

            reader = OTPEmailReader("test@test.com", "password", "imap.test.com")
            assert reader.connect() is True
            mock_imap.login.assert_called_once_with("test@test.com", "password")

    def test_connect_failure(self):
        """Failed IMAP login returns False."""
        mock_imap = MagicMock()
        mock_imap.login.side_effect = Exception("Auth failed")
        with patch(f"{OTP_MODULE}.imaplib.IMAP4_SSL", return_value=mock_imap):
            from utils.otp_email_reader import OTPEmailReader

            reader = OTPEmailReader("test@test.com", "wrong", "imap.test.com")
            assert reader.connect() is False

    def test_disconnect_closes_and_logs_out(self):
        """disconnect() calls close() and logout()."""
        mock_imap = _make_imap_mock()
        with patch(f"{OTP_MODULE}.imaplib.IMAP4_SSL", return_value=mock_imap):
            from utils.otp_email_reader import OTPEmailReader

            reader = OTPEmailReader("test@test.com", "password", "imap.test.com")
            reader.connect()
            reader.disconnect()
            mock_imap.close.assert_called_once()
            mock_imap.logout.assert_called_once()


@pytest.mark.unit
class TestOTPExtraction:
    """Tests for OTP code extraction from email content."""

    def test_otp_from_subject_bracket(self):
        """OTP[123456] in subject is extracted."""
        from utils.otp_email_reader import OTPEmailReader

        reader = OTPEmailReader("t@t.com", "p", "imap.t.com")
        msg = _build_email_message(subject="SECUDIUM OTP[987654]")
        result = reader._extract_otp_from_message(msg)
        assert result == "987654"

    def test_otp_from_subject_colon(self):
        """OTP: 123456 in subject is extracted."""
        from utils.otp_email_reader import OTPEmailReader

        reader = OTPEmailReader("t@t.com", "p", "imap.t.com")
        msg = _build_email_message(subject="OTP: 456789")
        result = reader._extract_otp_from_message(msg)
        assert result == "456789"

    def test_otp_from_body_korean(self):
        """인증번호: XXXXXX in body is extracted."""
        from utils.otp_email_reader import OTPEmailReader

        reader = OTPEmailReader("t@t.com", "p", "imap.t.com")
        msg = _build_email_message(subject="Auth Code", body="인증번호: 112233 입니다.")
        result = reader._extract_otp_from_message(msg)
        assert result == "112233"

    def test_otp_from_body_confirmation_code(self):
        """확인번호: XXXXXX in body is extracted."""
        from utils.otp_email_reader import OTPEmailReader

        reader = OTPEmailReader("t@t.com", "p", "imap.t.com")
        msg = _build_email_message(subject="Verify", body="확인번호: 998877")
        result = reader._extract_otp_from_message(msg)
        assert result == "998877"

    def test_no_otp_returns_none(self):
        """Email without OTP pattern returns None."""
        from utils.otp_email_reader import OTPEmailReader

        reader = OTPEmailReader("t@t.com", "p", "imap.t.com")
        msg = _build_email_message(subject="Hello", body="No code here")
        result = reader._extract_otp_from_message(msg)
        assert result is None


@pytest.mark.unit
class TestGetLatestOTP:
    """Tests for the polling OTP retrieval flow."""

    def test_otp_found_in_new_email(self):
        """New email with OTP is detected and code returned."""
        otp_email = _build_email_message(
            subject="SECUDIUM OTP[123456]",
            from_addr="noreply@secudium.com",
        )

        search_call_count = 0

        def search_side_effect(*args, **kwargs):
            nonlocal search_call_count
            search_call_count += 1
            if search_call_count <= 1:
                return ("OK", [b"1"])
            return ("OK", [b"1 2"])

        mock_imap = _make_imap_mock()
        mock_imap.search.side_effect = search_side_effect
        mock_imap.fetch.return_value = ("OK", [(b"2", otp_email.as_bytes())])

        with patch(f"{OTP_MODULE}.imaplib.IMAP4_SSL", return_value=mock_imap):
            with patch(f"{OTP_MODULE}.time.sleep"):
                from utils.otp_email_reader import OTPEmailReader

                reader = OTPEmailReader("t@t.com", "p", "imap.t.com")
                code = reader.get_latest_otp(max_wait_seconds=10)
                assert code == "123456"

    def test_timeout_returns_none(self):
        """No new email within timeout returns None."""
        mock_imap = _make_imap_mock(search_ids=[1])

        with patch(f"{OTP_MODULE}.imaplib.IMAP4_SSL", return_value=mock_imap):
            with patch(f"{OTP_MODULE}.time.sleep"):
                with patch(f"{OTP_MODULE}.time.time") as mock_time:
                    mock_time.side_effect = [0, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65]
                    from utils.otp_email_reader import OTPEmailReader

                    reader = OTPEmailReader("t@t.com", "p", "imap.t.com")
                    code = reader.get_latest_otp(max_wait_seconds=5)
                    assert code is None
