import pytest
import tempfile
import os
import pandas as pd
from pathlib import Path
from src.storage.data_storage import DataStorage

class TestDataStorage:
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    @pytest.fixture
    def data_storage(self, temp_dir):
        return DataStorage(results_dir=temp_dir)

    def test_save_and_load_tickers_to_csv(self, data_storage):
        url_name = "TPS SCANNER"
        tickers = ["AAPL", "GOOGL", "MSFT"]
        filepath = data_storage.save_tickers_to_csv(url_name, tickers)
        assert os.path.exists(filepath)
        records = data_storage.load_tickers_from_csv(filepath)
        assert len(records) == 3
        assert records[0]['url_name'] == url_name
        assert records[0]['ticker_symbol'] == "AAPL"

    def test_save_tickers_to_csv_no_tickers(self, data_storage):
        with pytest.raises(ValueError):
            data_storage.save_tickers_to_csv("TPS SCANNER", [])

    def test_get_latest_results(self, data_storage):
        url_name = "TPS SCANNER"
        tickers = ["AAPL"]
        filepath = data_storage.save_tickers_to_csv(url_name, tickers)
        latest = data_storage.get_latest_results(url_name)
        assert latest == filepath

    def test_list_result_files(self, data_storage):
        url_name = "TPS SCANNER"
        tickers = ["AAPL", "GOOGL"]
        data_storage.save_tickers_to_csv(url_name, tickers)
        results = data_storage.list_result_files()
        assert len(results) == 1
        assert results[0]['url_name'] == url_name
        assert results[0]['ticker_count'] == 2

    def test_delete_result_file(self, data_storage):
        url_name = "TPS SCANNER"
        tickers = ["AAPL"]
        filepath = data_storage.save_tickers_to_csv(url_name, tickers)
        filename = Path(filepath).name
        assert data_storage.delete_result_file(filename) is True
        assert not os.path.exists(filepath)

    def test_get_ticker_count(self, data_storage):
        url_name = "TPS SCANNER"
        tickers = ["AAPL", "GOOGL"]
        filepath = data_storage.save_tickers_to_csv(url_name, tickers)
        count = data_storage.get_ticker_count(filepath)
        assert count == 2

    def test_load_tickers_from_csv_invalid_file(self, data_storage, temp_dir):
        invalid_file = temp_dir / "invalid.csv"
        with open(invalid_file, 'w') as f:
            f.write("not,csv,content\n1,2,3")
        with pytest.raises(Exception):
            data_storage.load_tickers_from_csv(str(invalid_file)) 