import threading as td
from concurrent.futures import ThreadPoolExecutor
import requests
import random
from lxml import html
import time
from typing import List, Dict, Optional, Any, Tuple
import os
from datetime import datetime, timedelta
import sqlite3
import dotenv
from google import genai
import discord
import asyncio

# Load environment variables
dotenv.load_dotenv()

class CNNCrawler:
    def __init__(self):
        
        # List of user agents to rotate through
        self.user_agents: List[str] = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
        ]
        
        # List of proxies to rotate through
        self.proxies: List[str] = [
            # You can add proxies here
        ]
        
        # Base URL for CNN Lite
        self.base_url = "https://lite.cnn.com"
        
        # Database file
        self.db_file = "cnn_news.db"
        
        # Initialize database
        self.setup_database()
    
    def setup_database(self) -> None:
        """Set up the SQLite database and create tables if they don't exist."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Create articles table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            time TIMESTAMP,
            content TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"Database setup complete: {self.db_file}")
    
    def get_random_user_agent(self) -> Optional[str]:
        """Return a random user agent from the list or None if list is empty."""
        if not self.user_agents:
            return None
        return random.choice(self.user_agents)
    
    def get_random_proxy(self) -> Optional[str]:
        """Return a random proxy from the list or None if list is empty."""
        if not self.proxies:
            return None
        return random.choice(self.proxies)
    
    def get_request_headers(self) -> Dict[str, str]:
        """Generate request headers with a random user agent if available."""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        user_agent = self.get_random_user_agent()
        headers['User-Agent'] = user_agent

        return headers
    
    def make_request(self, url: str) -> Optional[requests.Response]:
        """Make an HTTP request with random user agent and proxy if available."""
        headers = self.get_request_headers()
        proxy = self.get_random_proxy()
        
        proxies = None
        if proxy:
            proxies = {
                'http': proxy,
                'https': proxy
            }
        
        try:
            response = requests.get(
                url, 
                headers=headers, 
                proxies=proxies, 
                timeout=30
            )
            response.raise_for_status()
            return response
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def get_article_urls_and_titles(self) -> List[Tuple[str, str]]:
        """Extract article URLs and titles from the CNN Lite homepage."""
        response = self.make_request(self.base_url)
        if not response:
            return []
        
        tree = html.fromstring(response.text)
        
        # Based on the HTML structure, articles are in <li class="card--lite"> elements
        article_elements = tree.xpath('//li[@class="card--lite"]')
        
        articles = []
        for element in article_elements:
            # Extract the URL
            link_elements = element.xpath('./a/@href')
            if not link_elements:
                continue
            
            relative_url = link_elements[0]
            full_url = f"{self.base_url}{relative_url}"
            
            # Extract the title from inside the <a> tag
            title_elements = element.xpath('./a/text()')
            title = title_elements[0].strip() if title_elements else "Unknown Title"
            
            articles.append((full_url, title))
        
        # Reverse the list of articles so newest are last
        articles.reverse()
        
        return articles
    
    def title_exists_in_db(self, title: str) -> bool:
        """Check if an article with the given title already exists in the database."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM articles WHERE title = ?", (title,))
        count = cursor.fetchone()[0]
        
        conn.close()
        
        return count > 0
    
    def parse_article(self, url: str, title: str) -> Optional[Dict[str, Any]]:
        """Parse an article page to extract title, time, and content."""
        response = self.make_request(url)
        if not response:
            return None
        
        tree = html.fromstring(response.text)
        
        try:
            # Extract time - CNN Lite uses p.timestamp--lite for time
            article_time = None
            time_elements = tree.xpath('//p[@class="timestamp--lite"]')
            if time_elements:
                time_text = time_elements[0].text_content().strip()
                # Extract time from format like "Updated: 5:39 PM EST, Mon March 3, 2025"
                try:
                    # Remove "Updated:" and parse the rest
                    time_str = time_text.replace("Updated:", "").strip()
                    # Parse into datetime object
                    article_time = datetime.strptime(time_str, "%I:%M %p EST, %a %B %d, %Y")
                except Exception as e:
                    print(f"Error parsing time {time_text}: {e}")
            
            # Extract content paragraphs - CNN Lite uses p.paragraph--lite for content
            content_paragraphs = []
            
            # First try the specific CNN Lite paragraph class
            paragraphs = tree.xpath('//p[@class="paragraph--lite"]')
            for p in paragraphs:
                # Get all text including text from child elements like <em> or <a>
                if p.text_content():
                    content_paragraphs.append(p.text_content().strip())
            
            # Join paragraphs with spaces
            content = '\n'.join([p for p in content_paragraphs if p])
            
            return {
                "title": title,
                "url": url,
                "time": article_time,
                "content": content
            }
        except Exception as e:
            print(f"Error parsing article {url}: {e}")
            return None
    
    def save_article_to_db(self, article: Dict[str, Any]) -> None:
        """Save an article to the SQLite database."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Convert datetime to string if it's a datetime object
        article_time = article["time"]
        if isinstance(article_time, datetime):
            article_time = article_time.isoformat()
        
        try:
            cursor.execute(
                "INSERT INTO articles (title, url, time, content) VALUES (?, ?, ?, ?)",
                (article["title"], article["url"], article_time, article["content"])
            )
            conn.commit()
            print(f"Article saved to database: {article['title']}")
        except sqlite3.IntegrityError as e:
            print(f"Article already exists in database: {article['title']}")
        finally:
            conn.close()
    
    def crawl(self) -> int:
        """Crawl CNN Lite website and save articles to SQLite database."""
        print("Starting CNN Lite crawler...")
        
        # Get article URLs and titles from homepage
        article_data = self.get_article_urls_and_titles()
        print(f"Found {len(article_data)} articles to crawl")
        
        # Parse each article
        articles_saved = 0
        for i, (url, title) in enumerate(article_data):            
            # Skip if title already exists in database
            if self.title_exists_in_db(title):
                continue
            
            article_item = self.parse_article(url, title)
            if article_item:
                self.save_article_to_db(article_item)
                articles_saved += 1
            
            # Add a small delay to avoid overloading the server
            time.sleep(random.uniform(1, 3))
        
        return articles_saved
    
    def get_articles_by_number(self, number: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve articles from the database ordered by time.
        
        Args:
            number: Maximum number of articles to return. If None, returns all articles.
        
        Returns:
            List of article dictionaries ordered by time (newest first).
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        query = "SELECT title, time, content FROM articles ORDER BY time DESC"
        
        if number is not None and isinstance(number, int) and number > 0:
            query += f" LIMIT {number}"
        
        cursor.execute(query)
        
        articles = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return articles
    
    def get_articles_by_time(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Retrieve articles from the database after the specified time.
        
        Args:
            cutoff_time: Datetime object specifying the cutoff time
            
        Returns:
            List of article dictionaries published after the specified time, ordered by time (newest first).
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        query = "SELECT title, time, content FROM articles WHERE time > ? ORDER BY time DESC"
        cursor.execute(query, (cutoff_time,))
        
        articles = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return articles

class GeminiAnalyzer:
    def __init__(self):
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def analyze(self, articles: List[Dict[str, Any]]) -> str:
        """Analyze article content using Google's Gemini AI.
        
        Args:
            articles: List of article dictionaries containing title and content
            
        Returns:
            Analysis text from Gemini
        """
        
        try:
            # Prepare the prompt
            prompt = f"""
            Read the news articles and analyze them.
            If there are articles that are related to president's policies, US policies, US foreign policies, wars, economics, banks, stock market, big companies like Apple, Google, Amazon, Microsoft, Nvidia, Tesla, Microsoft, or any other topics that are related to those, please give a summary of the article.
            For those articles, if they are related to US bonds or treasury yield, tell me if the bond price and the treasury yield of short term, medium term, and long term are going up or down based on the articles.
            If there are articles that are related to the stock market, tell me if the mentioned stock price is going up or down based on the articles.
            If there are articles that are related to the US dollar, tell me if the US dollar index is going up or down based on the articles.
            When you give the summary, put the time published in the summary. Skip the articles that are not related to the above topics.

            Analyze the following news articles:
            
            {articles}
            
            用中文回答
            """
            
            # Generate the response
            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt
            )
            
            return response.text
        
        except Exception as e:
            return f"Error analyzing with Gemini: {str(e)}"

class BackgroundDiscordClient(discord.Client):
    def __init__(self, token, *args, **kwargs):
        super().__init__(*args, intents=discord.Intents.default(), **kwargs)
        self._loop = asyncio.new_event_loop()
        td.Thread(target=self._start_loop, daemon=True).start()
        self._executor = ThreadPoolExecutor(max_workers=1)

        asyncio.run_coroutine_threadsafe(self.start(token), self._loop)

    def _start_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def stop_async(self):
        asyncio.run_coroutine_threadsafe(self.close(), self._loop)
        self._loop.stop()

    def send_message_sync(self, channel_id, content):
        def _send_message_task(channel_id, content):
            async def _send():
                channel = self.get_channel(channel_id)
                if channel:
                    for chunk in content.split('\n'):
                        if chunk:
                            await channel.send(chunk)
                            await asyncio.sleep(2)
                else:
                    print(f"Channel with ID {channel_id} not found.")

            return asyncio.run_coroutine_threadsafe(_send(), self.loop).result()

        return self._executor.submit(_send_message_task, channel_id, content).result()

class NewsProcessor:
    def __init__(self):
        self.cnn_crawler = CNNCrawler()
        self.gemini_analyzer = GeminiAnalyzer()
        self.discord_client = BackgroundDiscordClient(os.getenv('DISCORD_TOKEN'))

    def process_articles(self, articles: List[Dict[str, Any]]):
        """Process the articles with Gemini analysis and send to Discord.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Number of articles successfully processed
        """
        
        if not articles:
            print("No article to process")
            return 0
        
        print(f"Retrieved {len(articles)} articles for analysis")
        
        # Analyze articles in batches of 5
        for i in range(0, len(articles), 5):
            analysis = self.gemini_analyzer.analyze(articles[i:i+5])
        
            # Send to Discord
            now = datetime.now()
            time_info = f"Hourly message sent at {now.strftime('%H:%M:%S')}\n\n"
            self.discord_client.send_message_sync(int(os.getenv('DISCORD_CHANNEL')), time_info + analysis)
            print(f"Processed {len(articles[i:i+5])} articles")
    
    def process_articles_by_time(self, hours: int = 1):
        """Process the latest articles with Gemini analysis and send to Discord.
        
        Args:
            hours: Number of hours to process
            
        Returns:
            Number of articles successfully processed
        """

        if hours <= 0:
            return
        
        # Get the latest articles
        cutoff_time = datetime.now() - timedelta(hours=hours)
        articles = self.cnn_crawler.get_articles_by_time(cutoff_time)
        self.process_articles(articles)
    
    def process_articles_by_number(self, number: int = 10):
        if number <= 0:
            return
        
        articles = self.cnn_crawler.get_articles_by_number(number)
        self.process_articles(articles)

    def news_task(self):
        # Crawl CNN Lite website and save articles to SQLite database
        articles_saved = self.cnn_crawler.crawl()
        print(f"Articles saved: {articles_saved}")

        # Process the latest articles and send to Discord
        self.process_articles_by_number(articles_saved)

        # Start a new timer
        td.Timer(3600, self.news_task).start()
    
    def start(self):
        self.news_task()

if __name__ == "__main__":
    processor = NewsProcessor()
    processor.start()
