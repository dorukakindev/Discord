import os
import sys

import pytest

BOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BOT)
os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("WORK", os.path.join(os.path.dirname(os.path.abspath(__file__)), "_work_test"))


@pytest.fixture()
def film():
    return {
        "id": 42, "ingilizce_adi": "Örnek Film", "orijinal_adi": "Sample Film",
        "yili": "2020", "kategori": "Film", "yonetmen": "Yönetmen Kişi",
        "tur": "Drama", "sure": "120", "dil": "İngilizce",
        "imdb_puani": "8.1", "lb_puani": "4.2", "metascore": "80",
        "rotten_puani": "91%", "tmdb_puani": "7.9", "nutpuan": "77",
        "icm_lists": "5", "icm_favs": "120",
        "sana_uygunluk": "4/5", "uygunluk_guveni": "0.85",
        "uygunluk_gerekcesi": "tema uyumu",
        "konu_ozeti": "Kısa özet.", "imdb_id": "tt1234567",
        "imdb_link": "https://www.imdb.com/title/tt1234567/",
        "arsiv_no": "123",
    }
