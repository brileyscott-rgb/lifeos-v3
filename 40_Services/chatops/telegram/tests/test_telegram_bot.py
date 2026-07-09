"""Offline tests for Telegram Capture Bot — never connects to live Telegram or APIs."""

import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
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
                mock_tg.assert_called_once()
                args = mock_tg.call_args[0]
                self.assertEqual(args[0], 'sendMessage')
                text = args[1]['text']
                self.assertIn('Access denied', text)
                self.assertIn('not authorized', text.lower())

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
                mock_tg.assert_called_once()
                args = mock_tg.call_args[0]
                self.assertEqual(args[0], 'sendMessage')
                text = args[1]['text']
                self.assertIn('Access denied', text)
                self.assertIn('not authorized', text.lower())

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_process_capture_test_rejects_unauthorized(self, mock_evt, mock_tg):
        update = make_update('/capture test', sender_id=UNAUTHORIZED_SENDER)
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_capture') as mock_handle:
                bot.process_capture_test_update(update)
                mock_handle.assert_not_called()
                mock_tg.assert_called_once()
                args = mock_tg.call_args[0]
                self.assertEqual(args[0], 'sendMessage')
                text = args[1]['text']
                self.assertIn('Access denied', text)
                self.assertIn('not authorized', text.lower())

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_process_review_test_rejects_unauthorized(self, mock_evt, mock_tg):
        update = make_update('/p', sender_id=UNAUTHORIZED_SENDER)
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_p') as mock_p:
                bot.process_review_test_update(update)
                mock_p.assert_not_called()
                mock_tg.assert_called_once()
                args = mock_tg.call_args[0]
                self.assertEqual(args[0], 'sendMessage')
                text = args[1]['text']
                self.assertIn('Access denied', text)
                self.assertIn('not authorized', text.lower())

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_process_receive_test_rejects_unauthorized(self, mock_evt, mock_tg):
        update = make_update('/help', sender_id=UNAUTHORIZED_SENDER)
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            bot.process_receive_test_update(update)
            mock_tg.assert_called_once()
            args = mock_tg.call_args[0]
            self.assertEqual(args[0], 'sendMessage')
            text = args[1]['text']
            self.assertIn('Access denied', text)
            self.assertIn('not authorized', text.lower())


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
    def test_review_test_allows_view_compact(self, mock_evt, mock_tg):
        update = make_update('/view1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_view') as mock_v:
                bot.process_review_test_update(update)
                mock_v.assert_called_once()
                text_arg = mock_v.call_args[0][0]
                self.assertEqual(text_arg, '/view 1')

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_allows_a_compact(self, mock_evt, mock_tg):
        update = make_update('/a1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_a') as mock_a:
                bot.process_review_test_update(update)
                mock_a.assert_called_once()
                text_arg = mock_a.call_args[0][0]
                self.assertEqual(text_arg, '/a 1')

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'append_event')
    def test_review_test_allows_r_compact(self, mock_evt, mock_tg):
        update = make_update('/r1')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_r') as mock_r:
                bot.process_review_test_update(update)
                mock_r.assert_called_once()
                text_arg = mock_r.call_args[0][0]
                self.assertEqual(text_arg, '/r 1')

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
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
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
                              'load_pending_capture_summary',
                              'list_pending_captures', 'get_first_line_content']:
                    self.assertNotIn(stale, names,
                                     f"{h.__name__} references stale helper {stale}")


class TestNoDirectEventLogAppendByActiveHandlers(unittest.TestCase):
    def test_active_handlers_do_not_call_append_event_directly(self):
        handlers = [
            bot.handle_capture,
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


class TestTelemetryBoundaryCheck(unittest.TestCase):
    def test_append_event_raises_on_mutation_event(self):
        forbidden_event = 'chatops.telegram.capture_received'
        with self.assertRaises(ValueError) as ctx:
            bot.append_event(forbidden_event, {})
        self.assertIn("Direct logging of non-operational event", str(ctx.exception))



class TestActionAPIFallback(unittest.TestCase):
    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_action_api_unavailable_reply(self, mock_tg, mock_api):
        bot.action_api_unavailable_reply(CHAT_ID)
        mock_tg.assert_called_once()
        args = mock_tg.call_args[0]
        self.assertEqual(args[0], 'sendMessage')
        text = args[1]['text']
        self.assertIn('Action API', text)
        self.assertIn('UNAVAILABLE', text)


class TestTelegramEventIdReceipts(unittest.TestCase):
    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_capture_success_reply_includes_event_id(self, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_123', 'event_id': 'evt_capture_123'}
        bot.handle_capture('/capture hello', CHAT_ID, AUTHORIZED_SENDER, {})
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Capture', text)
        self.assertIn('cap_123', text)
        self.assertIn('evt_capture_123', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_capture_success_reply_without_event_id(self, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_123'}
        bot.handle_capture('/capture hello', CHAT_ID, AUTHORIZED_SENDER, {})
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Capture', text)
        self.assertIn('cap_123', text)
        self.assertNotIn('event_id', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_approve_success_reply_includes_event_id(self, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_123', 'event_id': 'evt_approve_123'}
        bot.handle_approve('/approve cap_123', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Approved', text)
        self.assertIn('cap_123', text)
        self.assertIn('evt_approve_123', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_approve_success_reply_without_event_id(self, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_123'}
        bot.handle_approve('/approve cap_123', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Approved', text)
        self.assertIn('cap_123', text)
        self.assertNotIn('event_id', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_reject_success_reply_includes_event_id(self, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_123', 'event_id': 'evt_reject_123'}
        bot.handle_reject('/reject cap_123', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Rejected', text)
        self.assertIn('cap_123', text)
        self.assertIn('evt_reject_123', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_reject_success_reply_without_event_id(self, mock_tg, mock_api):
        mock_api.return_value = {'success': True, 'capture_id': 'cap_123'}
        bot.handle_reject('/reject cap_123', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Rejected', text)
        self.assertIn('cap_123', text)
        self.assertNotIn('event_id', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_a_success_reply_includes_event_id(self, mock_tg, mock_api):
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_123'}},
            {'success': True, 'capture_id': 'cap_123', 'event_id': 'evt_a_123'}
        ]
        bot.handle_a('/a 1', CHAT_ID)
        self.assertEqual(mock_tg.call_count, 1)
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Approved', text)
        self.assertIn('cap_123', text)
        self.assertIn('evt_a_123', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_r_success_reply_includes_event_id(self, mock_tg, mock_api):
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_123'}},
            {'success': True, 'capture_id': 'cap_123', 'event_id': 'evt_r_123'}
        ]
        bot.handle_r('/r 1', CHAT_ID)
        self.assertEqual(mock_tg.call_count, 1)
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Rejected', text)
        self.assertIn('cap_123', text)
        self.assertIn('evt_r_123', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_capture_error_reply_does_not_claim_event_id(self, mock_tg, mock_api):
        mock_api.return_value = {'success': False, 'error': 'invalid_text'}
        bot.handle_capture('/capture hello', CHAT_ID, AUTHORIZED_SENDER, {})
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('LifeOS capture unavailable', text)
        self.assertNotIn('event_id', text)


class TestPollingModeControls(unittest.TestCase):
    def setUp(self):
        self.original_allow_review = bot.ALLOW_REVIEW_COMMANDS

    def tearDown(self):
        bot.ALLOW_REVIEW_COMMANDS = self.original_allow_review

    @patch.object(bot, 'tg_api')
    @patch.object(bot, 'call_action_api')
    def test_read_only_commands_allowed_in_capture_first(self, mock_api, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'handle_p') as mock_p:
                update = make_update('/p')
                bot.process_update(update)
                mock_p.assert_called_once()

            with patch.object(bot, 'handle_view') as mock_v:
                update = make_update('/view 1')
                bot.process_update(update)
                mock_v.assert_called_once()

            with patch.object(bot, 'handle_view') as mock_v:
                update = make_update('/view1')
                bot.process_update(update)
                mock_v.assert_called_once()

    @patch.object(bot, 'tg_api')
    def test_mutation_commands_blocked_in_capture_first(self, mock_tg):
        bot.ALLOW_REVIEW_COMMANDS = False
        mutation_commands = ['/a 1', '/r 1', '/a1', '/r1',
                             '/approve cap_1', '/reject cap_1', '/list_pending']

        for cmd in mutation_commands:
            mock_tg.reset_mock()
            update = make_update(cmd)
            with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
                bot.process_update(update)

            mock_tg.assert_called_once()
            text = mock_tg.call_args[0][1]['text']
            self.assertIn('REVIEW DISABLED', text.upper())

    @patch.object(bot, 'handle_p')
    @patch.object(bot, 'tg_api')
    def test_review_commands_allowed_when_flag_enabled(self, mock_tg, mock_handle_p):
        bot.ALLOW_REVIEW_COMMANDS = True
        update = make_update('/p')
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            bot.process_update(update)

        mock_handle_p.assert_called_once_with(CHAT_ID)
        mock_tg.assert_not_called()


class TestOfflineReviewValidation(unittest.TestCase):
    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_view_pending_capture_info_safely(self, mock_tg, mock_api):
        mock_api.return_value = {
            'success': True,
            'capture': {
                'capture_id': 'cap_123',
                'capture_type': 'note',
                'status': 'pending_review',
                'created_at': '2026-07-07T00:00:00Z',
                'content': 'Test note content text.'
            }
        }
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            bot.handle_view('/view 1', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Capture', text)
        self.assertIn('pending_review', text)
        self.assertIn('Test note content text.', text)
        self.assertNotIn('30_Capture', text)
        self.assertNotIn('.md', text)

    @patch.object(bot, 'tg_api')
    def test_view_invalid_id_fails_safely(self, mock_tg):
        bot.handle_view('/view ../../secret', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Invalid argument. Use a number, "latest", or a capture_id.', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_view_missing_capture_fails_safely(self, mock_tg, mock_api):
        mock_api.return_value = {'success': False}
        bot.handle_view('/view 999', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Capture not found or unavailable. No action was taken.', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_a_approves_only_through_action_api(self, mock_tg, mock_api):
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_123'}},
            {'success': True, 'capture_id': 'cap_123'}
        ]
        with patch('builtins.open') as mock_open:
            bot.handle_a('/a 1', CHAT_ID)
            # Verify it didn't call builtins.open (no direct filesystem modification)
            mock_open.assert_not_called()
        
        self.assertEqual(mock_api.call_count, 2)
        self.assertEqual(mock_api.call_args_list[0].args, ('/captures/pending/1',))
        self.assertEqual(mock_api.call_args_list[1].args, ('/captures/cap_123/approve', {}))
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Approved', text)
        self.assertIn('cap_123', text)
        self.assertNotIn('30_Capture', text)
        self.assertNotIn('.md', text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_r_rejects_only_through_action_api(self, mock_tg, mock_api):
        mock_api.side_effect = [
            {'success': True, 'capture': {'capture_id': 'cap_123'}},
            {'success': True, 'capture_id': 'cap_123'}
        ]
        with patch('builtins.open') as mock_open:
            bot.handle_r('/r 1', CHAT_ID)
            # Verify no direct filesystem modification
            mock_open.assert_not_called()

        self.assertEqual(mock_api.call_count, 2)
        self.assertEqual(mock_api.call_args_list[0].args, ('/captures/pending/1',))
        self.assertEqual(mock_api.call_args_list[1].args, ('/captures/cap_123/reject', {}))
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Rejected', text)
        self.assertIn('cap_123', text)
        self.assertNotIn('30_Capture', text)
        self.assertNotIn('.md', text)

    @patch.object(bot, 'tg_api')
    def test_a_invalid_id_fails_safely(self, mock_tg):
        bot.handle_a('/a invalid_index', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn("Invalid index: 'invalid_index'. Use a number or 'latest'.", text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_a_missing_capture_fails_safely(self, mock_tg, mock_api):
        mock_api.return_value = {'success': False}
        bot.handle_a('/a 999', CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Capture not found. No action was taken.', text)


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


class TestCallbackTokenHelpers(unittest.TestCase):
    """Offline token generation and verification tests."""

    TOKEN_TTL = 600

    def setUp(self):
        self.sender_id = 12345
        self.capture_id = "cap_20260707_120000_a1b2c3"
        self.cap_ref = "a1b2c3d4e5f6"   # first 12 hex of SHA256(capture_id)
        self.action = "a"
        # Fixed HMAC key for deterministic test output
        self.patcher = patch.object(bot, 'BOT_TOKEN', "test_token_12345")
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_make_cap_ref_is_first_12_hex_chars(self):
        ref = bot._make_cap_ref(self.capture_id)
        self.assertEqual(len(ref), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in ref))

    def test_make_cap_ref_is_deterministic(self):
        self.assertEqual(
            bot._make_cap_ref(self.capture_id),
            bot._make_cap_ref(self.capture_id),
        )

    def test_make_cap_ref_differs_for_different_ids(self):
        ref2 = bot._make_cap_ref("cap_other")
        self.assertNotEqual(bot._make_cap_ref(self.capture_id), ref2)

    def test_token_format_has_5_parts(self):
        cap_ref = bot._make_cap_ref(self.capture_id)
        token = bot._make_token(self.action, self.sender_id, cap_ref)
        parts = token.split("|")
        self.assertEqual(len(parts), 5)

    def test_token_starts_with_version(self):
        cap_ref = bot._make_cap_ref(self.capture_id)
        token = bot._make_token(self.action, self.sender_id, cap_ref)
        self.assertTrue(token.startswith("rv1|"))

    def test_token_contains_action_and_cap_ref(self):
        cap_ref = bot._make_cap_ref(self.capture_id)
        token = bot._make_token(self.action, self.sender_id, cap_ref)
        self.assertIn(f"|{self.action}|{cap_ref}|", token)

    def test_token_under_64_bytes(self):
        cap_ref = bot._make_cap_ref(self.capture_id)
        for act in ("v", "a", "r", "ca", "cr", "n"):
            token = bot._make_token(act, self.sender_id, cap_ref)
            self.assertLessEqual(len(token), 64, f"token for action {act} exceeds 64 bytes")

    def test_verify_token_valid(self):
        cap_ref = bot._make_cap_ref(self.capture_id)
        token = bot._make_token(self.action, self.sender_id, cap_ref)
        result = bot._verify_token(self.sender_id, token)
        self.assertIsNotNone(result)
        self.assertEqual(result["action"], self.action)
        self.assertEqual(result["cap_ref"], cap_ref)

    def test_verify_token_rejects_wrong_sender(self):
        cap_ref = bot._make_cap_ref(self.capture_id)
        token = bot._make_token(self.action, self.sender_id, cap_ref)
        result = bot._verify_token(99999, token)
        self.assertIsNone(result)

    def test_verify_token_rejects_malformed_parts(self):
        result = bot._verify_token(self.sender_id, "bad|data")
        self.assertIsNone(result)

    def test_verify_token_rejects_wrong_version(self):
        result = bot._verify_token(self.sender_id, "badver|a|caf|690f2a10|deadbeef")
        self.assertIsNone(result)

    def test_verify_token_rejects_unknown_action(self):
        cap_ref = bot._make_cap_ref(self.capture_id)
        # Build a token-like string with an invalid action
        exp_hex = format(int(time.time()) + 600, "x")
        payload = f"rv1|x|{self.sender_id}|{cap_ref}|{exp_hex}"
        key = hashlib.sha256(b"test_token_12345").digest()
        mac = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()[:12]
        token = f"rv1|x|{cap_ref}|{exp_hex}|{mac}"
        result = bot._verify_token(self.sender_id, token)
        self.assertIsNone(result)

    def test_verify_token_action_bound(self):
        """Token for action 'a' fails verification when checked as action 'r'."""
        cap_ref = bot._make_cap_ref(self.capture_id)
        token_a = bot._make_token("a", self.sender_id, cap_ref)
        # Verification reconstructs payload using the same action from token — so this
        # test verifies the action is embedded in the MAC and cannot be swapped.
        # A token created for 'a' has action 'a' in its visible data, so verify_token
        # uses token's own action field from the visible data. If someone modifies the
        # visible action char, MAC will mismatch.
        parts = token_a.split("|")
        tampered = f"rv1|r|{parts[2]}|{parts[3]}|{parts[4]}"
        result = bot._verify_token(self.sender_id, tampered)
        self.assertIsNone(result)

    def test_verify_token_rejects_expired_token(self):
        cap_ref = bot._make_cap_ref(self.capture_id)
        # Manually create an expired token
        exp_hex = format(int(time.time()) - 1, "x")
        payload = f"rv1|{self.action}|{self.sender_id}|{cap_ref}|{exp_hex}"
        key = hashlib.sha256(b"test_token_12345").digest()
        mac = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()[:12]
        token = f"rv1|{self.action}|{cap_ref}|{exp_hex}|{mac}"
        result = bot._verify_token(self.sender_id, token)
        self.assertIsNone(result)



class TestCallbackQueryDispatch(unittest.TestCase):
    """Callback query handler dispatch and safety gates."""

    def make_callback_update(self, callback_data, sender_id=AUTHORIZED_SENDER, chat_id=CHAT_ID, msg_id=100):
        return {
            "update_id": 2,
            "callback_query": {
                "id": "cb_test_1",
                "from": {"id": sender_id, "first_name": "TestUser"},
                "message": {
                    "message_id": msg_id,
                    "chat": {"id": chat_id},
                },
                "data": callback_data,
            }
        }

    def make_valid_token(self, action, sender_id=AUTHORIZED_SENDER):
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            cap_ref = bot._make_cap_ref("cap_test_123")
            return bot._make_token(action, sender_id, cap_ref)

    @patch.object(bot, 'tg_api')
    def test_unauthorized_callback_answers_and_returns(self, mock_tg):
        cb_data = self.make_valid_token("n")
        update = self.make_callback_update(cb_data, sender_id=UNAUTHORIZED_SENDER)
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            bot.process_callback_query(update)
        mock_tg.assert_called_once_with("answerCallbackQuery", {"callback_query_id": "cb_test_1"})

    @patch.object(bot, 'tg_api')
    def test_review_disabled_blocks_mutation_actions(self, mock_tg):
        cb_data = self.make_valid_token("a")
        update = self.make_callback_update(cb_data)
        bot.ALLOW_REVIEW_COMMANDS = False
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'BOT_TOKEN', "test_token"):
                bot.process_callback_query(update)
        mock_tg.assert_any_call("answerCallbackQuery", {
            "callback_query_id": "cb_test_1",
            "text": "Review actions are disabled. Read-only review still works."
        })

    @patch.object(bot, 'tg_api')
    def test_review_disabled_allows_readonly_actions(self, mock_tg):
        cb_data = self.make_valid_token("v")
        update = self.make_callback_update(cb_data)
        bot.ALLOW_REVIEW_COMMANDS = False
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'BOT_TOKEN', "test_token"):
                with patch.object(bot, '_handle_view_full') as mock_handler:
                    bot.process_callback_query(update)
                    mock_handler.assert_called_once()

    @patch.object(bot, 'tg_api')
    def test_invalid_token_answers_with_text_and_returns(self, mock_tg):
        update = self.make_callback_update("invalid|data|here|too|short")
        bot.ALLOW_REVIEW_COMMANDS = True
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            bot.process_callback_query(update)
        mock_tg.assert_called_once_with("answerCallbackQuery", {
            "callback_query_id": "cb_test_1",
            "text": "Invalid or expired button. Please /p to refresh."
        })

    @patch.object(bot, 'tg_api')
    def test_cancel_action_answers_no_text_and_handles(self, mock_tg):
        cb_data = self.make_valid_token("n")
        update = self.make_callback_update(cb_data)
        bot.ALLOW_REVIEW_COMMANDS = True
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'BOT_TOKEN', "test_token"):
                with patch.object(bot, '_handle_cancel') as mock_cancel:
                    bot.process_callback_query(update)
                    mock_cancel.assert_called_once_with(CHAT_ID, 100)
                    mock_tg.assert_called_once_with("answerCallbackQuery", {"callback_query_id": "cb_test_1"})

    @patch.object(bot, 'tg_api')
    def test_success_path_answers_once_no_text(self, mock_tg):
        """Valid token + review enabled = answerCallbackQuery called once with no text."""
        cb_data = self.make_valid_token("n")
        update = self.make_callback_update(cb_data)
        bot.ALLOW_REVIEW_COMMANDS = True
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'BOT_TOKEN', "test_token"):
                with patch.object(bot, '_handle_cancel'):
                    bot.process_callback_query(update)
        self.assertEqual(mock_tg.call_count, 1)
        args = mock_tg.call_args[0]
        self.assertEqual(args[0], "answerCallbackQuery")
        self.assertNotIn("text", args[1])

    @patch.object(bot, 'tg_api')
    def test_process_update_dispatches_callback_query(self, mock_tg):
        """process_update routes callback_query updates to process_callback_query."""
        cb_data = self.make_valid_token("n")
        update = self.make_callback_update(cb_data)
        bot.ALLOW_REVIEW_COMMANDS = True
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            with patch.object(bot, 'process_callback_query') as mock_dispatch:
                bot.process_update(update)
                mock_dispatch.assert_called_once_with(update)


class TestViewSummaryAndButtons(unittest.TestCase):
    """Modified /view sends summary + inline keyboard with tokens."""

    SAMPLE_CAPTURE = {
        "capture_id": "cap_20260707_120000_a1b2c3_slug",
        "status": "pending_review",
        "created_at": "2026-07-07T12:00:00Z",
        "content": "My quick note about something important.\n\nSecond line.",
    }

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_view_sends_summary_instead_of_full_content(self, mock_tg, mock_api):
        mock_api.return_value = {"success": True, "capture": self.SAMPLE_CAPTURE}
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            bot.handle_view("/view 1", CHAT_ID)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]["text"]
        self.assertIn("Capture", text)
        self.assertIn("pending_review", text)
        self.assertIn("My quick note about something important.", text)
        self.assertNotIn("Second line.", text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_view_includes_inline_keyboard(self, mock_tg, mock_api):
        mock_api.return_value = {"success": True, "capture": self.SAMPLE_CAPTURE}
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            bot.handle_view("/view 1", CHAT_ID)
        args = mock_tg.call_args[0]
        self.assertEqual(args[0], "sendMessage")
        payload = args[1]
        self.assertIn("reply_markup", payload)
        kb = payload["reply_markup"]
        self.assertIn("inline_keyboard", kb)
        buttons = kb["inline_keyboard"]
        self.assertEqual(len(buttons), 2)
        self.assertEqual(len(buttons[0]), 2)  # View Full + Proposal
        self.assertEqual(len(buttons[1]), 2)  # Approve + Reject
        self.assertEqual(buttons[0][0]["text"], "View Full")
        self.assertEqual(buttons[0][1]["text"], "Proposal")
        self.assertEqual(buttons[1][0]["text"], "Approve")
        self.assertEqual(buttons[1][1]["text"], "Reject")

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_view_keyboard_has_callback_data(self, mock_tg, mock_api):
        mock_api.return_value = {"success": True, "capture": self.SAMPLE_CAPTURE}
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            bot.handle_view("/view 1", CHAT_ID)
        payload = mock_tg.call_args[0][1]
        buttons = payload["reply_markup"]["inline_keyboard"]
        # All buttons should have callback_data
        for row in buttons:
            for btn in row:
                self.assertIn("callback_data", btn)
                data = btn["callback_data"]
                self.assertGreater(len(data), 0)
                self.assertLessEqual(len(data), 64)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_view_keyboard_action_chars(self, mock_tg, mock_api):
        mock_api.return_value = {"success": True, "capture": self.SAMPLE_CAPTURE}
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            bot.handle_view("/view 1", CHAT_ID)
        payload = mock_tg.call_args[0][1]
        buttons = payload["reply_markup"]["inline_keyboard"]
        # View Full button should have action 'v'
        v_data = buttons[0][0]["callback_data"]
        self.assertTrue(v_data.startswith("rv1|v|"))
        # Approve should have action 'a'
        a_data = buttons[1][0]["callback_data"]
        self.assertTrue(a_data.startswith("rv1|a|"))
        # Reject should have action 'r'
        r_data = buttons[1][1]["callback_data"]
        self.assertTrue(r_data.startswith("rv1|r|"))

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_view_full_resolves_and_sends_content(self, mock_tg, mock_api):
        """_handle_view_full resolves cap_ref and sends full content as new message."""
        cap_ref = bot._make_cap_ref("cap_test_123")
        mock_api.side_effect = [
            # First call for _resolve_cap_ref: GET /captures/pending
            {"success": True, "pending": [
                {"capture_id": "cap_test_123", "index": 1, "status": "pending_review", "created_at": "", "preview": ""},
            ], "count": 1},
            # Second call for full capture data
            {"success": True, "capture": {
                "capture_id": "cap_test_123",
                "status": "pending_review",
                "created_at": "2026-07-07T12:00:00Z",
                "content": "Full content line 1.\nLine 2.\nLine 3.",
            }},
        ]
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            bot._handle_view_full(CHAT_ID, cap_ref, AUTHORIZED_SENDER)
        self.assertEqual(mock_tg.call_count, 1)
        text = mock_tg.call_args[0][1]["text"]
        self.assertIn("Full content line 1.", text)
        self.assertIn("Line 2.", text)
        self.assertIn("Line 3.", text)
        payload = mock_tg.call_args[0][1]
        self.assertIn("reply_markup", payload)
        buttons = payload["reply_markup"]["inline_keyboard"]
        self.assertEqual(buttons[0][0]["text"], "Proposal")
        self.assertEqual(buttons[1][0]["text"], "Approve")
        self.assertEqual(buttons[1][1]["text"], "Reject")

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_view_full_no_matches_sends_error(self, mock_tg, mock_api):
        cap_ref = bot._make_cap_ref("nonexistent")
        mock_api.return_value = {"success": True, "pending": [], "count": 0}
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            bot._handle_view_full(CHAT_ID, cap_ref, AUTHORIZED_SENDER)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]["text"]
        self.assertIn("no longer pending", text)

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_view_truncates_preview_line(self, mock_tg, mock_api):
        long_text = "A" * 200
        mock_api.return_value = {"success": True, "capture": {
            "capture_id": "cap_long",
            "status": "pending_review",
            "created_at": "2026-07-07T12:00:00Z",
            "content": long_text,
        }}
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            bot.handle_view("/view 1", CHAT_ID)
        text = mock_tg.call_args[0][1]["text"]
        # Preview should not contain the full 200-char line — it will be truncated
        self.assertLessEqual(len(text.split("\n")[-1]) if "\n" in text else len(text), 130)


class TestIntentAndConfirmFlows(unittest.TestCase):
    """Approve/reject intent shows confirmation; confirm calls Action API."""

    def setUp(self):
        self.sender_id = AUTHORIZED_SENDER
        self.cap_ref = bot._make_cap_ref("cap_test_123")
        self.chat_id = CHAT_ID
        self.msg_id = 100
        self.pending_list = {
            "success": True,
            "pending": [
                {"capture_id": "cap_test_123", "index": 1, "status": "pending_review",
                 "created_at": "2026-07-07T12:00:00Z", "preview": "Test capture content"},
            ],
            "count": 1,
        }

    # --- Approve Intent ---

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_approve_intent_shows_confirmation_and_generates_tokens(self, mock_tg, mock_api):
        mock_api.return_value = self.pending_list
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                bot._handle_approve_intent(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)

        # Should edit the original message
        mock_tg.assert_called_once()
        args = mock_tg.call_args[0]
        self.assertEqual(args[0], "editMessageText")
        payload = args[1]
        self.assertEqual(payload["chat_id"], self.chat_id)
        self.assertEqual(payload["message_id"], self.msg_id)
        self.assertIn("Confirm Approval", payload["text"])
        self.assertIn("cap_test_123", payload["text"])

        # Should have Confirm Approve + Cancel buttons
        kb = payload["reply_markup"]["inline_keyboard"]
        self.assertEqual(len(kb), 1)
        self.assertEqual(len(kb[0]), 2)
        self.assertEqual(kb[0][0]["text"], "Confirm Approve")
        self.assertEqual(kb[0][1]["text"], "Cancel")
        # Callback data should be 'ca' and 'n' tokens
        self.assertTrue(kb[0][0]["callback_data"].startswith("rv1|ca|"))
        self.assertTrue(kb[0][1]["callback_data"].startswith("rv1|n|"))

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_approve_intent_no_pending_capture_shows_error(self, mock_tg, mock_api):
        mock_api.return_value = {"success": True, "pending": [], "count": 0}
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                bot._handle_approve_intent(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
        mock_tg.assert_called_once_with("sendMessage", {
            "chat_id": self.chat_id,
            "text": "Capture no longer pending. Please /p to refresh.",
        })

    # --- Reject Intent ---

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_reject_intent_shows_confirmation(self, mock_tg, mock_api):
        mock_api.return_value = self.pending_list
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                bot._handle_reject_intent(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)

        mock_tg.assert_called_once()
        payload = mock_tg.call_args[0][1]
        self.assertIn("Confirm Rejection", payload["text"])
        self.assertEqual(payload["reply_markup"]["inline_keyboard"][0][0]["text"], "Confirm Reject")
        self.assertTrue(payload["reply_markup"]["inline_keyboard"][0][0]["callback_data"].startswith("rv1|cr|"))

    # --- Confirm Approve Mutation ---

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_confirm_approve_calls_action_api_and_shows_event_id(self, mock_tg, mock_api):
        mock_api.side_effect = [
            self.pending_list,  # _resolve_cap_ref
            {"success": True, "capture_id": "cap_test_123", "event_id": "evt_approve_123"},  # POST approve
        ]
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                bot._handle_confirm_approve(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)

        # Should edit the original message
        edit_call = mock_tg.call_args_list[0]
        self.assertEqual(edit_call[0][0], "editMessageText")
        payload = edit_call[0][1]
        self.assertIn("Approved", payload["text"])
        self.assertIn("cap_test_123", payload["text"])
        self.assertIn("evt_approve_123", payload["text"])
        # Keyboard should be removed
        self.assertEqual(payload["reply_markup"], {"inline_keyboard": []})

        # Verify approve was called
        self.assertEqual(mock_api.call_args_list[1][0][0], "/captures/cap_test_123/approve")

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_confirm_approve_no_longer_pending_does_not_mutate(self, mock_tg, mock_api):
        mock_api.return_value = {"success": True, "pending": [], "count": 0}
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                bot._handle_confirm_approve(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
        # Should NOT call approve endpoint
        self.assertEqual(mock_api.call_count, 1)  # only the pending list call
        mock_tg.assert_called_once_with("sendMessage", {
            "chat_id": self.chat_id,
            "text": "Capture no longer pending. Please /p to refresh.",
        })

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_confirm_approve_api_unavailable_does_not_mutate(self, mock_tg, mock_api):
        mock_api.side_effect = [
            self.pending_list,
            None,  # Action API unavailable
        ]
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                bot._handle_confirm_approve(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
        mock_tg.assert_called_once_with("sendMessage", {
            "chat_id": self.chat_id,
            "text": "LifeOS review unavailable. No action was taken.",
        })

    # --- Confirm Reject Mutation ---

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_confirm_reject_calls_action_api_and_shows_event_id(self, mock_tg, mock_api):
        mock_api.side_effect = [
            self.pending_list,  # _resolve_cap_ref
            {"success": True, "capture_id": "cap_test_123", "event_id": "evt_reject_123"},  # POST reject
        ]
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                bot._handle_confirm_reject(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)

        edit_call = mock_tg.call_args_list[0]
        self.assertEqual(edit_call[0][0], "editMessageText")
        payload = edit_call[0][1]
        self.assertIn("Rejected", payload["text"])
        self.assertIn("cap_test_123", payload["text"])
        self.assertIn("evt_reject_123", payload["text"])
        self.assertEqual(payload["reply_markup"], {"inline_keyboard": []})

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_confirm_reject_no_longer_pending_does_not_mutate(self, mock_tg, mock_api):
        mock_api.return_value = {"success": True, "pending": [], "count": 0}
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                bot._handle_confirm_reject(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
        self.assertEqual(mock_api.call_count, 1)

    # --- Boundary: no direct filesystem access ---

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_intent_flow_does_not_touch_filesystem(self, mock_tg, mock_api):
        mock_api.return_value = self.pending_list
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                with patch("builtins.open") as mock_open:
                    bot._handle_approve_intent(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
                    mock_open.assert_not_called()

    @patch.object(bot, 'call_action_api')
    @patch.object(bot, 'tg_api')
    def test_confirm_flow_does_not_touch_filesystem(self, mock_tg, mock_api):
        mock_api.side_effect = [
            self.pending_list,
            {"success": True, "capture_id": "cap_test_123", "event_id": "evt_approve_123"},
        ]
        with patch.object(bot, 'BOT_TOKEN', "test_token"):
            with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                with patch("builtins.open") as mock_open:
                    bot._handle_confirm_approve(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
                    mock_open.assert_not_called()


class TestKtCommand(unittest.TestCase):
    """Tests for /kt command and proposal flow."""

    def setUp(self):
        self.patch_tg = patch('telegram_capture_bot.tg_api')
        self.mock_tg = self.patch_tg.start()
        with patch.object(bot, '_hmac_key', return_value=b'X' * 32):
            pass

    def tearDown(self):
        self.patch_tg.stop()

    @patch('telegram_capture_bot.call_action_api')
    def test_handle_kt_calls_orchestrator(self, mock_call_api):
        """/kt should call the orchestrator via subprocess and send result card."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({
                'success': True,
                'proposal_id': 'prop_test_001',
                'classification': 'knowledge',
                'proposed_title': 'Test Knowledge Note',
                'proposed_vault_path': '03_KNOWLEDGE/AI/Test_Knowledge_Note.md',
                'proposal_path': '/tmp/prop_test_001.md',
            }), stderr='')
            bot.handle_kt('/kt latest', CHAT_ID)
            self.assertTrue(self.mock_tg.called)
            payload = self.mock_tg.call_args_list[1][0][1]  # skip progress message
            self.assertIn('knowledge', payload.get('text', ''))

    @patch('subprocess.run')
    def test_handle_kt_orchestrator_failure(self, mock_run):
        """/kt should handle orchestrator failure gracefully."""
        mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='Capture not found')
        bot.handle_kt('/kt invalid', CHAT_ID)
        self.assertTrue(self.mock_tg.called)
        text = self.mock_tg.call_args_list[-1][0][1].get('text', '')
        self.assertIn('failed', text.lower())

    @patch('subprocess.run')
    def test_handle_proposal_view_returns_details(self, mock_run):
        """/proposal_view should return proposal details from buffer."""
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({
            'success': True,
            'proposal_id': 'prop_test_001',
            'status': 'pending_human_review',
            'proposed_title': 'Test Note',
            'classification': 'knowledge',
            'proposed_vault_path': '03_KNOWLEDGE/AI/Test.md',
            'summary': 'A test summary',
        }), stderr='')
        bot.handle_proposal_view('/proposal_view prop_test_001', CHAT_ID)
        self.assertTrue(self.mock_tg.called)
        text = self.mock_tg.call_args_list[-1][0][1].get('text', '')
        self.assertIn('prop_test_001', text)

    @patch('subprocess.run')
    def test_handle_proposal_reject_sets_status(self, mock_run):
        """/proposal_reject should set proposal to rejected."""
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({
            'success': True,
        }), stderr='')
        bot.handle_proposal_reject('/proposal_reject prop_test_001 Just because', CHAT_ID)
        self.assertTrue(self.mock_tg.called)
        text = self.mock_tg.call_args_list[-1][0][1].get('text', '')
        self.assertIn('rejected', text.lower())

    @patch('subprocess.run')
    def test_handle_proposal_revise_records_instruction(self, mock_run):
        """/proposal_revise should record revision instruction."""
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({
            'success': True,
        }), stderr='')
        bot.handle_proposal_revise('/proposal_revise prop_test_001 Change the title', CHAT_ID)
        self.assertTrue(self.mock_tg.called)
        text = self.mock_tg.call_args_list[-1][0][1].get('text', '')
        self.assertIn('Revision', text)

    @patch('subprocess.run')
    def test_handle_proposal_approve_shows_confirmation(self, mock_run):
        """/proposal_approve should approve but NOT import."""
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({
            'success': True,
            'proposed_vault_path': '03_KNOWLEDGE/AI/Test.md',
        }), stderr='')
        bot.handle_proposal_approve('/proposal_approve prop_test_001', CHAT_ID)
        self.assertTrue(self.mock_tg.called)
        text = self.mock_tg.call_args_list[-1][0][1].get('text', '')
        self.assertIn('approved', text.lower())
        self.assertIn('import_confirm', text.lower())

    @patch('subprocess.run')
    def test_handle_proposal_import_confirm_executes_import(self, mock_run):
        """/proposal_import_confirm should call the importer."""
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({
            'success': True,
            'destination': '03_KNOWLEDGE/AI/Test.md',
        }), stderr='')
        bot.handle_proposal_import_confirm('/proposal_import_confirm prop_test_001', CHAT_ID)
        self.assertTrue(self.mock_tg.called)
        text = self.mock_tg.call_args_list[-1][0][1].get('text', '')
        self.assertIn('Imported', text)

    @patch('subprocess.run')
    @patch.object(bot, 'append_event')
    @patch.object(bot, 'tg_api')
    def test_unauthorized_sender_blocked_from_kt(self, mock_tg, mock_append, mock_run):
        """process_update should reject unauthorized sender for /kt."""
        update = make_update('/kt latest', sender_id=UNAUTHORIZED_SENDER)
        with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
            bot.process_update(update)
        mock_tg.assert_called_once()
        text = mock_tg.call_args[0][1]['text']
        self.assertIn('Access denied', text)

    def test_command_added_to_dispatch(self):
        """Verify /kt and proposal handler functions exist."""
        self.assertTrue(hasattr(bot, 'handle_kt'), '/kt handler missing')
        self.assertTrue(hasattr(bot, 'handle_proposal_view'), '/proposal_view handler missing')
        self.assertTrue(hasattr(bot, 'handle_proposal_revise'), '/proposal_revise handler missing')
        self.assertTrue(hasattr(bot, 'handle_proposal_reject'), '/proposal_reject handler missing')
        self.assertTrue(hasattr(bot, 'handle_proposal_approve'), '/proposal_approve handler missing')
        self.assertTrue(hasattr(bot, 'handle_proposal_import_confirm'), '/proposal_import_confirm handler missing')

    @patch('subprocess.run')
    def test_no_direct_vault_write_from_kt_handler(self, mock_run):
        """Telegram /kt must not write to vault directly."""
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({
            'success': True, 'proposal_id': 'test', 'classification': 'knowledge',
            'proposed_title': 'T', 'proposed_vault_path': '03_KNOWLEDGE/AI/T.md',
        }), stderr='')
        with patch('builtins.open') as mock_open:
            bot.handle_kt('/kt latest', CHAT_ID)
        vault_writes = [c for c in mock_open.call_args_list if '/10_Vaults/LifeOS/' in str(c)]
        self.assertEqual(len(vault_writes), 0, "Telegram must not write to vault")

    @patch('subprocess.run')
    def test_no_shell_execution(self, mock_run):
        """Telegram must not invoke shell commands."""
        mock_run.return_value = MagicMock(returncode=0, stdout='{"success":true}', stderr='')
        bot.handle_kt('/kt latest', CHAT_ID)
        calls = mock_run.call_args_list
        for c in calls:
            args = c[0][0] if c[0] else []
            self.assertNotIn('shell', str(args).lower())

    @patch('subprocess.run')
    def test_no_arbitrary_mcp_tool_accepted(self, mock_run):
        """Telegram must not accept arbitrary MCP tool names from user."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='test', timeout=1)
        with patch.object(bot, 'tg_api') as mock_tg:
            bot.handle_kt('/kt latest', CHAT_ID)
        texts = [c[0][1].get('text', '') for c in mock_tg.call_args_list if c[0]]
        has_mcp = any('mcp' in t.lower() and 'tool' in t.lower() for t in texts)
        self.assertFalse(has_mcp, "Telegram must not accept arbitrary MCP tool names")

    @patch('subprocess.run')
    def test_kt_does_not_expose_argparse_usage(self, mock_run):
        """Telegram must not expose argparse usage text on orchestrator failure."""
        mock_run.return_value = MagicMock(returncode=2, stdout='', stderr='usage: capture_review_orchestrator.py ...\nerror: unrecognized arguments')
        with patch.object(bot, 'tg_api') as mock_tg:
            bot.handle_kt('/kt latest', CHAT_ID)
        texts = [c[0][1].get('text', '') for c in mock_tg.call_args_list if 'sendMessage' in str(c)]
        for t in texts:
            self.assertNotIn('usage:', t, "Must not expose argparse usage to Telegram")
            self.assertNotIn('unrecognized', t, "Must not expose argparse error to Telegram")

    @patch('subprocess.run')
    def test_kt_does_not_expose_traceback(self, mock_run):
        """Telegram must not expose raw Python tracebacks."""
        mock_run.side_effect = RuntimeError('test error')
        with patch.object(bot, 'tg_api') as mock_tg:
            bot.handle_kt('/kt latest', CHAT_ID)
        texts = [c[0][1].get('text', '') for c in mock_tg.call_args_list if 'sendMessage' in str(c)]
        for t in texts:
            self.assertNotIn('Traceback', t, "Must not expose tracebacks")
            self.assertNotIn('RuntimeError', t, "Must not expose exception types")

    @patch('subprocess.run')
    def test_kt_does_not_expose_raw_stderr(self, mock_run):
        """Telegram must not send raw subprocess stderr to user."""
        mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='/home/lifeos/.env: Permission denied\nTraceback...')
        with patch.object(bot, 'tg_api') as mock_tg:
            bot.handle_kt('/kt latest', CHAT_ID)
        texts = [c[0][1].get('text', '') for c in mock_tg.call_args_list if 'sendMessage' in str(c)]
        for t in texts:
            self.assertNotIn('.env', t, "Must not expose file paths")
            self.assertNotIn('Permission denied', t, "Must not expose raw errors")

    def test_kt_rejects_shell_metachars_in_target(self):
        """handle_kt should silently reject targets with shell metacharacters."""
        with patch.object(bot, 'tg_api') as mock_tg:
            bot.handle_kt('/kt latest;rm -rf /', CHAT_ID)
        texts = [c[0][1].get('text', '') for c in mock_tg.call_args_list if 'sendMessage' in str(c)]
        self.assertTrue(any('Invalid' in t for t in texts), "Should reject shell metachars")

    @patch('subprocess.run')
    def test_kt_uses_list_args_not_string(self, mock_run):
        """handle_kt must use list args for subprocess, not a shell string."""
        mock_run.return_value = MagicMock(returncode=0, stdout='{"success":true,"proposal_id":"p","classification":"knowledge","proposed_vault_path":"t.md"}', stderr='')
        bot.handle_kt('/kt latest', CHAT_ID)
        self.assertTrue(mock_run.called)
        call_args = mock_run.call_args[0][0]
        self.assertIsInstance(call_args, list, "subprocess.run must receive list args, not string")

    @patch('subprocess.run')
    def test_kt_proposal_card_contains_required_text(self, mock_run):
        """Success response must include buffer/vault/import messages."""
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps({
            'success': True,
            'proposal_id': 'prop_test_001',
            'classification': 'knowledge',
            'capture_id': 'cap_test_123',
            'proposed_title': 'Test',
            'proposed_vault_path': '04_KNOWLEDGE/AI/Test.md',
        }), stderr='')
        with patch.object(bot, 'tg_api') as mock_tg:
            bot.handle_kt('/kt latest', CHAT_ID)
        # Get the final response (not the progress message)
        texts = [c[0][1].get('text', '') for c in mock_tg.call_args_list if 'sendMessage' in str(c)]
        final = texts[-1] if texts else ''
        self.assertIn('buffer', final.lower(), "Must say buffer")
        self.assertIn('vault unchanged', final.lower(), "Must say vault unchanged")
        self.assertIn('import requires', final.lower(), "Must say import requires confirmation")


if __name__ == '__main__':
    unittest.main()
