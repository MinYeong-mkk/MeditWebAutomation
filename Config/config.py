import os
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENTS = {
    'dev': {
        'base_url': 'https://dev-www.meditlink.com',
        'email': os.getenv('DEV_EMAIL', ''),
        'password': os.getenv('DEV_PASSWORD', ''),
    },
    'stage': {
        'base_url': 'https://stage-www.meditlink.com',
        'email': os.getenv('STAGE_EMAIL', ''),
        'password': os.getenv('STAGE_PASSWORD', ''),
    },
    'oper': {
        'base_url': 'https://www.meditlink.com',
        'email': os.getenv('OPER_EMAIL', ''),
        'password': os.getenv('OPER_PASSWORD', ''),
    },
}

BROWSER = os.getenv('BROWSER', 'chrome')
HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true'
LOGIN_PATH = '/login'
DEFAULT_TIMEOUT = 10


def get_env_config(env_name: str) -> dict:
    if env_name not in ENVIRONMENTS:
        raise ValueError(f'Unsupported env: {env_name}')

    return ENVIRONMENTS[env_name]
