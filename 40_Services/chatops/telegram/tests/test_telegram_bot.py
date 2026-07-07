"""Offline tests for Telegram Capture Bot — never connects to live Telegram or APIs."""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import telegram_capture_bot as bot


AUTHORIZED_SENDER = 12345
UNAUTHORIZED_SENDER = 99999
CHAT_ID = 11111


def make_update(text, sender_id=AUTHORIZED_SENDER, chat_id=CHAT_ID):
    return {
        'update_id': 1,
        'message': {
            'message_id': 1,
            'from': {'id': sender_id, 'first_name': 'TestUser'},
            'chat': {'id': chat_id},
            'text': text,
        }
    }


class TestExtractAndAuth(unittest.TestCase):
    def test_extract_sender_id_valid(self):
        update = make_update('/help')
        sid, cid = bot.extract_sender_id(update)
        self.assertEqual(sid, AUTHORIZED_SENDER)
        self.assertEqual(cid, CHAT_ID)

    def test_extract_sender_id_no_message(self):
        sid, cid = bot.extract_sender_id({'update_id': 1})
        self.assertIsNone(sid)
        self.assertIsNone(cid)

    def test_is_authorized_sender_match(self):
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            self.assertTrue(bot.is_authorized_sender(AUTHORIZED_SENDER))

    def test_is_authorized_sender_mismatch(self):
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            self.assertFalse(bot.is_authorized_sender(UNAUTHORIZED_SENDER))

    def test_is_authorized_sender_none(self):
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            self.assertFalse(bot.is_authorized_sender(None))

    def test_reject_unauthorized_calls_tg_api(self):
        with patch.object(bot, 'tg_api') as mock_tg:
            with patch.object(bot, 'append_event'):
                bot.reject_unauthorized(CHAT_ID)
                mock_tg.assert_called_once_with('sendMessage', {
                    'chat_id': CHAT_ID,
                    'text': 'Unauthorized'
                })

    def test_reject_unauthorized_appends_event(self):
        with patch.object(bot, 'tg_api'):
            with patch.object(bot, 'append_event') as mock_evt:
                bot.reject_unauthorized(CHAT_ID)
                mock_evt.assert_called_once()
                args = mock_evt.call_args[0]
                self.assertEqual(args[0], 'chatops.telegram.unauthorized_sender_rejected')


class TestUnauthorizedSenderRejectedBeforeAction(unittest.TestCase):
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_process_update_rejects_unauthorized(self, mock_evt, mock_tg):
        update = make_update('/capture some text', sender_id=UNAUTHORIZED_SENDER)
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_capture') as mock_handle:
                bot.process_update(update)
                mock_handle.assert_not_called()
                mock_tg.assert_called_once_with('sendMessage', {
                    'chat_id': CHAT_ID,
                    'text': 'Unauthorized'
                })

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_process_capture_test_rejects_unauthorized(self, mock_evt, mock_tg):
        update = make_update('/capture test', sender_id=UNAUTHORIZED_SENDER)
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_capture') as mock_handle:
                bot.process_capture_test_update(update)
                mock_handle.assert_not_called()
                mock_tg.assert_called_once_with('sendMessage', {
                    'chat_id': CHAT_ID,
                    'text': 'Unauthorized'
                })

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_process_review_test_rejects_unauthorized(self, mock_evt, mock_tg):
        update = make_update('/p', sender_id=UNAUTHORIZED_SENDER)
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_p') as mock_p:
                bot.process_review_test_update(update)
                mock_p.assert_not_called()
                mock_tg.assert_called_once_with('sendMessage', {
                    'chat_id': CHAT_ID,
                    'text': 'Unauthorized'
                })

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_process_receive_test_rejects_unauthorized(self, mock_evt, mock_tg):
        update = make_update('/help', sender_id=UNAUTHORIZED_SENDER)
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            bot.process_receive_test_update(update)
            mock_tg.assert_called_once_with('sendMessage', {
                'chat_id': CHAT_ID,
                'text': 'Unauthorized'
            })


class TestReceiveTestSafeMode(unittest.TestCase):
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_receive_test_never_dispatches_commands(self, mock_evt, mock_tg):
        update = make_update('/capture dangerous')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'process_update') as mock_proc:
                bot.process_receive_test_update(update)
                mock_proc.assert_not_called()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_receive_test_sends_safe_ack(self, mock_evt, mock_tg):
        update = make_update('/capture dangerous')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            bot.process_receive_test_update(update)
            mock_tg.assert_called_once_with('sendMessage', {
                'chat_id': CHAT_ID,
                'text': 'LifeOS receive test OK. No action was taken.'
            })

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_receive_test_no_chat_id_skips(self, mock_evt, mock_tg):
        update = {'update_id': 2, 'message': {}}
        bot.process_receive_test_update(update)
        mock_tg.assert_not_called()


class TestCaptureTestBlocksNonCapture(unittest.TestCase):
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_capture_test_blocks_status(self, mock_evt, mock_tg):
        update = make_update('/status')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_capture') as mock_cap:
                bot.process_capture_test_update(update)
                mock_cap.assert_not_called()
                mock_tg.assert_called_once_with('sendMessage', {
                    'chat_id': CHAT_ID,
                    'text': 'LifeOS capture-test mode is active. No action was taken.'
                })

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_capture_test_blocks_help(self, mock_evt, mock_tg):
        update = make_update('/help')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_capture') as mock_cap:
                bot.process_capture_test_update(update)
                mock_cap.assert_not_called()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_capture_test_blocks_review_commands(self, mock_evt, mock_tg):
        for cmd in ['/p', '/view 1', '/a 1', '/r 1', '/list_pending', '/approve cap_xxx']:
            update = make_update(cmd)
            with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
                with patch.object(bot, 'handle_capture') as mock_cap:
                    with self.subTest(cmd=cmd):
                        bot.process_capture_test_update(update)
                        mock_cap.assert_not_called()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_capture_test_allows_capture(self, mock_evt, mock_tg):
        update = make_update('/capture test message')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_capture') as mock_cap:
                bot.process_capture_test_update(update)
                mock_cap.assert_called_once()


class TestReviewTestBlocksNonReview(unittest.TestCase):
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_blocks_capture(self, mock_evt, mock_tg):
        update = make_update('/capture test')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_p') as mock_p:
                bot.process_review_test_update(update)
                mock_p.assert_not_called()
                mock_tg.assert_called_once_with('sendMessage', {
                    'chat_id': CHAT_ID,
                    'text': 'LifeOS review-test mode is active. No action was taken.'
                })

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_blocks_status(self, mock_evt, mock_tg):
        update = make_update('/status')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_p') as mock_p:
                bot.process_review_test_update(update)
                mock_p.assert_not_called()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_blocks_help(self, mock_evt, mock_tg):
        update = make_update('/help')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_p') as mock_p:
                bot.process_review_test_update(update)
                mock_p.assert_not_called()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_blocks_unknown(self, mock_evt, mock_tg):
        update = make_update('/unknown_cmd')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_p') as mock_p:
                bot.process_review_test_update(update)
                mock_p.assert_not_called()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_allows_p(self, mock_evt, mock_tg):
        update = make_update('/p')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_p') as mock_p:
                bot.process_review_test_update(update)
                mock_p.assert_called_once()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_allows_list_pending(self, mock_evt, mock_tg):
        update = make_update('/list_pending')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_list_pending') as mock_lp:
                bot.process_review_test_update(update)
                mock_lp.assert_called_once()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_allows_view(self, mock_evt, mock_tg):
        update = make_update('/view 1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_view') as mock_v:
                bot.process_review_test_update(update)
                mock_v.assert_called_once()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_allows_a(self, mock_evt, mock_tg):
        update = make_update('/a 1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_a') as mock_a:
                bot.process_review_test_update(update)
                mock_a.assert_called_once()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_allows_r(self, mock_evt, mock_tg):
        update = make_update('/r 1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_r') as mock_r:
                bot.process_review_test_update(update)
                mock_r.assert_called_once()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_allows_approve(self, mock_evt, mock_tg):
        update = make_update('/approve cap_xxx')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_approve') as mock_ap:
                bot.process_review_test_update(update)
                mock_ap.assert_called_once()

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_allows_reject(self, mock_evt, mock_tg):
        update = make_update('/reject cap_xxx')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_reject') as mock_rej:
                bot.process_review_test_update(update)
                mock_rej.assert_called_once()


class TestActiveHandlersCallActionAPI(unittest.TestCase):
    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_handle_capture_calls_action_api(self, mock_evt, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_test'}
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            bot.handle_capture('/capture hello', CHAT_ID, AUTHORIZED_SENDER, {})
            mock_api.assert_called_once_with('/captures', {'text': 'hello'})

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_handle_list_pending_calls_action_api(self, mock_evt, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'pending': [], 'count': 0}
        bot.handle_list_pending(CHAT_ID)
        mock_api.assert_called_once_with('/captures/pending')

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_handle_approve_calls_action_api(self, mock_evt, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_test'}
        bot.handle_approve('/approve cap_test', CHAT_ID)
        mock_api.assert_called_once_with('/captures/cap_test/approve', {})

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_handle_reject_calls_action_api(self, mock_evt, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_test'}
        bot.handle_reject('/reject cap_test', CHAT_ID)
        mock_api.assert_called_once_with('/captures/cap_test/reject', {})

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_handle_p_calls_action_api(self, mock_evt, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'pending': [], 'count': 0}
        bot.handle_p(CHAT_ID)
        mock_api.assert_called_once_with('/captures/pending')

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_handle_view_calls_action_api(self, mock_evt, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture': {'capture_id': 'cap_1'}}
        bot.handle_view('/view 1', CHAT_ID)
        self.assertEqual(mock_api.call_args[0][0], '/captures/pending/1')


class TestActiveHandlersDoNotTouchFilesystem(unittest.TestCase):
    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_handle_capture_no_filesystem_write(self, mock_evt, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_test'}
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch('builtins.open', create=True) as mock_open:
                bot.handle_capture('/capture hello', CHAT_ID, AUTHORIZED_SENDER, {})
                for call_args in mock_open.call_args_list:
                    self.assertNotIn('30_Capture', str(call_args))
                    self.assertNotIn('pending_review', str(call_args))
                    self.assertNotIn('events.jsonl', str(call_args))

    def test_no_review_handler_calls_stale_helpers(self):
        handlers = [
            bot.handle_list_pending,
            bot.handle_approve,
            bot.handle_reject,
            bot.handle_p,
            bot.handle_view,
            bot.handle_a,
            bot.handle_r,
        ]
        for h in handlers:
            with self.subTest(handler=h.__name__):
                source = getattr(h, '__code__', None)
                if source is None:
                    continue
                names = source.co_names
                for stale in ['move_capture_file', 'update_capture_frontmatter',
                              'find_pending_capture', 'list_pending_review_files',
                              'resolve_pending_index', 'parse_frontmatter',
                              'format_pending_queue', 'load_pending_capture_summary',
                              'list_pending_captures', 'get_first_line_content']:
                    self.assertNotIn(stale, names,
                                     f"{h.__name__} references stale helper {stale}")


class TestNoDirectEventLogAppendByReviewHandlers(unittest.TestCase):
    def test_review_handlers_do_not_call_append_event_directly(self):
        handlers = [
            bot.handle_list_pending,
            bot.handle_approve,
            bot.handle_reject,
            bot.handle_p,
            bot.handle_view,
            bot.handle_a,
            bot.handle_r,
        ]
        for h in handlers:
            with self.subTest(handler=h.__name__):
                source = getattr(h, '__code__', None)
                if source is None:
                    continue
                names = source.co_names
                self.assertNotIn('append_event', names,
                                 f"{h.__name__} calls append_event directly")


class TestActionAPIFallback(unittest.TestCase):
    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_action_api_unavailable_reply(self, mock_tg, mock_api):
        bot.action_api_unavailable_reply(CHAT_ID)
        mock_tg.assert_called_once_with('sendMessage', {
            'chat_id': CHAT_ID,
            'text': 'LifeOS review unavailable. No action was taken.'
        })


class TestStaleHelpersRemoved(unittest.TestCase):
    def test_stale_helpers_do_not_exist(self):
        stale_names = [
            'parse_frontmatter', 'find_pending_capture', 'get_first_line_content',
            'load_pending_capture_summary', 'list_pending_review_files',
            'format_pending_queue', 'resolve_pending_index', 'list_pending_captures',
            'update_capture_frontmatter', 'move_capture_file',
        ]
        for name in stale_names:
            with self.subTest(helper=name):
                self.assertFalse(hasattr(bot, name),
                                 f"Stale helper {name} still exists in module")


if __name__ == '__main__':
    unittest.main()
