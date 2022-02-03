import scrapy
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from scrapy.selector import Selector

class CnnSpider(scrapy.Spider):
    #  Spiders name to be called in terminal
    name = 'cnn'

    allowed_domains = ['edition.cnn.com']
    start_urls = ['https://edition.cnn.com']
    
    def __init__(self):
        chrome_options = Options()
        driver = webdriver.Chrome(executable_path=str('./chromedriver')
            , options=chrome_options)

        #  Link should be copied from the website, it is complex and error can accur
        driver.get("https://edition.cnn.com/search?q=Donald%20Trump&size=10&category=us,politics,world,opinion,health&type=article&sort=relevance")
        
        #  Create a wait function to imitate human-like behavour
        wait = WebDriverWait(driver, 10)

        #  Copy the first page html code
        self.html = [driver.page_source]
        
        # start turning pages (there will not be more than 1000 because of the error)
        i = 0
        while i < 1000:
            i += 1

            #  Button do not load up that fast
            next_btn = wait.until(EC.visibility_of_element_located(
                    (By.XPATH
                    , "(//div[@class='pagination-arrow pagination-arrow-right cnnSearchPageLink text-active'])")))
            next_btn.click()

            #  Append a new page html source to already obtained
            self.html.append(driver.page_source) # not the best way but will do

    def parse(self, response):
        #  Loop though pages in saved html list
        for page in self.html:

            #  Convert html to text
            resp = Selector(text=page)

            #  Put articles to a list for another loop
            results = resp.xpath("//div[@class='cnn-search__result cnn-search__result--article']/div/h3/a")

            for result in results:
                title = result.xpath(".//text()").get()

                # Avoid videos, COVID related news or ads
                if ("Video" in title) | ("coronavirus" in title) | ("http" in title):
                    continue 
                else:
                    #  Remove domain in the beginning of a link
                    link = result.xpath(".//@href").get()[13:]

                    #  Determine a link you want to scrape and send title as metadata
                    yield response.follow(url=link
                        , callback=self.parse_article
                        , meta={"title": title})

    # pass on the links to open and process actual news articles
    def parse_article(self, response):
        title = response.request.meta['title']
        
        # several variations of author's locator
        authors = response.xpath(
            "//span[@class='metadata__byline__author']//text()"
            ).getall()

        #  In case an article do not have an author find a higher entity(subtitle)
        if len(authors) == 0:
            authors = response.xpath(
                "//p[@data-type='byline-area']//text()"
                ).getall()
            if len(authors) == 0:
                authors = response.xpath(
                    "//div[@class='Article__subtitle']//text()"
                    ).getall()
        
        #  Connect separated texts and if it is None convert it to a blank line
        content = ' '.join(response.xpath(
            "//section[@id='body-text']/div[@class='l-container']//text()")
            .getall())

        if content is None:
            content = ' '

        yield {
            "title": title,
            "author": ' '.join(authors), # could be multiple authors
            "time": response.xpath("//p[@class='update-time']/text()").get(),
            "content": content
        }