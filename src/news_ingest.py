import csv
import html
import re
import requests
from textblob import TextBlob
import os

"""
the newsapi is only accessible for 1 month of news history.
may need to switch to paid alternatives such as https://newsmesh.co/
"""

# api key for newsapi.org
newsapi_api_key = os.getenv("NEWSAPI_API_KEY")



# https://newsapi.org/docs/endpoints/everything
class NewsIngestor:

    def __init__(self, date=None):
        self.date = date


    # Clean noisy text in news article for sentiment analysis.
    # Returns a plain, readable string with non-words and junk removed.
    @staticmethod
    def clean_text_for_sentiment(raw_text: str) -> str:
        if not raw_text:
            return ""

        text = html.unescape(str(raw_text))
        text = re.sub(r"<[^>]+>", " ", text)  # strip HTML tags
        text = re.sub(r"\[\+\d+\s*chars\]", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"https?://\S+", " ", text)
        text = text.replace("’", "'").replace("“", '"').replace("”", '"')
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return ""

        try:
            sentences = [str(s).strip() for s in TextBlob(text).sentences]
        except Exception:
            sentences = re.split(r"[.!?]+", text)

        cleaned_sentences = []
        prev_norm = None

        for sentence in sentences:
            if not sentence:
                continue
            if sentence.strip().lower() == "by":
                continue

            try:
                tokens = [w for w in TextBlob(sentence).words if re.search(r"[A-Za-z]", w)]
            except Exception:
                tokens = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", sentence)

            tokens = [w for w in tokens if len(w) > 1 or w.lower() in {"a", "i"}]

            if len(tokens) < 3:
                continue

            norm = " ".join(tokens).lower()
            if norm == prev_norm:
                continue
            prev_norm = norm

            cleaned_sentences.append(" ".join(tokens))

        return ". ".join(cleaned_sentences)

    
    stock_list = "Nvidia OR NVDA OR Apple OR AAPL OR Microsoft OR MSFT OR Broadcom OR AVGO OR Palantir OR PLTR OR AMD OR Oracle OR ORCL OR Micron OR MU OR Cisco OR CSCO OR IBM"
    domain_list = 'theverge.com,wired.com,techcrunch.com,arstechnica.com,zdnet.com,engadget.com,cnet.com,tomshardware.com,anandtech.com,reuters.com,bloomberg.com,wsj.com,ft.com,economist.com,cnbc.com,forbes.com,nature.com,sciencemag.org,schneier.com,krebsonsecurity.com,darkreading.com,theregister.com,infoworld.com,linuxfoundation.org,infoq.com,github.blog'

    def _build_newsapi_url(self, date):
        return (
            'https://newsapi.org/v2/everything?'
            'domains=' + NewsIngestor.domain_list + '&'
            'q=' + NewsIngestor.stock_list + '&'
            'from=' + date + '&'
            'to=' + date + '&'
            'language=en&'
            'apiKey=' + newsapi_api_key
        )

    def _fetch_articles_payload(self, date):
        url = self._build_newsapi_url(date)
        try:
            response = requests.get(url, timeout=20)
            data = response.json()
        except Exception as exc:
            print(f"News request failed for {date}: {exc}")
            return []

        if data.get("status") != "ok":
            code = data.get("code", "unknown_error")
            message = data.get("message", "Unknown NewsAPI error")
            print(f"NewsAPI error for {date}: {code} - {message}")
            return []

        articles = data.get("articles") or []
        if not isinstance(articles, list):
            return []
        return articles
    
    def write_csv_VGT_stock_news(self, date):
        # the top 10 holding stock for the VGT ETF is: NVIDIA(NVDA), Apple(AAPL), Microsoft(MSFT),Broadcom(AVGO), Palantir(PLTR), AMD(AMD), Oracle(ORCL), Micron(MU), Cisco(CSCO), IBM(IBM)
        articles = self._fetch_articles_payload(date)

        # makes a csv file with the news articles for the given date, with the title, description, and content all concatenated together in one column called "article"
        with open(f"data/news_articles_{date}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["article"])

            for article in articles:
                cleaned_article = (
                    self.clean_text_for_sentiment(article.get("title")) +
                    self.clean_text_for_sentiment(article.get("description")) +
                    self.clean_text_for_sentiment(article.get("content"))
                )
                if cleaned_article:
                    writer.writerow([cleaned_article])

    # Backward-compatible alias used by older scripts.
    def get_VGT_stock_news(self, date):
        self.write_csv_VGT_stock_news(date)

    # returns a list of news articles for the given date, with the title, description, and content all concatenated together in one string for each article
    def get_news_articles(self, date):
        articles = self._fetch_articles_payload(date)

        # iterate through the articles and concatenate the title, description, and content together for each article, then clean the text for sentiment analysis and return a list of the cleaned articles
        news_articles = []
        
        for article in articles:
            cleaned_article = (
                self.clean_text_for_sentiment(article.get("title")) +
                self.clean_text_for_sentiment(article.get("description")) +
                self.clean_text_for_sentiment(article.get("content"))
            )
            if cleaned_article:
                news_articles.append(cleaned_article)

        return news_articles
"""
if __name__ == "__main__":
    date = "2026-02-16"
    NI = NewsIngestor()
    print(NI.get_news_articles(date))
"""