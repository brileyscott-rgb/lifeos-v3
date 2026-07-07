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


if __name__ == '__main__':
    unittest.main()
