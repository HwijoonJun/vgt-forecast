import yfinance as yf

class StockIngestor:

    def __init__(self):
        pass

    def get_stock_data_for_VGT(self, start_date, end_date):
        """
        Fetch historical stock data for the stocks for the Vanguard Information Technology ETF (VGT) between the specified start and end dates.
        NVIDIA(NVDA), Apple(AAPL), Microsoft(MSFT),Broadcom(AVGO), Palantir(PLTR), AMD(AMD), Oracle(ORCL), Micron(MU), Cisco(CSCO), IBM(IBM)
        """

        stock_symbols = ['NVDA', 'AAPL', 'MSFT', 'AVGO', 'PLTR', 'AMD', 'ORCL', 'MU', 'CSCO', 'IBM']
        stock_data = {}

        try:
            tickers = yf.Tickers(" ".join(stock_symbols))
            data = yf.download(stock_symbols, start=start_date, end=end_date)
            print(data.head())
        except Exception as e:
            print(f"Error fetching data for VGT stocks: {e}")

        return stock_data

    # get the combined price increase and percentage increase for VGT

    def get_VGT_percentage_change(start_date, end_date):
        """
        Calculate the price increase and percentage increase for the given stock data.
        """
        stock_name = "VGT"
        stock_data = yf.download([stock_name], start=start_date, end=end_date)
    
        VGT_percentage_change = []

        for index, row in stock_data.iterrows():
            percentage_change = (row["Close"][stock_name] - row["Open"][stock_name]) / row["Open"][stock_name] * 100
            VGT_percentage_change.append((index.strftime("%Y-%m-%d"), percentage_change))
            
