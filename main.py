import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_binary  # Adds chromedriver binary to path
import requests
import uuid
import configargparse



class TopUpper:
    def __init__(self, args):
        self.vastai_username = args.vastai_username
        self.vastai_password = args.vastai_password
        self.bot_id = args.bot_id
        self.update_frequency = args.update_frequency
        self.send_balance_info = args.send_balance_info
        self.send_top_up_info = args.send_top_up_info
        self.top_up_amount = args.top_up_amount
        self.min_credit_amount = args.min_credit_amount
        self.chat_id = None
        if self.send_balance_info or self. send_top_up_info:
            self.chat_id = self.setup_bot()
        self.options = webdriver.ChromeOptions()

        user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/82.0.4103.61 Safari/537.36'   
        self.options.add_argument('user-agent={0}'.format(user_agent))
        self.options.add_argument("--headless")

        self.driver = webdriver.Chrome(chrome_options=self.options)
        self.driver.set_window_size(2560, 1440)

    def check_balance(self):
        self.driver.delete_all_cookies()
        self.driver.get("https://vast.ai/console/create/")
        WebDriverWait(self.driver, 300).until(
            EC.visibility_of_element_located((By.XPATH, '//*[text() = "Sign In"]')))
        self.driver.find_elements_by_xpath('//*[text() = "Sign In"]')[0].click()
        self.driver.find_elements_by_xpath('//a[text() = "Log In"]')[0].click()
        #self.driver.find_element_by_class_name("mui--is-untouched.mui--is-pristine.mui--is-empty")
        self.driver.find_elements_by_xpath('//input[@name = "username"]')[1].send_keys(self.vastai_username)
        self.driver.find_elements_by_xpath('//input[@name = "password"]')[1].send_keys(self.vastai_password)
        self.driver.find_element_by_xpath('//button[text() = "Log In & Go"]').click()
        WebDriverWait(self.driver, 300).until(
            lambda driver: float(driver.find_element_by_class_name('free-credit').text.split("$")[1]) != 0.0
        )

        credit_amount = float(self.driver.find_element_by_class_name('free-credit').text.split("$")[1])
        if credit_amount < self.min_credit_amount:
            self.driver.find_element_by_xpath('//a[text() = "Billing"]').click()
            WebDriverWait(self.driver, 300).until(
                EC.visibility_of_element_located((By.XPATH, '//button[text() = "Add Credit"]')))
            time.sleep(3)
            self.driver.find_element_by_xpath('//button[text() = "Add Credit"]').click()
            add_credit_input = self.driver.find_elements_by_xpath('//div[@class = "credit-amount-box"]/*[2]/*')[0]
            add_credit_input.click()
            for _ in range(100):
                if add_credit_input.get_attribute("value") != "":
                    add_credit_input.send_keys(Keys.BACK_SPACE)
                else:
                    break
            add_credit_input.send_keys(str(self.top_up_amount))
            WebDriverWait(self.driver, 300).until(
                EC.element_to_be_clickable((By.XPATH, '//button[text() = "Add Credit Once"]')))
            self.driver.find_element_by_xpath('//button[text() = "Add Credit Once"]').click()
            time.sleep(25)
            if self.send_top_up_info:
                requests.post(f"https://api.telegram.org/bot{self.bot_id}/sendMessage", params={'chat_id': self.chat_id, "text": "Your balance was topped up."})
                credit_amount += self.top_up_amount
        #driver.find_elements_by_xpath('//input[@name = "username"]')[0].location
        if self.send_balance_info:
            requests.post(f"https://api.telegram.org/bot{self.bot_id}/sendMessage", params={'chat_id': self.chat_id, "text": f"Your current balance is ${credit_amount}"})

    def setup_bot(self, rand_uuid=None):
        if rand_uuid == None:
            rand_uuid = uuid.uuid4()
            print(f"Send generated UUID to @VastAITopUp_bot. UUID:\n {rand_uuid}")
            print("Press Enter after sending")
            input()
        r = requests.get(f"https://api.telegram.org/bot{self.bot_id}/getUpdates")
        data = r.json()
        chat_id = None
        for val in data['result']:
            if val['message']['text'] == str(rand_uuid):
                chat_id = val['message']['chat']['id']
                break
        if chat_id == None:
            raise Exception("Cannot find chat id! Make sure you've sent generated UUID")
        requests.post(f"https://api.telegram.org/bot{self.bot_id}/sendMessage", params={'chat_id': chat_id, "text": f"Your bot is successfully added"})
        return chat_id

    def run_job(self):
        while True:
            self.check_balance()
            time.sleep(self.update_frequency * 60 * 60)


if __name__ == "__main__":
    parser = configargparse.ArgParser(config_file_parser_class=configargparse.YAMLConfigFileParser, default_config_files=['example_config.yaml'])
    parser.add_argument('--update_frequency', type=int, default=1.0,
                        help='Update frequency in hours')

    parser.add_argument('--top_up_amount', type=float, default=10.0)

    parser.add_argument('--min_credit_amount', type=float, default=50.0,
                    help='Min threshold when to top up.')

    parser.add_argument('--bot_id', type=str,
                        help='Telegram bot ID')

    parser.add_argument('--vastai_username', type=str)

    parser.add_argument('--vastai_password', type=str)
                    

    parser.add_argument('--send_balance_info', action="store_true",
                        help='Send balance info to telegram bot if not topped up')
    parser.add_argument('--send_top_up_info', action="store_true",
                    help='Send notification if balance is topped up')

    
    parser.add_argument('--sum', dest='accumulate', action='store_const',
                        const=sum, default=max,
                        help='sum the integers (default: find the max)')
    args = parser.parse_args()
    top_up = TopUpper(args)
    top_up.run_job()