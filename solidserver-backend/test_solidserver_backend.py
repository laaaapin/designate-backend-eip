"""
Unit tests for SOLIDserver Designate backend
"""

import unittest
from unittest import mock

from designate import exceptions
from designate.tests import TestCase
from designate import objects

from solidserver_backend import SolidServerBackend


class SolidServerBackendTestCase(TestCase):
    """Test cases for SolidServerBackend"""

    def setUp(self):
        """Set up test fixtures"""
        super(SolidServerBackendTestCase, self).setUp()
        
        # Mock configuration
        self.config_opts = {
            'solidserver_host': 'localhost',
            'solidserver_port': 443,
            'solidserver_username': 'admin',
            'solidserver_password': 'admin',
            'solidserver_dns_server': 'NS1',
            'solidserver_dns_view': 'default',
            'solidserver_verify_ssl': False,
        }

    @mock.patch('solidserver_backend.CONF')
    @mock.patch('solidserver_backend.requests.Session')
    def test_init(self, mock_session, mock_conf):
        """Test backend initialization"""
        mock_conf.__getitem__.return_value = mock.MagicMock(**self.config_opts)
        
        backend = SolidServerBackend(None)
        
        self.assertEqual(backend.host, 'localhost')
        self.assertEqual(backend.port, 443)
        self.assertEqual(backend.dns_server, 'NS1')

    @mock.patch('solidserver_backend.requests.Session')
    def test_create_zone(self, mock_session_class):
        """Test zone creation"""
        # Setup mock session
        mock_session = mock.MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'data': [{'zone_id': '123'}],
            'messages': []
        }
        mock_response.raise_for_status.return_value = None
        mock_session.request.return_value = mock_response
        
        with mock.patch('solidserver_backend.CONF') as mock_conf:
            mock_conf.__getitem__.return_value = mock.MagicMock(**self.config_opts)
            
            backend = SolidServerBackend(None)
            backend.session = mock_session
            
            # Create a zone object
            zone = objects.Zone(
                id='zone-id',
                name='example.com.',
                type='PRIMARY',
            )
            
            # Test zone creation
            backend.create_zone(None, zone)
            
            # Verify the request was made
            mock_session.request.assert_called_once()
            call_args = mock_session.request.call_args
            self.assertEqual(call_args[0][0], 'POST')
            self.assertIn('/dns/zone/add', call_args[0][1])

    @mock.patch('solidserver_backend.requests.Session')
    def test_delete_zone(self, mock_session_class):
        """Test zone deletion"""
        mock_session = mock.MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'data': [{'zone_id': '123'}],
            'messages': []
        }
        mock_response.raise_for_status.return_value = None
        mock_session.request.return_value = mock_response
        
        with mock.patch('solidserver_backend.CONF') as mock_conf:
            mock_conf.__getitem__.return_value = mock.MagicMock(**self.config_opts)
            
            backend = SolidServerBackend(None)
            backend.session = mock_session
            
            zone = objects.Zone(
                id='zone-id',
                name='example.com.',
                type='PRIMARY',
            )
            
            backend.delete_zone(None, zone)
            
            mock_session.request.assert_called_once()
            call_args = mock_session.request.call_args
            self.assertEqual(call_args[0][0], 'DELETE')
            self.assertIn('/dns/zone/delete', call_args[0][1])

    @mock.patch('solidserver_backend.requests.Session')
    def test_ping_success(self, mock_session_class):
        """Test successful ping"""
        mock_session = mock.MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'data': [{'count': 5}],
            'messages': []
        }
        mock_response.raise_for_status.return_value = None
        mock_session.request.return_value = mock_response
        
        with mock.patch('solidserver_backend.CONF') as mock_conf:
            mock_conf.__getitem__.return_value = mock.MagicMock(**self.config_opts)
            
            backend = SolidServerBackend(None)
            backend.session = mock_session
            
            result = backend.ping(None)
            
            self.assertTrue(result)

    @mock.patch('solidserver_backend.requests.Session')
    def test_ping_failure(self, mock_session_class):
        """Test failed ping"""
        mock_session = mock.MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_session.request.side_effect = Exception('Connection error')
        
        with mock.patch('solidserver_backend.CONF') as mock_conf:
            mock_conf.__getitem__.return_value = mock.MagicMock(**self.config_opts)
            
            backend = SolidServerBackend(None)
            backend.session = mock_session
            
            result = backend.ping(None)
            
            self.assertFalse(result)

    def test_build_rr_value_a_record(self):
        """Test A record value building"""
        with mock.patch('solidserver_backend.CONF') as mock_conf:
            mock_conf.__getitem__.return_value = mock.MagicMock(**self.config_opts)
            
            backend = SolidServerBackend(None)
            
            recordset = objects.RecordSet(type='A')
            record = objects.Record(data='192.0.2.1')
            
            value = backend._build_rr_value(recordset, record)
            
            self.assertEqual(value, '192.0.2.1')

    def test_build_rr_value_mx_record(self):
        """Test MX record value building"""
        with mock.patch('solidserver_backend.CONF') as mock_conf:
            mock_conf.__getitem__.return_value = mock.MagicMock(**self.config_opts)
            
            backend = SolidServerBackend(None)
            
            recordset = objects.RecordSet(type='MX')
            record = objects.Record(data='10 mail.example.com.')
            
            value = backend._build_rr_value(recordset, record)
            
            self.assertEqual(value, '10;mail.example.com.')


if __name__ == '__main__':
    unittest.main()
