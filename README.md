# Cafe Inventory Control App

Flaskで作成したカフェ向け在庫管理アプリです。  
小さな店舗でも使える、シンプルで実用的な在庫管理を目指しました。

## 機能
- 商品登録
- 在庫移動（入庫・出庫）
- ユーザー管理

## 起動方法

1. 必要ライブラリをインストール
pip install -r requirements.txt

2. アプリ起動
python app.py

ブラウザで  
http://127.0.0.1:5000  
を開きます。

## データベース作成

sqlite3 inventory.db < schema.sql

## 今後の予定
- CSV出力
- 在庫アラート
- ログイン機能

## 作者
地域の商品や想いをお客様に届けることを大切に、  
店舗運営経験をもとに開発しました。
