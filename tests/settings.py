DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = [
    'tests.testapp',
]

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': [
            '127.0.0.1:6379',
            '127.0.0.1:6380',
            '127.0.0.1:6381',
            '127.0.0.1:6382',
        ],
        'OPTIONS': { # optional
            'DB': 15,
            'PASSWORD': 'yadayada',
        },
    },
}
