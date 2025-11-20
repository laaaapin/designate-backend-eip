======================================
SOLIDserver Backend for Designate
======================================

Overview
========

This is a Designate backend driver that integrates with SOLIDserver from EfficientIP for DNS zone and record management.

Features
--------

- Create and delete DNS zones
- Create, update, and delete DNS records (A, AAAA, CNAME, MX, NS, SRV, TXT, SOA, etc.)
- Support for master zones
- Zone synchronization with SOLIDserver
- API connectivity validation (ping)

Installation
============

1. Copy the `solidserver_backend.py` file to your Designate installation
2. Register the backend in Designate's setup.py or setup.cfg
3. Configure the backend in your Designate configuration

Configuration
=============

Add the following to your Designate configuration file (typically `/etc/designate/designate.conf`):

.. code-block:: ini

    [backend:solidserver]
    # SOLIDserver API host and port
    solidserver_host = 192.168.1.100
    solidserver_port = 443
    
    # SOLIDserver authentication
    solidserver_username = admin
    solidserver_password = your_password
    
    # SOLIDserver DNS configuration
    solidserver_dns_server = NS1
    solidserver_dns_view = default
    
    # SSL verification
    solidserver_verify_ssl = False

Then configure Designate to use this backend:

.. code-block:: ini

    [designate]
    backends = solidserver
    
    [[solidserver]]
    backend = solidserver

API Integration
===============

The backend communicates with SOLIDserver via its REST API v2.0 at:

    https://{host}:{port}/api/v2.0

Supported Endpoints
-------------------

- ``POST /dns/zone/add`` - Create DNS zone
- ``DELETE /dns/zone/delete`` - Delete DNS zone
- ``GET /dns/zone/list`` - List zones
- ``GET /dns/zone/info`` - Get zone information
- ``POST /dns/rr/add`` - Create DNS record
- ``DELETE /dns/rr/delete`` - Delete DNS record
- ``GET /dns/rr/list`` - List records
- ``GET /dns/rr/info`` - Get record information

Record Type Support
===================

The following DNS record types are supported:

- A
- AAAA
- CNAME
- MX
- NS
- SRV
- SOA
- TXT
- And any other type supported by SOLIDserver

Implementation Details
======================

Zone Management
---------------

When a zone is created in Designate, the backend:

1. Extracts zone name and configuration
2. Sends a POST request to ``/dns/zone/add`` endpoint
3. Stores the returned zone ID for future reference
4. Logs the operation

When a zone is deleted, the backend:

1. Sends a DELETE request to ``/dns/zone/delete`` endpoint
2. Confirms successful deletion
3. Logs the operation

Record Management
-----------------

For each record in a recordset:

1. Extract record data and build SOLIDserver-compatible value
2. Send appropriate API request (POST for create, DELETE for remove)
3. Handle record type-specific formatting (MX, SRV, etc.)
4. Log all operations

Authentication
---------------

The backend uses HTTP Basic Authentication with the configured username and password. The session is maintained throughout the backend's lifetime, reducing authentication overhead.

Error Handling
--------------

The backend:

1. Validates API responses for success status
2. Extracts error messages from API responses
3. Logs all errors for debugging
4. Raises Designate BackendException for error propagation

Logging
=======

The backend uses the standard OpenStack oslo_log module with the logger name `designate.backend.solidserver`.

All major operations are logged at INFO level:
- Zone creation/deletion
- Record creation/deletion/update
- Zone synchronization
- API connectivity checks

Errors are logged at ERROR level with full context.

Troubleshooting
===============

Connection Issues
-----------------

If you see authentication or connection errors:

1. Verify SOLIDserver host and port are correct
2. Check username and password
3. If using HTTPS with self-signed certificates, set `solidserver_verify_ssl = False`
4. Check SOLIDserver API is accessible: ``curl -k https://host:port/api/v2.0/dns/zone/list``

Zone Not Found
---------------

If zones are not appearing in SOLIDserver:

1. Verify the configured DNS server name matches SOLIDserver configuration
2. Check the DNS view name is correct
3. Review SOLIDserver logs for API errors

Record Creation Failures
------------------------

If record creation fails:

1. Check the record type is supported by SOLIDserver
2. Verify record data format is correct
3. Ensure the zone exists on SOLIDserver first
4. Check SOLIDserver resource limits and permissions

Performance Considerations
===========================

- The backend creates a persistent HTTP session with connection pooling
- Each operation requires at least one API call to SOLIDserver
- Zone synchronization performs a filtered query to verify zone state
- Consider network latency when setting Designate timeouts

Development
===========

To extend this backend:

1. Implement additional record type handlers in `_build_rr_value()`
2. Add support for additional zone types (slave, forward, etc.)
3. Implement bulk operations for better performance
4. Add caching layer for frequently accessed zones

License
=======

Apache License 2.0

See the LICENSE file for details.

Support
=======

For issues and questions:

1. Check the SOLIDserver API documentation
2. Review Designate backend documentation
3. Check Designate logs for detailed error messages
4. Contact your SOLIDserver support team

References
==========

- Designate Documentation: https://docs.openstack.org/designate/
- SOLIDserver API Documentation: https://www.efficientip.com/
- OpenStack Backend Development: https://docs.openstack.org/designate/latest/admin/backends.html
