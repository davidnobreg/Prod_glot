import os

from pathlib import Path

from datetime import timedelta

# from prettyconf import Configuration

from decouple import Config, Csv, RepositoryEnv

from kombu import Queue



from core.env import get_env



# Ambiente

DJANGO_ENV = os.getenv("DJANGO_ENV", "development")

IS_PRODUCTION = DJANGO_ENV == "production"

INSTANCIA = get_env("EVOLUTION_INSTANCE", required=True)

N8N_URL = get_env("N8N_WEBHOOK_URL", required=True)

N8N_INSTANCIA = get_env("N8N_INSTANCIA", default="default")

# --- Caminhos bÃƒÂ¡sicos ---

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_PATH = BASE_DIR / 'configuration' / '.env'



# Carrega variÃƒÂ¡veis do .env

config = Config(repository=RepositoryEnv(ENV_PATH))



# Carrega o arquivo .env desta pasta

# config= Config(RepositoryEnv(ENV_PATH))

# config_host = Configuration()



# --- SeguranÃƒÂ§a ---

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', cast=bool, default=False)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default=[])

CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv(), default=[])



# --- Templates ---

TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')



# --- Tempo de Reserva para lote bloqueados ---

TEMPO_RESERVA_MINUTOS = 10



# Application definition



DEFAULT_APPS = [

    'jazzmin',

    'rest_framework',

    'django.contrib.admin',

    'django.contrib.auth',

    'django.contrib.contenttypes',

    'django.contrib.sessions',

    'django.contrib.messages',

    'django.contrib.staticfiles',

    'django_extensions',

    'django.contrib.humanize',



]



THIRD_APPS = [

    'rolepermissions',

    # 'django_crontab',

    # 'django_q',

    'django_celery_results',

    'django_celery_beat',

    'django_filters',

    'ckeditor',



]



PROJECT_APPS = [

    'accounts',

    'base',

    'clientes',

    'documentos',

    'dashboard',

    'empreendimentos',

    'mensagem',

    'vendas',



]



INSTALLED_APPS = PROJECT_APPS + THIRD_APPS + DEFAULT_APPS



"""REST_FRAMEWORK = {

    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend']

}"""



# URL base da Evolution API (ajuste conforme o seu servidor)

EVOLUTION_URL = config("EVOLUTION_API_URL")

EVOLUTION_INSTANCE = config("EVOLUTION_INSTANCE")

EVOLUTION_TOKEN = config("EVOLUTION_TOKEN")



if IS_PRODUCTION:
	STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
else:
	STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'



MIDDLEWARE = [

    'django.middleware.security.SecurityMiddleware',

    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',

]



# SessÃƒÂ£o expira em 15 minutos (900 segundos)

SESSION_COOKIE_AGE = 15 * 60

SESSION_EXPIRE_AT_BROWSER_CLOSE = False

SESSION_SAVE_EVERY_REQUEST = True



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

# Banco unico: PostgreSQL (credenciais via .env). DEBUG nao altera o banco.



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



TIME_ZONE = 'America/Sao_Paulo'  # Ajuste conforme necessÃƒÂ¡rio



USE_TZ = True  # Habilita o uso de fuso horÃƒÂ¡rio



USE_I18N = True



USE_L10N = True



USE_THOUSAND_SEPARATOR = True



LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)



# English default

# LANGUAGES = DJANGO_LANGUAGES



# Static files (CSS, JavaScript, Images)

# https://docs.djangoproject.com/en/5.1/howto/static-files/



# URLs para navegador

STATIC_URL = '/static/'

MEDIA_URL = '/media/'



# Caminhos fÃƒÂ­sicos

STATIC_ROOT = os.path.join(BASE_DIR, 'static')  # usado pelo collectstatic

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # usado para uploads



# --- Backblaze B2 / S3-compatible storage ---

USE_REMOTE_STORAGE = config('USE_REMOTE_STORAGE', cast=bool, default=False)

if USE_REMOTE_STORAGE:
	AWS_ACCESS_KEY_ID = config('B2_KEY_ID')
	AWS_SECRET_ACCESS_KEY = config('B2_APPLICATION_KEY')
	AWS_STORAGE_BUCKET_NAME = config('B2_BUCKET_NAME')
	AWS_S3_ENDPOINT_URL = config('B2_ENDPOINT_URL')
	AWS_S3_REGION_NAME = config('B2_REGION')
	AWS_DEFAULT_ACL = 'private'
	AWS_S3_FILE_OVERWRITE = False
	AWS_QUERYSTRING_AUTH = True
	AWS_QUERYSTRING_EXPIRE = 3600

	_staticfiles_backend = (
		'whitenoise.storage.CompressedManifestStaticFilesStorage'
		if IS_PRODUCTION
		else 'django.contrib.staticfiles.storage.StaticFilesStorage'
	)
	STORAGES = {
		'default': {
			'BACKEND': 'storages.backends.s3.S3Storage',
		},
		'staticfiles': {
			'BACKEND': _staticfiles_backend,
		},
	}
	MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"



# Opcional: desenvolvimento

# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'base/static')] # onde seus apps guardam static]





# Default primary key field type

# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field



DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



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





# ==========================================================
# Celery - RabbitMQ broker + Redis result backend
# ==========================================================

rabbitmq_user = config("RABBITMQ_USER")
rabbitmq_password = config("RABBITMQ_PASSWD")
rabbitmq_host = config("RABBITMQ_HOST")
rabbitmq_port = config("RABBITMQ_PORT")
rabbitmq_vhost = config("RABBITMQ_VHOST")

CELERY_BROKER_URL = os.getenv(
	"CELERY_BROKER",
	f"amqp://{rabbitmq_user}:{rabbitmq_password}@{rabbitmq_host}:{rabbitmq_port}/{rabbitmq_vhost}",
)

# Redis
redis_host = config("REDIS_HOST", default="redis")
redis_port = config("REDIS_PORT", default="6379")
redis_password = config("REDIS_PASSWORD", default="")
redis_db_result = config("REDIS_DB_RESULT", default="0")
redis_db_cache = config("REDIS_DB_CACHE", default="1")


if redis_password:
    REDIS_BASE_URL = f"redis://:{redis_password}@{redis_host}:{redis_port}"
else:
    REDIS_BASE_URL = f"redis://{redis_host}:{redis_port}"


CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    f"{REDIS_BASE_URL}/{redis_db_result}",
)

CACHE_REDIS_URI = os.getenv(
    "CACHE_REDIS_URI",
    f"{REDIS_BASE_URL}/{redis_db_cache}",
)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Sao_Paulo"

CELERY_WORKER_POOL = "solo"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"
CELERY_TASK_DEFAULT_QUEUE = "empreendimentos"
CELERY_TASK_QUEUES = (
	Queue("empreendimentos"),
	Queue("mensagens"),
)

FLOWER_BASIC_AUTH = ["admin:admin"]



LOG_DIR = BASE_DIR / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)



# django setting.

CACHES = {

    'default': {

        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',

        'LOCATION': 'my_cache_table',

    }

}



LOGGING = {

    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {

        "default": {

            "format": "[{asctime}] {levelname} {name}: {message}",

            "style": "{",

        },

    },

    "handlers": {

        "console": {

            "class": "logging.StreamHandler",

            "formatter": "default",

        },

    },

    "loggers": {

        "django": {

            "handlers": ["console"],

            "level": "INFO",

        },

        "celery": {

            "handlers": ["console"],

            "level": "INFO",

            "propagate": False,

        },

    },

}



# Ã°Å¸â€â€ž SOMENTE NO WINDOWS / DEV ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ adiciona arquivo

if not IS_PRODUCTION:

    LOG_DIR = BASE_DIR / "logs"

    LOG_DIR.mkdir(exist_ok=True)



    LOGGING["handlers"]["file"] = {

        "class": "logging.FileHandler",

        "filename": LOG_DIR / "celery.log",

        "formatter": "default",

    }



    LOGGING["loggers"]["celery"]["handlers"].append("file")

    LOGGING["loggers"]["django"]["handlers"].append("file")



JAZZMIN_SETTINGS = {

    # title of the window (Will default to current_admin_site.site_title if absent or None)

    "site_title": "Glot Admin",



    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)

    "site_header": "Carlos_&_Celso",



    # Title on the brand (19 chars max) (defaults to current_admin_site.site_header if absent or None)

    "site_brand": "Carlos_&_Celso",



    # Logo to use for your site, must be present in static files, used for brand on top left

    "site_logo": "books/img/logo.jpg",

    "site_logo_classes": "img-fluid",  # classes extras da logo

    "site_logo_width": 200,  # opcional



    # Logo to use for your site, must be present in static files, used for login form logo (defaults to site_logo)

    "login_logo": None,



    # Logo to use for login form in dark themes (defaults to login_logo)

    "login_logo_dark": None,



    # CSS classes that are applied to the logo above

    "site_logo_classes": "img-circle",



    # Relative path to a favicon for your site, will default to site_logo if absent (ideally 32x32 px)

    "site_icon": None,



    # Welcome text on the login screen

    "welcome_sign": "Seja Bem-vindo",



    # Copyright on the footer

    "copyright": "",



    # List of model admins to search from the search bar, search bar omitted if excluded

    # If you want to use a single search field you dont need to use a list, you can use a simple string

    # "search_model": ["auth.User", "auth.Group"],



    # Field name on user model that contains avatar ImageField/URLField/Charfield or a callable that receives the user

    "user_avatar": None,



    ############

    # Top Menu #

    ############



    # Links to put along the top menu

    "topmenu_links": [



        # Url that gets reversed (Permissions can be added)

        # {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},



        # external url that opens in a new window (Permissions can be added)

        # {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},



        # model admin to link to (Permissions checked against model)

        # {"model": "auth.User"},



        # App with dropdown menu to all its models pages (Permissions checked against models)

        # {"app": "books"},

    ],



    #############

    # User Menu #

    #############



    # Additional links to include in the user menu on the top right ("app" url type is not allowed)

    "usermenu_links": [

        {"name": "Support", "url": "https://github.com/farridav/django-jazzmin/issues", "new_window": True},

        {"model": "auth.user"}

    ],



    #############

    # Side Menu #

    #############



    # Whether to display the side menu

    "show_sidebar": True,



    # Whether to aut expand the menu

    "navigation_expanded": False,



    # Hide these apps when generating side menu e.g (auth)

    "hide_apps": [],



    # Hide these models when generating side menu (e.g auth.user)

    "hide_models": [],



    # List of apps (and/or models) to base side menu ordering off of (does not need to contain all apps/models)

    "order_with_respect_to": ["auth", "books", "books.author", "books.book"],



    # Custom links to append to app groups, keyed on app name

    "custom_links": {

        "books": [{

            "name": "Make Messages",

            "url": "/admin/",

            "icon": "fas fa-comments",

            "permissions": ["books.view_book"]

        }]

    },



    # Custom icons for side menu apps/models See https://fontawesome.com/icons?d=gallery&m=free&v=5.0.0,5.0.1,5.0.10,5.0.11,5.0.12,5.0.13,5.0.2,5.0.3,5.0.4,5.0.5,5.0.6,5.0.7,5.0.8,5.0.9,5.1.0,5.1.1,5.2.0,5.3.0,5.3.1,5.4.0,5.4.1,5.4.2,5.13.0,5.12.0,5.11.2,5.11.1,5.10.0,5.9.0,5.8.2,5.8.1,5.7.2,5.7.1,5.7.0,5.6.3,5.5.0,5.4.2

    # for the full list of 5.13.0 free icon classes

    "icons": {

        "auth": "fas fa-users-cog",

        "auth.user": "fas fa-user",

        "auth.Group": "fas fa-users",

        "Accounts": "fa-solid fa-user",

        "Clientes": "fa-solid fa-pen-nib",

        "Empreendimentos": "fa-solid fa-square-poll-vertical",

        "Vendas": "fa-solid fa-pencil",

    },

    # Icons that are used when one is not manually specified

    "default_icon_parents": "fas fa-chevron-circle-right",

    "default_icon_children": "fas fa-circle",



    #################

    # Related Modal #

    #################

    # Use modals instead of popups

    "related_modal_active": False,



    #############

    # UI Tweaks #

    #############

    # Relative paths to custom CSS/JS scripts (must be present in static files)

    "custom_css": None,

    "custom_js": None,

    # Whether to link font from fonts.googleapis.com (use custom_css to supply font otherwise)

    "use_google_fonts_cdn": True,

    # Whether to show the UI customizer on the sidebar

    "show_ui_builder": True,



    ###############

    # Change view #

    ###############

    # Render out the change view as a single form, or in tabs, current options are

    # - single

    # - horizontal_tabs (default)

    # - vertical_tabs

    # - collapsible

    # - carousel

    "changeform_format": "vertical_tabs",

    # override change forms on a per modeladmin basis

    "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs"},

    # Add a language dropdown into the admin

    "language_chooser": False,

}

# ===================================
# Sentry Ã¢â‚¬â€ Monitoramento de erros
# Adicionar no settings.py de produÃƒÂ§ÃƒÂ£o
# ===================================


SENTRY_DSN = config("SENTRY_DSN", default="")


if SENTRY_DSN:
    from core.sentry import init_sentry
    init_sentry(
        dsn=SENTRY_DSN,
        environment=os.environ.get("ENVIRONMENT", "production"),
        release=os.environ.get("GIT_COMMIT", None),
    )
