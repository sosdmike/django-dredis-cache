======================================
Distributed Redis Django Cache Backend
======================================

A distributed Redis cache backend for Django

Notes:
------

    *   This cache backend requires the `redis-py`_ Python client library for
        communicating with the Redis server.

    *   This is a fork of `django-redis-cache`_.  Since a cache backend is not likely
        to change much, it doesn't make much sense to add more machinery and overhead
        just to allow a distributed cache setup. django-redis-cache should remain simple
        and fast.

    *   The sharding uses consistent hashing so you can add or remove nodes without
        resharding everything.  However, since the server list is determined by the
        settings file, you can't dynamically add or delete cache servers.  To do so in
        the future, there needs to be some kind of shared state between app servers.
        Probably a redis server to hold the configuration and status of each cache
        server.  However, this will require a round trip from the app server to the
        cache configuration server before it can start the a normal cache lookup.

    *   Variable cache node consistent hashing requires a O(log n) lookup for every key
        access, where n is the number of cache servers.  This is less ideal than the
        O(1) lookup we are used to, but necessary if you don't have a fixed power of 2
        number of cache servers.




Usage
-----

1. Run ``python setup.py install`` to install,
   or place ``dredis_cache`` on your Python path.

2. Modify your Django settings to use ``dredis_cache`` :


On Django >= 1.3::

    CACHES = {
        'default': {
            'BACKEND': 'dredis_cache.RedisCache',
            'LOCATION': [
                '<host0>:<port0>',
                '<host1>:<port1>',
                '<host2>:<port2>',
                '<host3>:<port3>',
            ],
            'OPTIONS': { # optional
                'DB': 1,
                'PASSWORD': 'yadayada',
            },
        },
    }

.. _redis-py: http://github.com/andymccurdy/redis-py/
.. _django-redis-cache: http://github.com/sebleier/django-redis-cache/


Running tests
-------------

To run tests, you need four instances of a redis-server running on localhost,
ports 6379-6382. Then, assuming redis-py is installed, type
``python runtests.py`` in the project root.
