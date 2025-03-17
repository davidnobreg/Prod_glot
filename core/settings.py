import os
from pathlib import Path
from datetime import timedelta

from prettyconf import Configuration
from decouple import config

config_host = Configuration()

BASE_DIR = Path(__file__).resolve().parent.parent

TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

STATIC_DIR = os.path.join(BASE_DIR, 'static')

MEDIA_DIR = os.path.join(BASE_DIR, 'media')

SECRET_KEY = config('SECRET_KEY')

DEBUG = config_host('DEBUG', default=False, cast=config_host.boolean)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=config_host.list)

# Application definition

DEFAULT_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    #'django_celery_beat',
]

THIRD_APPS = [
    'base',
    'rolepermissions',
]

PROJECT_APPS = [
    'clientes',
    'empreendimentos',
    'vendas',
    'accounts',

]

INSTALLED_APPS = PROJECT_APPS + THIRD_APPS + DEFAULT_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases


if DEBUG:
    DATABASES = {
        'default': {
           'ENGINE': 'django.db.backends.sqlite3',
          'NAME': BASE_DIR / "db.sqlite3",
        }
    }

else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT')
        }
    }

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'base/static')

STATIC_URL = 'base/static/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'base/static/media')

MEDIA_URL = 'static/media/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

# --- Messages --- #
from django.contrib.messages import constants

MESSAGE_TAGS = {
    constants.ERROR: 'alert-danger',
    constants.WARNING: 'alert-warning',
    constants.DEBUG: 'alert-danger',
    constants.SUCCESS: 'alert-success',
    constants.INFO: 'alert-info',
}

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/empreendimentos/'
LOGOUT_URL = 'logout'

AUTH_USER_MODEL = "accounts.User"

# Role permissions
ROLEPERMISSIONS_MODULE = 'core.roles'

# CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

# CRISPY_TEMPLATE_PACK = "bootstrap5"

CELERY_BROKER_URL = os.getenv('CELERY_BROKER',
                              f'amqp://{config('RABBITMQ_USER')}:{config('RABBITMQ_PASSWD')}@rabbitmq:5672/')
CELERY_RESULT_BACKEND = os.getenv('CELERY_BACKEND', 'rpc://')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
