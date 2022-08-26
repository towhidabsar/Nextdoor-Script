# Python Version 3.8.0
from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import pandas as pd
import re

import sys
import time
import csv

from lxml import html
import requests
import json

from dotenv import load_dotenv
import os


class NextDoorScraper():
	def __init__(self):
		load_dotenv()

		all_posts = []
		# Set up driver options
		capa = DesiredCapabilities.CHROME
		capa["pageLoadStrategy"] = "none"

		# Set up driver
		self.driver = webdriver.Chrome(desired_capabilities=capa, executable_path=os.getenv("chromedriver_path"))
		self.is_logged_in = False

	def login(self):
		self.driver.get("https://nextdoor.com/login/")
		# Log In
		time.sleep(2)
		username = self.driver.find_element(by=By.ID, value="id_email")
		password = self.driver.find_element(by=By.ID, value="id_password")

		username.send_keys(os.getenv("email")) # Retrieved from .env file
		password.send_keys(os.getenv("password")) # Retrieved from .env file

		self.driver.find_element(by=By.XPATH, value='//button[@id="signin_button"]').click()
		time.sleep(10) # if not scrolling in time, make this number larger
	
	def search(self, search_term):
		# Search for a specific term
		search = self.driver.find_element(by=By.XPATH, value='//input[@id="search-input-field"]')
		search.send_keys(search_term)
		search.send_keys(Keys.ENTER)
		time.sleep(5)
		self.driver.find_element(By.XPATH, value='.//a[@data-testid="tab-posts"]').click()
	
	def scroll(self, x):
		# Use Selenium to scroll 'range' number of times
		# Change the second number in 'range(x, y)' to determine how many times you want it to scroll down.
		for i in range(1, x):
		
			self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
			time.sleep(1)

			# Find all "previous comments and replies"

			number_of_posts = self.driver.find_elements(by=By.XPATH, value='.//div[@class="css-15luflj"]')
			print(number_of_posts)
			# Scroll to top to avoid "Unable to click element" error
			if (i == 1):
				self.driver.execute_script("window.scrollTo(0, 0);")
				# time.sleep(1)

		time.sleep(5)

	def get_tree(self):
		# Scrape the page source returned from Chrome driver for posts
		html_source = self.driver.page_source
		readable_html = html_source.encode('utf-8')
		tree = html.fromstring(readable_html)
		print(tree)
		# all_posts = tree.xpath('//a[@class="uUGmI2_t css-1q9s7yp"]/@href')
		return tree
	def posts(self, tree, filename):
		posts = pd.DataFrame()
		replies = pd.DataFrame()
		all_posts = tree.xpath('//a[@class="uUGmI2_t css-1q9s7yp"]/@href')
		for url in all_posts:
			self.driver.get(url)	
			time.sleep(10)
			html_source = self.driver.page_source
			readable_html = html_source.encode('utf-8')
			tree = html.fromstring(readable_html)
			author_path = tree.xpath('(.//a[@class="_3I7vNNNM E7NPJ3WK"]/text())[1]')
			location_path = tree.xpath('(.//span[@class="_1ji44zuk _1tG0eIs7"]/*[1]/text())[1]')
			title_path = './/*[@class="content-title-container"]/h5/text()[1]'

			category_path = tree.xpath('(.//div[@class="css-m9gd8r"]/span/text())[1]')
			date_path = tree.xpath('(.//span[@class="_1ji44zuk _1tG0eIs7"]/*[2]/text())[1]')
			post_content_path = tree.xpath('(.//p[@class="content-body"]//span[@class="Linkify"]/text())[1]')
			num_replies_path = tree.xpath('(.//span[@class="css-z5avht"]/text())[1]')
			reply_author_path = tree.xpath('.//a[@class="comment-detail-author-name"]/text()')
			reply_content_path = tree.xpath('.//div[@class="_2kP4d1Rw css-10em2lv"]/span/div/span/span/text()')
			cur_post = {
				'uid': url.split('/')[4],
				'author': author_path if len(author_path) > 0 else ['No Author'],
				'location': location_path if len(location_path) > 0 else ['No Location'],
				'category': category_path if len(category_path) > 0 else ['No Category'],
				'date': date_path if len(date_path) > 0 else ['No Date'],
				'content': post_content_path if len(post_content_path) else ['No Content'],
				'num_comments': num_replies_path if len(num_replies_path) else ['No Comments'],
				'url': url,
			}
			print(cur_post)
			posts = pd.concat([posts, pd.DataFrame(cur_post)])
			# reply_authors = tree.xpath(reply_author_path)
			# reply_contents = tree.xpath(reply_content_path)
			# print(replies)
			# replies = pd.concat([replies,
			# 	pd.DataFrame({
			# 		'url': url,
			# 		'reply_author': reply_authors,
			# 		'reply_content': reply_contents
			# 	})
			# ])
			posts.to_json(f'{filename}_posts.jsonl', orient='records', lines=True)
			# replies.to_json('replies.jsonl', orient='records', lines=True)
			time.sleep(2)
		self.driver.quit()

	def replies(self, search_term, folder=''):
		posts = pd.read_json(f'{folder}{search_term}_posts.jsonl', orient='records', lines=True)
		replies = pd.DataFrame()
		# /[A-Za-z0-9-_]*
		for url in posts['url']:
			print(re.split('/|\?', url))
			uid = re.split('/|\?', url)
			self.driver.get(url)
			time.sleep(5)
			view_all_comments = self.driver.find_elements(By.XPATH, value='.//button[contains(@class, "see-previous-comments-button-paged")]')
			for comment in view_all_comments:
				try:
					comment.click()
				except:
					pass
				time.sleep(2)
			
			tree = self.get_tree()
			reply_authors = tree.xpath('.//a[@class="comment-detail-author-name"]/text() | .//span[@class="comment-detail-author-name"]/text()')
			# reply_contents = self.driver.find_element(by=By.XPATH, value='.//div[@class="_2kP4d1Rw css-10em2lv"]/span/div/span/span/text()')
			reply_contents_div = self.driver.find_elements(by=By.XPATH, value='.//div[@class="_2kP4d1Rw css-10em2lv"]')

			reply_contents = []
			for a in reply_contents_div:
				# try:
				# print('text',a.get_attribute('innerText'))
				reply_contents.append(a.get_attribute('innerText'))
				# except:
				# 	print('a', a)
				# 	pass
				# reply_contents.append(a.get_attribute('innerText'))				
			print("authors", len(reply_authors))
			print("contents", len(reply_contents))
			print("authors", reply_authors)
			print("contents", reply_contents)
			replies = pd.concat([replies, pd.DataFrame({
				'uid': [uid for i in range(len(reply_contents))],
				'reply_author': reply_authors if len(reply_authors) > 0 else [None for i in range(len(reply_contents))],
				'reply_content': reply_contents if len(reply_contents) > 0 else [None for i in range(len(reply_authors))]
			})])
		replies.to_json(f'{folder}{search_term}_replies.jsonl', orient='records', lines=True)
		self.driver.quit()


def parse_all():
# Load ability to use .env
	load_dotenv()

	# Set up driver options
	capa = DesiredCapabilities.CHROME
	capa["pageLoadStrategy"] = "none"

	# Set up driver
	driver = webdriver.Chrome(desired_capabilities=capa, executable_path=os.getenv("chromedriver_path"))
	driver.get("https://nextdoor.com/login/")

	time.sleep(10)


	# Log In
	username = driver.find_element(by=By.ID, value="id_email")
	password = driver.find_element(by=By.ID, value="id_password")

	username.send_keys(os.getenv("email")) # Retrieved from .env file
	password.send_keys(os.getenv("password")) # Retrieved from .env file

	driver.find_element(by=By.XPATH, value='//button[@id="signin_button"]').click()
	time.sleep(10) # if not scrolling in time, make this number larger

	# Search for a specific term
	search = driver.find_element(by=By.XPATH, value='//button[@id="signin_button"]')
	search.send_keys("")
	# Click the pop up, if one appears
	try:
		driver.find_element(By.XPATH, value="//button[@class='channels-bulk-join-close-button']").click()
	except:
		pass

	# Use Selenium to scroll 'range' number of times
	# Change the second number in 'range(x, y)' to determine how many times you want it to scroll down.
	for i in range(1, 2):
		
		driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
		time.sleep(1)

		# Find all "previous comments and replies"

		numberOfElementsFound = driver.find_elements(by=By.XPATH, value='//button[contains(@class, "see-previous-comments-button-paged")]')
		
		# print(numberOfElementsFound)
		# numberOfElementsFound = driver.find_elements_by_xpath('//button[contains(@class, "see-previous-comments-button-paged")]')
		# print(numberOfElementsFound)
		# Scroll to top to avoid "Unable to click element" error
		if (i == 1):
			driver.execute_script("window.scrollTo(0, 0);")
			# time.sleep(1)

		# Click all "view all replies" found previously to prepare to scrape the replies
		for pos in range (0, len(numberOfElementsFound)):
			if (numberOfElementsFound[pos].is_displayed()):
				try:
					# time.sleep(1.5) 
					driver.execute_script("arguments[0].click();", numberOfElementsFound[pos])
				except Exception:
					pass

		# Click on "see more" to view full reply
		numberOfElementsFound = driver.find_elements(by=By.XPATH, value='//a[@class="truncate-view-more-link"]')
		# numberOfElementsFound = driver.find_elements_by_xpath('//a[@class="truncate-view-more-link"]')
		for pos in range (0, len(numberOfElementsFound)):
			if (numberOfElementsFound[pos].is_displayed()):
				try:
					# time.sleep(1) 
					driver.execute_script("arguments[0].click();", numberOfElementsFound[pos])
				except:
					pass

	time.sleep(1)

	# Scrape the page source returned from Chrome driver for posts
	html_source = driver.page_source
	readable_html = html_source.encode('utf-8')
	tree = html.fromstring(readable_html)
	postNodes = tree.xpath('//div[@class="css-15wtqd7"]')
	print("postNodes")
	print(postNodes)
	# Iterate over each post node that has an author to get data in an organized fashion

	# author_path = './/div[@class="avatar-toggle-node"]/a/text()'
	author_path = './/a[@class="_3I7vNNNM E7NPJ3WK"]/text()'
	# driver.execute_script("arguments[0].setAttribute('style', arguments[1]);", author_path, "background: yellow; border: 2px solid red;")
	# location_path = './/span/*[contains(@class, "post-byline-cursor")]/text()'
	location_path = './/span[@class="_1ji44zuk _1tG0eIs7"]/*[1]/text()'
	title_path = './/*[@class="content-title-container"]/h5/text()'

	category_path = './/div[@class="css-m9gd8r"]/span/text()'
	date_path = './/span[@class="_1ji44zuk _1tG0eIs7"]/*[2]/text()'
	post_content_path = './/p[@class="content-body"]//span[@class="Linkify"]/text()'
	num_replies_path = './/span[@class="css-z5avht"]/text()'
	reply_author_path = './/a[@class="comment-detail-author-name"]/text()'
	reply_content_path = './/div[@class="_2kP4d1Rw css-10em2lv"]/span/div/span/span/text()'
	for post in postNodes:
		print("Author:")
		print(post.xpath(author_path))

	posts = [(post.xpath(author_path),
			post.xpath(location_path),
			post.xpath(title_path),
			post.xpath(category_path),
			post.xpath(date_path),
			post.xpath(post_content_path),
			post.xpath(num_replies_path),
			post.xpath(reply_author_path),
			post.xpath(reply_content_path),
			post) for post in postNodes if post.xpath(author_path) != []]
	print("Posts")
	print(posts)
	# Create CSV Writer for first document (Posts)
	ofile  = open('posts.csv', "w")
	writer = csv.writer(ofile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)

	# Create CSV Writer for second document (Replies)
	rfile = open('replies.csv', "w")
	rWriter = csv.writer(rfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
	post_counter = 1

	# Output to csv files
	for post in posts:
		# Posts
		author = post[0][0].encode('utf8').decode('utf8')

		location = "Unlisted"
		try:
			location = post[1][0].encode('utf8').decode('utf8')
		except:
			pass

		title = "No Title"
		try:
			title = post[2][0].encode('utf8').decode('utf8')
		except:
			pass

		category = "No Category"
		category_list = ""

		try:
			category = post[3][0].encode('utf8').decode('utf8')
		except:
			category_list = post[9].xpath('.//span[@class="content-scope-line-hood-link js-scope-line-hoods"]/text()')
			try:
				category = category_list[0]
			except:
				pass
		
		date = "No Date"
		try:
			date = post[4][0].encode('utf8').decode('utf8')
		except:
			pass

		content = "No Content"
		try:
			content = post[5][0].encode('utf8').decode('utf8')
		except:
			pass
		
		numReplies = 0
		try:
			numReplies = post[6][0].encode('utf8').decode('utf8')
		except:
			pass

		writer.writerow([author, location, title, category, date, content, numReplies])

		# Replies
		# Iterate through all replies with an author (post[7])
		for count in range(0, len(post[7])):
			try:
				name = post[7][count].encode('utf-8').decode('utf8')
			except Exception:
				pass

			try:
				reply = post[8][count].encode('utf-8').decode('utf8')
			except Exception:
				pass

			rWriter.writerow([post_counter, name, reply])

		post_counter += 1

	driver.quit()


# def parse_replies(json_posts, file=True):
# 	posts = pd.read_json(json_posts, orient='records', lines=True) if (file) else json_posts
# 	# /[A-Za-z0-9-_]*
# 	for url in posts['url']:
# 		# print(url.split('/')[4])
# 		driver

# parse_replies('homeless_posts.jsonl')
nd = NextDoorScraper()
nd.login()
nd.replies('homeless')
nd.replies('homeless_shelter')
nd.driver.quit()