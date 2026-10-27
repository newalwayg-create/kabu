"""米国株が動いた翌日に、事業でつながる日本株がどれだけ同じ向きに動くかを調べる。

翌日の終値・寄り付き・寄り付き後それぞれとの相関と、SOXとS&P500の動きを差し引いた後の上乗せ分を、2019〜23年と2024年以降に分けて測る。
"""
import pandas as pd, numpy as np, yfinance as yf, warnings; warnings.filterwarnings('ignore')
P=[('MU','285A','マイクロン','キオクシア'),('WDC','285A','ウエスタンデジタル','キオクシア'),('SNDK','285A','サンディスク','キオクシア'),
   ('NVDA','6857','NVIDIA','アドバンテスト'),('NVDA','9984','NVIDIA','ソフトバンクG'),('AMAT','8035','アプライド','東京エレクトロン'),
   ('LRCX','8035','ラム','東京エレクトロン'),('LRCX','6525','ラム','KOKUSAI'),('ASML','6920','ASML','レーザーテック'),('TSM','6146','TSMC','ディスコ'),
   ('AVGO','4062','ブロードコム','イビデン'),('GLW','5803','コーニング','フジクラ'),('GLW','5802','コーニング','住友電工'),('VRT','5803','バーティブ','フジクラ'),
   ('ORCL','3778','オラクル','さくらインターネット'),('CRWV','3778','コアウィーブ','さくらインターネット'),('TSLA','6752','テスラ','パナソニック'),
   ('AAPL','6981','アップル','村田製作所'),('CAT','6301','キャタピラー','コマツ'),('XOM','1605','エクソン','INPEX'),
   ('GEV','6501','GEベルノバ','日立'),('JPM','8306','JPモルガン','三菱UFJ'),('MU','3436','マイクロン','SUMCO')]
us=sorted({p[0] for p in P}|{'^SOX','^GSPC'}); jp=sorted({p[1]+'.T' for p in P})
U=yf.download(us,start='2019-01-01',progress=False,auto_adjust=True)
J=yf.download(jp,start='2019-01-01',progress=False,auto_adjust=True)
ur=U['Close'].pct_change(fill_method=None); jr=J['Close'].pct_change(fill_method=None)
gap=(J['Open']/J['Close'].shift()-1); oc=J['Close']/J['Open']-1
# map each JP day to previous US session
jd=jr.index; ud=ur.index
prev=pd.Series([ud[ud<t][-1] if (ud<t).any() else pd.NaT for t in jd],index=jd)
UA=ur.reindex(prev.values); UA.index=jd
rows=[]
for u,j,un,jn in P:
    t=j+'.T'
    df=pd.DataFrame({'u':UA[u],'sox':UA['^SOX'],'spx':UA['^GSPC'],'j':jr[t],'g':gap[t],'oc':oc[t]}).dropna()
    df=df[(df.j.abs()<.3)]
    if len(df)<150: continue
    def part(d):
        X=np.column_stack([np.ones(len(d)),d.sox,d.spx,d.u]); c,*_=np.linalg.lstsq(X,d.j,rcond=None); e=d.j-X@c
        se=np.sqrt(np.diag(e@e/(len(d)-4)*np.linalg.inv(X.T@X))); return c[3],c[3]/se[3]
    b,tv=part(df); bi,ti=part(df.loc[:'2023']) if len(df.loc[:'2023'])>150 else (np.nan,np.nan); bo,to=part(df.loc['2024':])
    big=df[df.u<=-0.04]
    rows.append({'米国':un,'日本':jn,'開始':str(df.index[0].date()),'日数':len(df),'翌日相関':round(df.u.corr(df.j),2),'寄り付き相関':round(df.u.corr(df.g),2),
                 '寄り後(日中)相関':round(df.u.corr(df.oc),2),'SOX等を除いた上乗せ係数':round(b,2),'t':round(tv,1),'2019-23 t':round(ti,1) if ti==ti else '-','2024- t':round(to,1),
                 '米-4%以下の翌日 日本平均%':round(big.j.mean()*100,1) if len(big)>=5 else '-','回数':len(big),'同じ向き':round((np.sign(big.j)==-1).mean(),2) if len(big)>=5 else '-'})
R=pd.DataFrame(rows).sort_values('翌日相関',ascending=False); pd.set_option('display.width',300); print(R.to_string(index=False))
