from Config.config import get_env_config
from TestBase.webDriverSetup import create_driver


def main():
    env_config = get_env_config('stage')
    driver = create_driver()
    driver.get(env_config['base_url'])
    print(f"Opened: {driver.current_url}")
    driver.quit()


if __name__ == '__main__':
    main()
