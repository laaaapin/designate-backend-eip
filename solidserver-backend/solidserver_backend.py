"""
SOLIDserver DNS Backend for Designate

This module implements a Designate backend driver for SOLIDserver EIP DNS service.
It handles DNS zone and resource record management through SOLIDserver's REST API.
"""

import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin

from oslo_log import log as logging
from oslo_config import cfg

from designate.backend import base
from designate import exceptions
from designate import objects

LOG = logging.getLogger(__name__)

# Configuration options
SOLIDSERVER_OPTS = [
    cfg.StrOpt(
        'url',
        help='SOLIDserver API URL (IP or hostname)',
        required=True
    ),
    cfg.StrOpt(
        'space',
        help='SOLIDserver space name',
        required=True
    ),
    cfg.StrOpt(
        'user',
        help='SOLIDserver API username',
        required=True
    ),
    cfg.StrOpt(
        'password',
        help='SOLIDserver API password',
        required=True,
        secret=True
    ),
    cfg.BoolOpt(
        'ssl',
        help='Use HTTPS for API communication',
        default=True
    ),
    cfg.BoolOpt(
        'verify_ssl',
        help='Verify SSL certificate',
        default=False
    ),
]

CONF = cfg.CONF
CONF.register_opts(SOLIDSERVER_OPTS, group='solidserver')


class SolidServerBackend(base.Backend):
    __plugin_name__ = 'solidserver'

    def __init__(self, target):
        """Initialize the SOLIDserver backend.

        Args:
            target: The backend target configuration
        """
        super(SolidServerBackend, self).__init__(target)
        
        # Get configuration from [solidserver] section
        self.url = CONF.solidserver.url
        self.space = CONF.solidserver.space
        self.user = CONF.solidserver.user
        self.password = CONF.solidserver.password
        self.ssl = CONF.solidserver.ssl
        self.verify_ssl = CONF.solidserver.verify_ssl
        
        # Build API base URL
        protocol = 'https' if self.ssl else 'http'
        self.api_url = f'{protocol}://{self.url}/api/v2.0'
        
        # Create session with authentication
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.user, self.password)
        self.session.verify = self.verify_ssl
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        LOG.info(
            'Initialized SOLIDserver backend: url=%s, space=%s, ssl=%s',
            self.url,
            self.space,
            self.ssl
        )

    def _request(self, method, endpoint, data=None, params=None):
        """Make a request to the SOLIDserver API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            Response JSON data

        Raises:
            exceptions.BackendException: If API request fails
        """
        url = urljoin(self.api_url, endpoint)
        
        try:
            response = self.session.request(
                method,
                url,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Check for API-level errors
            if not result.get('success', False):
                messages = result.get('messages', [])
                error_msg = ', '.join([m.get('msg', '') for m in messages])
                LOG.error(f'SOLIDserver API error: {error_msg}')
                raise exceptions.BackendException(error_msg)
            
            return result
            
        except requests.exceptions.RequestException as e:
            LOG.error(f'SOLIDserver API request failed: {e}')
            raise exceptions.BackendException(str(e))

    def _get_zone_params(self, zone):
        """Extract zone parameters for SOLIDserver API.

        Args:
            zone: Designate zone object

        Returns:
            Dictionary of zone parameters
        """
        return {
            'zone_name': zone.name.rstrip('.'),
            'zone_type': 'master',
            'zone_space': self.space,
            'row_state': 1,  # Enable the zone
        }

    def _get_record_params(self, zone, recordset, record):
        """Extract record parameters for SOLIDserver API.

        Args:
            zone: Designate zone object
            recordset: Designate recordset object
            record: Designate record object

        Returns:
            Dictionary of record parameters
        """
        # Map Designate record types to SOLIDserver RR types
        rr_type = recordset.type
        
        # Build the record value based on type
        rr_value = self._build_rr_value(recordset, record)
        
        params = {
            'zone_name': zone.name.rstrip('.'),
            'zone_space': self.space,
            'rr_name': recordset.name.rstrip('.'),
            'rr_type': rr_type,
            'rr_value': rr_value,
            'rr_ttl': recordset.ttl,
            'row_state': 1,
        }
        
        return params

    def _build_rr_value(self, recordset, record):
        """Build RR value string for SOLIDserver API based on record type.

        Args:
            recordset: Designate recordset object
            record: Designate record object

        Returns:
            String representation of the record value

        Raises:
            exceptions.BackendException: If record type is not A or AAAA
        """
        rr_type = recordset.type
        data = record.data
        
        # Only support A (IPv4) and AAAA (IPv6) record types
        if rr_type in ('A', 'AAAA'):
            return data
        else:
            error_msg = f'Unsupported record type: {rr_type}. Only A and AAAA records are supported.'
            LOG.error(error_msg)
            raise exceptions.BackendException(error_msg)

    def create_zone(self, context, zone):
        """Create a DNS zone.

        Args:
            context: Designate context
            zone: Designate zone object

        Raises:
            exceptions.BackendException: If zone creation fails
        """
        LOG.info('Creating zone %r', zone.name)
        
        zone_params = self._get_zone_params(zone)
        
        try:
            result = self._request('POST', '/dns/zone/add', data=zone_params)
            
            if result.get('data'):
                zone_id = result['data'][0].get('zone_id')
                LOG.info(f'Zone {zone.name} created with ID {zone_id}')
            else:
                raise exceptions.BackendException('No zone ID returned from API')
                
        except exceptions.BackendException as e:
            LOG.error(f'Failed to create zone {zone.name}: {e}')
            raise

    def delete_zone(self, context, zone):
        """Delete a DNS zone.

        Args:
            context: Designate context
            zone: Designate zone object

        Raises:
            exceptions.BackendException: If zone deletion fails
        """
        LOG.info('Deleting zone %r', zone.name)
        
        delete_params = {
            'zone_name': zone.name.rstrip('.'),
            'zone_space': self.space,
        }
        
        try:
            self._request('DELETE', '/dns/zone/delete', params=delete_params)
            LOG.info(f'Zone {zone.name} deleted')
            
        except exceptions.BackendException as e:
            LOG.error(f'Failed to delete zone {zone.name}: {e}')
            raise

    def create_recordset(self, context, zone, recordset):
        """Create a recordset (RRset).

        Args:
            context: Designate context
            zone: Designate zone object
            recordset: Designate recordset object

        Raises:
            exceptions.BackendException: If recordset creation fails or record type is not A/AAAA
        """
        # Validate record type
        if recordset.type not in ('A', 'AAAA'):
            error_msg = f'Unsupported record type: {recordset.type}. Only A and AAAA records are supported.'
            LOG.error(error_msg)
            raise exceptions.BackendException(error_msg)
        
        LOG.info('Creating recordset %r in zone %r', recordset.name, zone.name)
        
        # Create each record in the recordset
        for record in recordset.records:
            self.create_record(context, zone, recordset, record)

    def create_record(self, context, zone, recordset, record):
        """Create a single DNS record.

        Args:
            context: Designate context
            zone: Designate zone object
            recordset: Designate recordset object
            record: Designate record object

        Raises:
            exceptions.BackendException: If record creation fails or record type is not A/AAAA
        """
        LOG.info(
            'Creating record %s %s in zone %r',
            recordset.name,
            recordset.type,
            zone.name
        )
        
        record_params = self._get_record_params(zone, recordset, record)
        
        try:
            result = self._request('POST', '/dns/rr/add', data=record_params)
            
            if result.get('data'):
                rr_id = result['data'][0].get('rr_id')
                LOG.info(
                    f'Record {recordset.name} {recordset.type} created with ID {rr_id}'
                )
            else:
                raise exceptions.BackendException('No RR ID returned from API')
                
        except exceptions.BackendException as e:
            LOG.error(
                f'Failed to create record {recordset.name} {recordset.type}: {e}'
            )
            raise

    def delete_recordset(self, context, zone, recordset):
        """Delete a recordset (RRset).

        Args:
            context: Designate context
            zone: Designate zone object
            recordset: Designate recordset object

        Raises:
            exceptions.BackendException: If recordset deletion fails or record type is not A/AAAA
        """
        LOG.info('Deleting recordset %r in zone %r', recordset.name, zone.name)
        
        # Delete each record in the recordset
        for record in recordset.records:
            self.delete_record(context, zone, recordset, record)

    def delete_record(self, context, zone, recordset, record):
        """Delete a single DNS record.

        Args:
            context: Designate context
            zone: Designate zone object
            recordset: Designate recordset object
            record: Designate record object

        Raises:
            exceptions.BackendException: If record deletion fails or record type is not A/AAAA
        """
        LOG.info(
            'Deleting record %s %s in zone %r',
            recordset.name,
            recordset.type,
            zone.name
        )
        
        delete_params = {
            'zone_name': zone.name.rstrip('.'),
            'zone_space': self.space,
            'rr_name': recordset.name.rstrip('.'),
            'rr_type': recordset.type,
        }
        
        try:
            self._request('DELETE', '/dns/rr/delete', params=delete_params)
            LOG.info(
                f'Record {recordset.name} {recordset.type} deleted'
            )
            
        except exceptions.BackendException as e:
            LOG.error(
                f'Failed to delete record {recordset.name} {recordset.type}: {e}'
            )
            raise

    def update_recordset(self, context, zone, recordset, changes):
        """Update a recordset.

        Note: This is optional in base.Backend. Implement if your backend supports it.

        Args:
            context: Designate context
            zone: Designate zone object
            recordset: Designate recordset object
            changes: Tuple of (desired, existing) recordset objects

        Raises:
            exceptions.BackendException: If recordset update fails
        """
        desired, existing = changes
        
        LOG.info('Updating recordset %r in zone %r', desired.name, zone.name)
        
        # Delete old records and create new ones
        if existing:
            self.delete_recordset(context, zone, existing)
        
        if desired:
            self.create_recordset(context, zone, desired)

    def update_record(self, context, zone, recordset, record, changes):
        """Update a single record.

        Note: This is optional in base.Backend. Implement if your backend supports it.

        Args:
            context: Designate context
            zone: Designate zone object
            recordset: Designate recordset object
            record: Designate record object
            changes: Tuple of (desired, existing) record objects

        Raises:
            exceptions.BackendException: If record update fails
        """
        desired, existing = changes
        
        LOG.info(
            'Updating record %s %s in zone %r',
            recordset.name,
            recordset.type,
            zone.name
        )
        
        # Delete old record and create new one
        if existing:
            self.delete_record(context, zone, recordset, existing)
        
        if desired:
            self.create_record(context, zone, recordset, desired)

    def sync(self, context, zone, target=False):
        """Synchronize zone with SOLIDserver.

        Args:
            context: Designate context
            zone: Designate zone object
            target: Whether this is a target sync (optional)

        Returns:
            None (or list of serial/status objects if needed)
        """
        LOG.info('Syncing zone %r with SOLIDserver', zone.name)
        
        # Fetch the zone from SOLIDserver
        try:
            params = {
                'where': f'zone_name=\'{zone.name.rstrip(".")}\'',
                'zone_space': self.space,
            }
            
            result = self._request('GET', '/dns/zone/list', params=params)
            
            if result.get('data'):
                zone_data = result['data'][0]
                LOG.info(f'Zone {zone.name} synced from SOLIDserver')
                LOG.debug(f'Zone data: {zone_data}')
            else:
                LOG.warning(f'Zone {zone.name} not found on SOLIDserver')
                
        except exceptions.BackendException as e:
            LOG.error(f'Failed to sync zone {zone.name}: {e}')

    def ping(self, context):
        """Ping the SOLIDserver API to verify connectivity.

        Args:
            context: Designate context

        Returns:
            True if API is reachable, False otherwise
        """
        LOG.debug('Pinging SOLIDserver API')
        
        try:
            # Try to list zones (minimal operation)
            result = self._request('GET', '/dns/zone/count')
            
            if result.get('success'):
                LOG.debug('SOLIDserver API is reachable')
                return True
            else:
                LOG.warning('SOLIDserver API returned unsuccessful response')
                return False
                
        except exceptions.BackendException as e:
            LOG.error(f'Failed to ping SOLIDserver API: {e}')
            return False
