from distutils.core import setup

setup(
    name = "django-dredis-cache",
    url = "http://github.com/sebleier/django-dredis-cache/",
    author = "Sean Bleier",
    author_email = "sebleier@gmail.com",
    version = "1.3.0a",
    packages = ["dredis_cache"],
    description = "A distributed Redis cache backend for Django",
    classifiers = [
        "Programming Language :: Python",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "Environment :: Web Environment",
        "Framework :: Django",
    ],
)
