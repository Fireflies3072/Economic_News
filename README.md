# Economic_News

This project crawls CNN Lite for news articles, stores them in a SQLite database, analyzes them using Google's Gemini AI, and sends the results to Discord using the Discord.py library.

## Features

- Crawls CNN Lite for news articles
- Stores articles in a SQLite database
- Skips articles that already exist in the database
- Analyzes article content using Google's Gemini AI
- Sends analysis results to Discord via webhook using Discord.py
- Supports rotating user agents and proxies
- Handles long analysis by splitting into multiple embed fields

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   DISCORD_TOKEN=your_discord_application_token_here
   DISCORD_CHANNEL=your_discord_channel_here
   ```

## Usage

Run the project:

```cmd
python3 economic_news.py
```

Run the project in the background:

```cmd
nohup python3 economic_news.py &
```

This will:
1. Crawl CNN Lite for new articles every hour
2. Save new articles to the SQLite database
3. Get the latest articles from the database
4. Analyze the articles with Gemini AI
5. Send the analysis to Discord using Discord.py

Find running python programs:

```cmd
ps aux | grep python
```

Kill the running program (pid):

```cmd
kill -9 pid
```

## Database

The SQLite database (`cnn_news.db`) contains a single table `articles` with the following columns:
- `id`: Auto-incrementing primary key
- `title`: Article title
- `url`: Article URL (unique)
- `time`: Publication timestamp
- `content`: Article content

## Requirements

- Python 3.7+
- Google Gemini API key
- Discord Application Token
- Discord Channel ID