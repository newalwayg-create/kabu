"""日本の大型株ユニバースの株価・決算履歴・指標を取得して data/research/ に保存する。"""
import json, sys, time
from pathlib import Path
import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parents[1] / "data" / "research"
UNIVERSE = {
 "7203":"トヨタ自動車","6758":"ソニーG","9984":"ソフトバンクG","8306":"三菱UFJ","8316":"三井住友FG","8411":"みずほFG","9432":"NTT","9433":"KDDI","9434":"ソフトバンク",
 "6098":"リクルート","4063":"信越化学","6501":"日立","6503":"三菱電機","6702":"富士通","6752":"パナソニック","6954":"ファナック","6981":"村田製作所","6971":"京セラ","6762":"TDK",
 "6594":"ニデック","6723":"ルネサス","8035":"東京エレクトロン","7735":"SCREEN","6146":"ディスコ","6857":"アドバンテスト","6920":"レーザーテック","4568":"第一三共","4502":"武田薬品",
 "4519":"中外製薬","4503":"アステラス","4523":"エーザイ","8058":"三菱商事","8031":"三井物産","8001":"伊藤忠","8053":"住友商事","8002":"丸紅","7974":"任天堂","3382":"セブン&アイ",
 "2914":"JT","7267":"ホンダ","7201":"日産","7269":"スズキ","7011":"三菱重工","7012":"川崎重工","7013":"IHI","6301":"コマツ","6367":"ダイキン","5401":"日本製鉄","5108":"ブリヂストン",
 "4452":"花王","4911":"資生堂","9020":"JR東日本","9022":"JR東海","9101":"日本郵船","9104":"商船三井","9107":"川崎汽船","8766":"東京海上","8725":"MS&AD","8630":"SOMPO","8591":"オリックス",
 "8604":"野村HD","8601":"大和証券G","8801":"三井不動産","8802":"三菱地所","1925":"大和ハウス","1928":"積水ハウス","4661":"OLC","6178":"日本郵政","9201":"JAL","9202":"ANA",
 "4543":"テルモ","7741":"HOYA","6326":"クボタ","5803":"フジクラ","5802":"住友電工","6526":"ソシオネクスト","3436":"SUMCO","4062":"イビデン","6963":"ローム","4689":"LINEヤフー",
 "4755":"楽天G","2802":"味の素","2502":"アサヒGHD","2503":"キリンHD","4901":"富士フイルム","7751":"キヤノン","6902":"デンソー","7270":"SUBARU","7733":"オリンパス","8015":"豊田通商",
 "5020":"ENEOS","1605":"INPEX","9531":"東京ガス","9501":"東京電力","6532":"ベイカレント","3659":"ネクソン","9766":"コナミG","7832":"バンダイナムコ","9697":"カプコン","285A":"キオクシア",
 "6861":"キーエンス","9983":"ファーストリテイリング","6273":"SMC","7974":"任天堂","8267":"イオン","9843":"ニトリ","4307":"野村総研","6701":"NEC","6506":"安川電機","6645":"オムロン",
}
INFO_KEYS = ["currentPrice","trailingPE","forwardPE","priceToBook","dividendYield","targetMeanPrice","targetHighPrice","targetLowPrice","recommendationMean",
             "numberOfAnalystOpinions","marketCap","fiftyTwoWeekHigh","fiftyTwoWeekLow","earningsGrowth","revenueGrowth","returnOnEquity","sector","industry"]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tickers = [c + ".T" for c in UNIVERSE] + ["^N225", "1475.T", "^SOX", "JPY=X"]
    px = yf.download(tickers, start="2018-06-01", auto_adjust=True, progress=False, group_by="ticker", threads=True)
    px.to_pickle(OUT / "prices.pkl")
    info, earn, cal = {}, [], {}
    for i, c in enumerate(UNIVERSE):
        t = c + ".T"; tk = yf.Ticker(t)
        try:
            inf = tk.info; info[t] = {k: inf.get(k) for k in INFO_KEYS}
        except Exception as e:
            info[t] = {"error": str(e)[:80]}
        try:
            ed = tk.get_earnings_dates(limit=40)
            if ed is not None and len(ed):
                ed = ed.reset_index().rename(columns={"Earnings Date": "ts"}); ed["ticker"] = t; earn.append(ed)
        except Exception as e:
            pass
        try:
            cal[t] = {k: str(v) for k, v in (tk.calendar or {}).items()}
        except Exception:
            pass
        if i % 20 == 0: print(i, t, flush=True)
    pd.DataFrame(info).T.to_csv(OUT / "info.csv")
    pd.concat(earn).to_pickle(OUT / "earnings.pkl")
    json.dump(cal, open(OUT / "calendar.json", "w"), ensure_ascii=False)
    json.dump(UNIVERSE, open(OUT / "names.json", "w"), ensure_ascii=False)
    print("done", len(info), "earnings rows", sum(len(e) for e in earn))

if __name__ == "__main__":
    main()
