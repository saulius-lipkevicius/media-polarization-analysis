import scrapy
import time
import random
from scrapy.selector import Selector
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select

class FoxSpider(scrapy.Spider):
    #  Spiders name to be called in terminal
    name = 'fox' 

    allowed_domains = ['www.foxnews.com']
    start_urls = ['https://www.foxnews.com']

    def __init__(self):
        chrome_options = Options()
        driver = webdriver.Chrome(executable_path=str('./chromedriver')
                                    , options=chrome_options)

        #  Determine an initial page, and keyword to look after
        driver.get("https://www.foxnews.com/search-results/search?q=Joe%20Biden")

        #  Find "By Content" button and select "Articles"
        driver.find_element_by_xpath(
            '//div[@class = "filter content"]//button[@class = "select"]'
            ).click()

        driver.find_element_by_xpath(
            '//div[@class = "filter content"]//label//input[@title="Article"]'
            ).click()

        #  Find "Date Range" from--to fields
        #  Start month
        driver.find_element_by_xpath(
            '//div[@class = "date min"]//div[@class = "sub month"]//button[@class="select"]'
            ).click()
        driver.find_element_by_id("01").click() 

        #  Start day
        driver.find_element_by_xpath(
            '//div[@class = "date min"]//div[@class = "sub day"]//button[@class="select"]'
            ).click()
        driver.find_element_by_xpath(
            '//div[@class = "date min"]//div[@class = "sub day"]//ul[@class="option"]//li[@class="01"]'
            ).click()

        #  Start year
        driver.find_element_by_xpath(
            '//div[@class = "date min"]//div[@class = "sub year"]//button[@class="select"]'
            ).click()
        driver.find_element_by_id("2016").click() 

        #  End month
        driver.find_element_by_xpath(
            '//div[@class = "date max"]//div[@class = "sub month"]//button[@class="select"]'
            ).click()
        driver.find_element_by_xpath(
            '//div[@class = "date max"]//div[@class = "sub month"]//ul[@class="option"]//li[@class="01"]'
            ).click()

        #  End day
        driver.find_element_by_xpath(
            '//div[@class = "date max"]//div[@class = "sub day"]//button[@class="select"]'
        ).click()
        driver.find_element_by_xpath(
            '//div[@class = "date max"]//div[@class = "sub day"]//ul[@class="option"]//li[@class="01"]'
            ).click()

        #  End year
        driver.find_element_by_xpath(
            '//div[@class = "date max"]//div[@class = "sub year"]//button[@class="select"]'
        ).click()
        driver.find_element_by_xpath(
            '//div[@class = "date max"]//div[@class = "sub year"]//ul[@class="option"]//li[@id="2017"]'
            ).click()

        #  Click "Search" icon
        select = driver.find_element_by_xpath('//div[@class = "button"]')
        select.click()

        #  Define wait time to act more like human and not to put on load on the page
        wait = WebDriverWait(driver, 10)

        #  Page ojnly shows 100 articles per search, hence only 9 "Show more" buttons
        i = 0
        while i < 9:
            try:
                time.sleep(3)

                #  Wait until page loads the button and then press it, if no BREAK
                element = wait.until(EC.visibility_of_element_located(
                    (By.XPATH, "(//div[@class='button load-more'])[1]/a")))
                element.click()
                i += 1
            except TimeoutException:
                break
            
            #  To not repeat actions in the same manners generate different waits
            time.sleep(random.randint(2, 7)) 
                
        #  Copy what is shown in page after all "Show more" buttons are pressed
        self.html = driver.page_source

    #  Parser, which gets separate articles data from the main source
    def parse(self, response):
        resp = Selector(text=self.html)

        #  Read every title in the html saved
        results = resp.xpath("//article[@class='article']//h2[@class='title']/a")

        for result in results:
            title = result.xpath(".//text()").get()
            link = result.xpath(".//@href").get()

            #  Read link which have to be scraped and send its title as metadate
            yield response.follow(url=link, callback=self.parse_article, meta={"title": title})

    def parse_article(self, response):
        title = response.request.meta['title']
        authors = response.xpath("(//div[@class='author-byline']//span/a)[1]/text()").getall()

        #  If there is no author look for higher level entity
        if len(authors) == 0:
            authors = [i for i in response.xpath("//div[@class='author-byline opinion']//span/a/text()").getall() if 'Fox News' not in i]

        #  Text is mostly separated by paragraphs, it must be joined
        content = ' '.join(response.xpath("//div[@class='article-body']//text()").getall())

        yield {
            "title": title,
            "author": ' '.join(authors),
            "time": response.xpath("//div[@class='article-date']/time/text()").get(),
            "content": content
        } 