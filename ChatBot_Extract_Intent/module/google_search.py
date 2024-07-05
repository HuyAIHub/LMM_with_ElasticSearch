from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time

service = Service(executable_path=r'./chrome-gg/chromedriver-linux64/chromedriver')
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=service, options=options)

def google_search(query):
    try:

        driver.get('https://www.google.com')

        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'q'))
        )
        search_box.send_keys(query)

        search_box.send_keys(Keys.RETURN)

        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.g'))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Extract search results
        search_results = []
        for g in soup.find_all('div', class_='g'):
            title = g.find('h3')
            link = g.find('a', href=True)
            if title and link:
                search_results.append({
                    'name': title.text,
                    'link': link['href']
                })

        return search_results

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        driver.quit()
        
def search_google(object, value=None, describe=None):
    t1 = time.time()
    search_query = f"tìm kiếm sản phẩm {object} bán chạy {value} {describe}"
    print('search_query', search_query)
    results = google_search(search_query)
    return results


# print(search_google('Điều hòa','5 triệu'))