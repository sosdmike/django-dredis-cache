from collections import defaultdict
from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
from django.utils.encoding import smart_unicode, smart_str
from django.utils.datastructures import SortedDict
from sharder import CacheSharder

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import redis
except ImportError:
    raise InvalidCacheBackendError(
        "Redis cache backend requires the 'redis-py' library")


class CacheKey(object):
    """
    A stub string class that we can use to check if a key was created already.
    """
    def __init__(self, key):
        self._key = key

    def __eq__(self, other):
        return self._key == other

    def __repr__(self):
        return self.__unicode__()

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return smart_str(self._key)


class RedisCache(BaseCache):
    def __init__(self, server, params):
        """
        Connect to Redis, and set up cache backend.
        """
        super(RedisCache, self).__init__(params)
        self.sharder = CacheSharder()
        options = params.get('OPTIONS', {})
        password = params.get('password', options.get('PASSWORD', None))
        db = params.get('db', options.get('DB', 1))
        try:
            db = int(db)
        except (ValueError, TypeError):
            db = 1
        if isinstance(server, basestring):
            self._servers = server.split(';')
        else:
            self._servers = server or ['localhost']
        for host in self._servers:
            port = 6379
            if ':' in host:
                host, port = host.split(':')
                try:
                    port = int(port)
                except (ValueError, TypeError):
                    port = 6379
            client = redis.Redis(host=host, port=port, db=db, password=password)
            self.sharder.add(client, ":".join([host, str(port)]))

    def get_cache(self, key):
        return self.sharder.get_node(key)

    def get_caches(self, keys, version=None):
        """
        Returns a dict of keys that belong to a cache's keyspace.
        """
        caches = defaultdict(list)
        keys = map(lambda key: self.make_key(key, version=version), keys)
        for key in keys:
            caches[self.get_cache(key)].append(key)
        return caches

    @property
    def caches(self):
        return self.sharder._nodes

    def make_key(self, key, version=None):
        if not isinstance(key, CacheKey):
            key = CacheKey(super(RedisCache, self).make_key(key, version))
        return key

    def get(self, key, default=None, version=None):
        """
        Retrieve a value from the cache.

        Returns unpickled value if key is found, the default if not.
        """
        key = self.make_key(key, version=version)
        value = self.get_cache(key).get(key)
        if value is None:
            return default
        return self.unpickle(value)

    def get_many(self, keys, version=None):
        """
        Retrieve many keys.
        """
        recovered_data = SortedDict()
        new_keys = map(lambda key: self.make_key(key, version=version), keys)
        map_keys = dict(zip(new_keys, keys))
        caches = self.get_caches(new_keys)
        for cache, keys in caches.items():
            values = cache.mget(keys)
            for key, value in zip(keys, values):
                if value is None:
                    continue
                value = self.unpickle(value)
                if isinstance(value, basestring):
                    value = smart_unicode(value)
                recovered_data[map_keys[key]] = value
        return recovered_data

    def add(self, key, value, timeout=None, version=None):
        """
        Add a value to the cache, failing if the key already exists.

        Returns ``True`` if the object was added, ``False`` if not.
        """
        key = self.make_key(key, version=version)
        if self.get_cache(key).exists(key):
            return False
        return self.set(key, value, timeout)

    def set(self, key, value, timeout=None, version=None):
        """
        Persist a value to the cache, and set an optional expiration time.
        """
        key = self.make_key(key, version=version)
        result = self.get_cache(key).set(key, pickle.dumps(value))
        self.expire(key, timeout, version=version)
        return result

    def set_many(self, data, timeout=None, version=None):
        """
        Set a bunch of values in the cache at once from a dict of key/value
        pairs. This is much more efficient than calling set() multiple times.

        If timeout is given, that timeout will be used for the key; otherwise
        the default cache timeout will be used.
        """
        caches = defaultdict(dict)
        for key, value in data.iteritems():
            cache_key = self.make_key(key, version=version)
            caches[self.get_cache(cache_key)][cache_key] = pickle.dumps(value)
        if caches:
            for cache, safe_data in caches.items():
                cache.mset(safe_data)
                map(self.expire, safe_data.keys(), [timeout]*len(safe_data))

    def expire(self, key, timeout=None, version=None):
        """
        Set content expiration, if necessary
        """
        key = self.make_key(key, version=version)
        if timeout is None:
            timeout = self.default_timeout
        if timeout <= 0:
            # force the key to be non-volatile
            result = self.get_cache(key).get(key)
            self.get_cache(key).set(key, result)
        else:
            # If the expiration command returns false, we need to reset the key
            # with the new expiration
            if not self.get_cache(key).expire(key, timeout):
                value = self.get(key, version=version)
                self.set(key, value, timeout, version=version)

    def delete(self, key, version=None):
        """
        Remove a key from the cache.
        """
        self.get_cache(key).delete(self.make_key(key, version=version))

    def delete_many(self, keys, version=None):
        """
        Remove multiple keys at once.
        """
        if keys:
            caches = self.get_caches(keys, version)
            for cache, keys in caches.iteritems():
                cache.delete(*keys)

    def clear(self):
        """
        Flush all cache keys.
        """
        # TODO : potential data loss here, should we only delete keys based on the correct version ?
        for cache in self.caches:
            cache._node.flushdb()

    def unpickle(self, value):
        """
        Unpickles the given value.
        """
        value = smart_str(value)
        return pickle.loads(value)

    def incr_version(self, key, delta=1, version=None):
        """
        Adds delta to the cache version for the supplied key. Returns the
        new version.

        Note: In Redis 2.0 you cannot rename a volitle key, so we have to move
        the value from the old key to the new key and maintain the ttl.
        """
        if version is None:
            version = self.version
        old_key = self.make_key(key, version)
        value = self.get(old_key, version=version)
        ttl = self.get_cache(key).ttl(old_key)
        if value is None:
            raise ValueError("Key '%s' not found" % key)
        new_key = self.make_key(key, version=version+delta)
        # TODO: See if we can check the version of Redis, since 2.2 will be able
        # to rename volitile keys.
        self.set(new_key, value, timeout=ttl)
        self.delete(old_key)
        return version + delta

    def close(self, **kwargs):
        """
        Disconnect from the cache.
        """
        for cache in self.caches:
            node = cache._node
            if hasattr(node, 'connection_pool'):
                cache._node.connection_pool.disconnect()
            else:
                cache._node.connection.disconnect()
