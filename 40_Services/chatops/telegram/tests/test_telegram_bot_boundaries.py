"""Offline Telegram bot boundary tests.

These tests use only stdlib unittest/mocking. They never read .env, never call
Telegram, and never require a live Action API.
"""

import inspect
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import telegram_capture_bot as bot


AUTHORIZED_SENDER = 12345
UNAUTHORIZED_SENDER = 99999
CHAT_ID = 11111

STALE_HELPERS = [
    'parse_frontmatter',
    'find_pending_capture',
    'get_first_line_content',
    'load_pending_capture_summary',
    'list_pending_review_files',
    'format_pending_queue',
    'resolve_pending_index',
    'list_pending_captures',
    'update_capture_frontmatter',
    'move_capture_file',
]


def make_update(text, sender_id=AUTHORIZED_SENDER, chat_id=CHAT_ID):
    return {
        'update_id': 1,
        'message': {
            'message_id': 1,
            'from': {'id': sender_id, 'first_name': 'TestUser'},
            'chat': {'id': chat_id},
            'text': text,
        },
    }


class TelegramBoundaryTests(unittest.TestCase):
    def test_stale_helper_names_are_absent(self):
        for name in STALE_HELPERS:
            with self.subTest(helper=name):
                self.assertFalse(hasattr(bot, name), name)

    @patch.object(bot, 'tg_api')
    def test_capture_test_blocks_non_capture_without_dispatch(self, mock_tg):
        update = make_update('/view 1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_view') as mock_view:
                with patch.object(bot, 'process_update') as mock_process:
                    bot.process_capture_test_update(update)

        mock_tg.assert_called_once_with('sendMessage', {
            'chat_id': CHAT_ID,
            'text': 'LifeOS capture-test mode is active. No action was taken.',
        })
        mock_view.assert_not_called()
        mock_process.assert_not_called()

    @patch.object(bot, 'tg_api')
    def test_review_test_blocks_non_review_without_dispatch(self, mock_tg):
        update = make_update('/capture something')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_capture') as mock_capture:
                with patch.object(bot, 'process_update') as mock_process:
                    bot.process_review_test_update(update)

        mock_tg.assert_called_once_with('sendMessage', {
            'chat_id': CHAT_ID,
            'text': 'LifeOS review-test mode is active. No action was taken.',
        })
        mock_capture.assert_not_called()
        mock_process.assert_not_called()

    @patch.object(bot, 'tg_api')
    def test_receive_test_never_dispatches_normal_commands(self, mock_tg):
        update = make_update('/capture something')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_capture') as mock_capture:
                with patch.object(bot, 'process_update') as mock_process:
                    bot.process_receive_test_update(update)

        mock_tg.assert_called_once_with('sendMessage', {
            'chat_id': CHAT_ID,
            'text': 'LifeOS receive test OK. No action was taken.',
        })
        mock_capture.assert_not_called()
        mock_process.assert_not_called()

    def test_unauthorized_sender_rejected_before_action(self):
        update = make_update('/capture test', sender_id=UNAUTHORIZED_SENDER)
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'reject_unauthorized') as mock_reject:
                with patch.object(bot, 'handle_capture') as mock_capture:
                    bot.process_update(update)

        mock_reject.assert_called_once_with(CHAT_ID)
        mock_capture.assert_not_called()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_capture_handler_uses_action_api(self, mock_api, mock_tg):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_test'}

        bot.handle_capture('/capture test content', CHAT_ID, AUTHORIZED_SENDER, {})

        mock_api.assert_called_once_with('/captures', {'text': 'test content'})
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('CAPTURE', text)
        self.assertIn('cap_test', text)
        self.assertIn('no vault processing', text.lower())
        for name in STALE_HELPERS:
            self.assertFalse(hasattr(bot, name), name)

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_review_handlers_use_action_api(self, mock_api, mock_tg):
        mock_api.return_value = {'success': True, 'pending': [], 'count': 0}
        bot.handle_p(CHAT_ID)
        mock_api.assert_called_with('/captures/pending')

        mock_api.reset_mock()
        mock_api.return_value = {'success': True, 'capture': {'capture_id': 'cap_1', 'content': ''}}
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            bot.handle_view('/view 1', CHAT_ID)
        mock_api.assert_called_with('/captures/pending/1')

        mock_api.reset_mock()
        mock_api.return_value = {'success': True, 'capture_id': 'cap_1'}
        bot.handle_approve('/approve cap_1', CHAT_ID)
        mock_api.assert_called_with('/captures/cap_1/approve', {})

        mock_api.reset_mock()
        mock_api.return_value = {'success': True, 'capture_id': 'cap_1'}
        bot.handle_reject('/reject cap_1', CHAT_ID)
        mock_api.assert_called_with('/captures/cap_1/reject', {})

        mock_api.reset_mock()
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_1'}},
            {'success': True, 'capture_id': 'cap_1'},
        ]
        bot.handle_a('/a 1', CHAT_ID)
        self.assertEqual(mock_api.call_args_list[0].args, ('/captures/pending/1',))
        self.assertEqual(mock_api.call_args_list[1].args, ('/captures/cap_1/approve', {}))

        mock_api.reset_mock()
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_1'}},
            {'success': True, 'capture_id': 'cap_1'},
        ]
        bot.handle_r('/r 1', CHAT_ID)
        self.assertEqual(mock_api.call_args_list[0].args, ('/captures/pending/1',))
        self.assertEqual(mock_api.call_args_list[1].args, ('/captures/cap_1/reject', {}))

        for name in STALE_HELPERS:
            self.assertFalse(hasattr(bot, name), name)

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_review_handlers_do_not_call_filesystem_mutation_apis(self, mock_api, mock_tg):
        with patch('builtins.open') as mock_open:
            with patch.object(bot.os, 'rename') as mock_rename:
                mock_api.return_value = {'success': True, 'pending': [], 'count': 0}
                bot.handle_p(CHAT_ID)

                mock_api.return_value = {'success': True, 'capture': {'capture_id': 'cap_1', 'content': ''}}
                with patch.object(bot, 'BOT_TOKEN', "test_token"):
                    bot.handle_view('/view 1', CHAT_ID)

                mock_api.return_value = {'success': True, 'capture_id': 'cap_1'}
                bot.handle_approve('/approve cap_1', CHAT_ID)
                bot.handle_reject('/reject cap_1', CHAT_ID)

                mock_api.side_effect = [
                    {'success': True, 'capture': {'capture_id': 'cap_1'}},
                    {'success': True, 'capture_id': 'cap_1'},
                    {'success': True, 'capture': {'capture_id': 'cap_1'}},
                    {'success': True, 'capture_id': 'cap_1'},
                ]
                bot.handle_a('/a 1', CHAT_ID)
                bot.handle_r('/r 1', CHAT_ID)

                mock_open.assert_not_called()
                mock_rename.assert_not_called()

    def test_active_review_handlers_do_not_contain_direct_file_mutation(self):
        forbidden = [
            'os.rename',
            'shutil.move',
            '.update_capture_frontmatter',
            'move_capture_file',
            'open(PENDING_DIR',
            'open(APPROVED_DIR',
            'open(REJECTED_DIR',
        ]
        handlers = [
            bot.handle_list_pending,
            bot.handle_approve,
            bot.handle_reject,
            bot.handle_p,
            bot.handle_view,
            bot.handle_a,
            bot.handle_r,
        ]
        for handler in handlers:
            source = inspect.getsource(handler)
            for token in forbidden:
                with self.subTest(handler=handler.__name__, token=token):
                    self.assertNotIn(token, source)



class TestCallbackBoundaries(unittest.TestCase):
    def make_callback_update(self, callback_data, sender_id=AUTHORIZED_SENDER):
        return {
            "update_id": 2,
            "callback_query": {
                "id": "cb_test_1",
                "from": {"id": sender_id, "first_name": "TestUser"},
                "message": {
                    "message_id": 100,
                    "chat": {"id": CHAT_ID},
                },
                "data": callback_data,
            }
        }

    def test_callback_handler_does_not_contain_filesystem_ops(self):
        source = inspect.getsource(bot.process_callback_query)
        forbidden = [
            "open(", "os.rename", "shutil.move", "CAPTURE_DIR",
            "PENDING_DIR", "APPROVED_DIR", "REJECTED_DIR",
        ]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    @patch.object(bot, 'tg_api')
    def test_cancel_handler_uses_editMessageReplyMarkup(self, mock_tg):
        bot._handle_cancel(CHAT_ID, 100)
        mock_tg.assert_called_once_with("editMessageReplyMarkup", {
            "chat_id": CHAT_ID,
            "message_id": 100,
            "reply_markup": {"inline_keyboard": []},
        })


class TestCompactAliases(unittest.TestCase):
    """Compact mobile aliases: /r1 == /r 1, /a1 == /a 1, /view1 == /view 1."""

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_r1_dispatches_to_handle_r(self, mock_api, mock_tg):
        update = make_update('/r1')
        bot.ALLOW_REVIEW_COMMANDS = True
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_r') as mock_r:
                bot.process_update(update)
                mock_r.assert_called_once()
                text_arg = mock_r.call_args[0][0]
                self.assertEqual(text_arg, '/r 1')

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_a1_dispatches_to_handle_a(self, mock_api, mock_tg):
        update = make_update('/a1')
        bot.ALLOW_REVIEW_COMMANDS = True
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_a') as mock_a:
                bot.process_update(update)
                mock_a.assert_called_once()
                text_arg = mock_a.call_args[0][0]
                self.assertEqual(text_arg, '/a 1')

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_view1_dispatches_to_handle_view(self, mock_api, mock_tg):
        update = make_update('/view1')
        bot.ALLOW_REVIEW_COMMANDS = True
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_view') as mock_v:
                bot.process_update(update)
                mock_v.assert_called_once()
                text_arg = mock_v.call_args[0][0]
                self.assertEqual(text_arg, '/view 1')

    @patch.object(bot, 'tg_api')
    def test_r1_review_test_dispatches_to_handle_r(self, mock_tg):
        update = make_update('/r1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_r') as mock_r:
                bot.process_review_test_update(update)
                mock_r.assert_called_once()
                text_arg = mock_r.call_args[0][0]
                self.assertEqual(text_arg, '/r 1')

    @patch.object(bot, 'tg_api')
    def test_a1_review_test_dispatches_to_handle_a(self, mock_tg):
        update = make_update('/a1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_a') as mock_a:
                bot.process_review_test_update(update)
                mock_a.assert_called_once()
                text_arg = mock_a.call_args[0][0]
                self.assertEqual(text_arg, '/a 1')

    @patch.object(bot, 'tg_api')
    def test_view1_review_test_dispatches_to_handle_view(self, mock_tg):
        update = make_update('/view1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_view') as mock_v:
                bot.process_review_test_update(update)
                mock_v.assert_called_once()
                text_arg = mock_v.call_args[0][0]
                self.assertEqual(text_arg, '/view 1')

    @patch.object(bot, 'tg_api')
    def test_r1_still_blocked_when_review_disabled(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        update = make_update('/r1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_r') as mock_r:
                bot.process_update(update)
                mock_r.assert_not_called()


class TestCaptureFirstMode(unittest.TestCase):
    """Capture-first mode: read-only allowed, mutations blocked."""

    @patch.object(bot, 'tg_api')
    def test_p_allowed_in_capture_first(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        with patch.object(bot, 'handle_p') as mock_p:
            update = make_update('/p')
            with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
                bot.process_update(update)
            mock_p.assert_called_once()

    @patch.object(bot, 'tg_api')
    def test_view_allowed_in_capture_first(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        with patch.object(bot, 'handle_view') as mock_v:
            update = make_update('/view 1')
            with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
                bot.process_update(update)
            mock_v.assert_called_once()

    @patch.object(bot, 'tg_api')
    def test_view1_allowed_in_capture_first(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        with patch.object(bot, 'handle_view') as mock_v:
            update = make_update('/view1')
            with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
                bot.process_update(update)
            mock_v.assert_called_once()

    @patch.object(bot, 'tg_api')
    def test_a_blocked_in_capture_first(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        update = make_update('/a 1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_a') as mock_a:
                bot.process_update(update)
                mock_a.assert_not_called()
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NO ACTION', text)

    @patch.object(bot, 'tg_api')
    def test_a1_blocked_in_capture_first(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        update = make_update('/a1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_a') as mock_a:
                bot.process_update(update)
                mock_a.assert_not_called()
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NO ACTION', text)

    @patch.object(bot, 'tg_api')
    def test_r_blocked_in_capture_first(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        update = make_update('/r 1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_r') as mock_r:
                bot.process_update(update)
                mock_r.assert_not_called()
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NO ACTION', text)

    @patch.object(bot, 'tg_api')
    def test_r1_blocked_in_capture_first(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        update = make_update('/r1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_r') as mock_r:
                bot.process_update(update)
                mock_r.assert_not_called()
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NO ACTION', text)

    @patch.object(bot, 'tg_api')
    def test_blocked_mutation_does_not_call_action_api(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        update = make_update('/a 1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'call_action_api') as mock_api:
                bot.process_update(update)
                mock_api.assert_not_called()

    @patch.object(bot, 'tg_api')
    def test_blocked_reject_does_not_call_action_api(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        update = make_update('/r 1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'call_action_api') as mock_api:
                bot.process_update(update)
                mock_api.assert_not_called()

    @patch.object(bot, 'handle_p')
    @patch.object(bot, 'tg_api')
    def test_p_in_capture_first_passes_mode(self, mock_tg, mock_handle_p):
        bot.ALLOW_REVIEW_COMMANDS = False
        update = make_update('/p')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            bot.process_update(update)
        mock_handle_p.assert_called_once_with(CHAT_ID)


class TestFullReviewMode(unittest.TestCase):
    """Full review mode: all commands allowed, index resolution still works."""

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_a_still_dispatches_in_review_mode(self, mock_api, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = True
        with patch.object(bot, 'handle_a') as mock_a:
            update = make_update('/a 1')
            with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
                bot.process_update(update)
            mock_a.assert_called_once()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_r_still_dispatches_in_review_mode(self, mock_api, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = True
        with patch.object(bot, 'handle_r') as mock_r:
            update = make_update('/r 1')
            with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
                bot.process_update(update)
            mock_r.assert_called_once()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_numeric_index_still_resolves_in_review_mode(self, mock_api, mock_tg):
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_123'}},
            {'success': True, 'capture_id': 'cap_123'},
        ]
        bot.handle_a('/a 1', CHAT_ID)
        self.assertEqual(mock_api.call_args_list[0].args, ('/captures/pending/1',))
        self.assertEqual(mock_api.call_args_list[1].args, ('/captures/cap_123/approve', {}))


class TestNeedsIndexResponses(unittest.TestCase):
    """/view, /a, /r without index should return NEEDS INDEX card."""

    @patch.object(bot, 'tg_api')
    def test_view_without_index_returns_needs_index(self, mock_tg):
        bot.handle_view('/view', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NEEDS INDEX', text.upper())
        self.assertIn('No action was taken', text)

    @patch.object(bot, 'tg_api')
    def test_a_without_index_returns_needs_index(self, mock_tg):
        bot.handle_a('/a', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NEEDS INDEX', text.upper())
        self.assertIn('No action was taken', text)

    @patch.object(bot, 'tg_api')
    def test_r_without_index_returns_needs_index(self, mock_tg):
        bot.handle_r('/r', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NEEDS INDEX', text.upper())
        self.assertIn('No action was taken', text)

    @patch.object(bot, 'tg_api')
    def test_view_with_whitespace_only_returns_needs_index(self, mock_tg):
        bot.handle_view('/view   ', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NEEDS INDEX', text.upper())

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_a_with_index_still_works(self, mock_api, mock_tg):
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_123'}},
            {'success': True, 'capture_id': 'cap_123'},
        ]
        bot.handle_a('/a 1', CHAT_ID)
        self.assertEqual(mock_api.call_count, 2)
        self.assertEqual(mock_api.call_args_list[0].args, ('/captures/pending/1',))
        self.assertEqual(mock_api.call_args_list[1].args, ('/captures/cap_123/approve', {}))

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_r_with_index_still_works(self, mock_api, mock_tg):
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_123'}},
            {'success': True, 'capture_id': 'cap_123'},
        ]
        bot.handle_r('/r 1', CHAT_ID)
        self.assertEqual(mock_api.call_count, 2)
        self.assertEqual(mock_api.call_args_list[0].args, ('/captures/pending/1',))
        self.assertEqual(mock_api.call_args_list[1].args, ('/captures/cap_123/reject', {}))


class TestErrorMessagesUseCards(unittest.TestCase):
    """Error messages in approve/reject handlers use Operator Cards."""

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_handle_approve_error_uses_card(self, mock_tg, mock_api):
        mock_api.return_value = {'success': False, 'error': 'not_found'}
        bot.handle_approve('/approve cap_xxx', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NO ACTION', text)
        self.assertIn('not found', text.lower())

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_handle_reject_error_uses_card(self, mock_tg, mock_api):
        mock_api.return_value = {'success': False, 'error': 'capture_not_found'}
        bot.handle_reject('/reject cap_xxx', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NO ACTION', text)
        self.assertIn('capture not found', text.lower())

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_handle_r_error_uses_card(self, mock_tg, mock_api):
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_1'}},
            {'success': False, 'error': 'not_found'},
        ]
        bot.handle_r('/r 1', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NO ACTION', text)
        self.assertIn('not found', text.lower())

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_handle_a_error_uses_card(self, mock_tg, mock_api):
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_1'}},
            {'success': False, 'error': 'mutation_failed'},
        ]
        bot.handle_a('/a 1', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('NO ACTION', text)
        self.assertIn('mutation failed', text.lower())


if __name__ == '__main__':
    unittest.main()
