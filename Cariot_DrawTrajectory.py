# -*- coding: utf-8 -*-

# -- このスクリプトについて --
# Cariotサーバに蓄積された走行データを API で取得して地図上にプロットするスクリプトです
#
#
# -- 使い方 --
# [1] 以下のサイトにアクセスする(APIアクセスキー, APIアクセスシークレットを取得するためのサイト)
# https://app.cariot.jp/auth/salesforce
#
# [2] [Salesforce組織種別を選択してください] という画面が表示されたら [Production/Dev] を選択
#
# [3] Salesforceのログイン画面が表示された場合は、Cariotシステム管理者のユーザ名・パスワードを入力する
#
# [3] 初期状態では[Salesforceデータ連携ユーザ情報]タブの情報が表示されているので、[APIアクセス情報]タブを選択する
#
# [4] 画面にAPIアクセスキー, APIアクセスシークレットが記載されているので、
#     このスクリプトの以下の api_access_key, api_access_secret の部分に値をペーストする
#
# [5] Pythonの最新版をインストールする
# https://www.python.org/
#
# [6] PCのターミナルで以下のコマンドを実行する(Pythonのライブラリをインストール)
# pip3 install requests,folium
#
# [7] ターミナルで以下のコマンドを実行する(このスクリプトを実行)
# python3 Cariot_DrawTrajectory.py


#---------------------------------------------------------------------
# ユーザー設定値
#---------------------------------------------------------------------

# APIアクセスキー (現在記載されているのはダミー)
api_access_key = 'xxxxxxxx'

# APIシークレット (現在記載されているのはダミー)
api_access_secret = 'xxxxxxxx'


#---------------------------------------------------------------------
# ライブラリの読み込み
#---------------------------------------------------------------------
import requests
import json
import datetime
import sys
import os
import copy
import folium
from folium.plugins import HeatMap


#---------------------------------------------------------------------
# メイン
#---------------------------------------------------------------------
def main():
    print ('\n\n--- Process Start --------------------------------\n')

    # 認証(APIトークンの取得)
    api_token = getAPItoken(api_access_key, api_access_secret)

    # デバイス一覧の取得
    deviceList = getDeviceList(api_token, 'Cariot_DeviceList.csv')

    # 走行データ一覧の取得
    tripList = getTripList(api_token, deviceList[0], 'Cariot_TripList.csv')

    # 走行データの取得
    #trip = getTrip(api_token, deviceList[0], tripList[0], 'Cariot_Trip.csv')

    # 走行データの描画
    #plotTripOnMap(trip, 'Cariot_Trip.html')

    # デモンストレーション(デバイスIDと走行データIDを直接指定して実行)
    deviceID = '20201211002'
    tripID   = '20201211002-1619901702375'
    tripCSV  = 'Cariot_Trip_DeviceID-' + deviceID + '.csv'
    tripHTML = 'Cariot_Trip_DeviceID-' + deviceID + '_TripID-' + tripID + '.html'
    trip     = getTrip(api_token, deviceID, tripID, tripCSV)
    plotTripOnMap(trip, tripHTML)

    print('\n----- Process Finished ------------------------------\n\n')


#---------------------------------------------------------------------
# Authentication: 認証(APIトークンの取得)
#---------------------------------------------------------------------
def getAPItoken(api_access_key, api_access_secret):

    # ログ出力
    #print('--getAPItoken() - Start')
    #print('api_access_key: ' + api_access_key)
    #print('api_access_secret: ' + api_access_secret)
    
    # ヘッダ部の設定
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    # データ部の設定
    data = ''
    data = data + '{'
    data = data + '"api_access_key":'
    data = data + '"' + api_access_key + '"' + ','
    data = data + '"api_access_secret":'
    data = data + '"' + api_access_secret + '"' + ','
    data = data + '}'

    # URL部の指定
    url = 'https://api.cariot.jp/api/login'

    # リクエスト実行
    res = requests.post(url, headers=headers, data=data)

    # リクエスト実行に対する応答の確認
    if(res.status_code != 200):
        ErrorEnd('APIトークンの取得に失敗しました (HTTPステータスコード:' + str(res.status_code) + ')\n' + str(res.text))

    # リクエスト実行結果の取得
    result = json.loads(res.text)
    timestamp = result['timestamp']
    api_token = result['api_token']
    print('timestamp: ' + str(UnixTimeUTC_to_DateTimeJST(timestamp)))
    print('api_access_key: ' + str(api_access_key))
    print('api_access_secret: ' + str(api_access_secret))
    print('api_token: ' + str(api_token))
    
    # ログ出力
    #print('--getAPItoken() - End')

    return api_token


#---------------------------------------------------------------------
# デバイス一覧(JSON形式テキスト)を取得
#---------------------------------------------------------------------
def getDeviceList(api_token, path_deviceListCSV):
    
    # ログ出力
    #print('--getDeviceList() - Start')
    #print('api_token: ' + api_token)
    #print('path_deviceListCSV: ' + path_deviceListCSV)
    
    # CSVのヘッダ行を出力
    with open(path_deviceListCSV, 'w') as f:
        f.write('device_id,device_uid,description,status\n')

    # リクエストのヘッダ部の設定
    headers = {
        'Accept': 'application/json',
        'x-auth-token': api_token
    }
    
    # デバイス情報を20件ずつ取得してゆく
    page, totalPage = 0, 1
    deviceList = []
    while (page < totalPage):

        # リクエストのURL部の設定
        url = 'https://api.cariot.jp/api/devices?&page=' + str(page)

        # リクエスト実行
        res = requests.get(url, headers=headers)

        # リクエスト実行に対する応答の確認
        if(res.status_code != 200):
            ErrorEnd('デバイス一覧の取得に失敗しました (HTTPステータスコード:' + str(res.status_code) + ')\n' + str(res.text))
        
        # リクエスト実行結果(JSON形式テキスト)をデコード
        data = json.loads(res.text)
        #print(data.keys())

        # リクエスト実行結果に記載されているデータ数を取得
        dataCount = len(data['items'])

        # CSVのデータ行を出力すると同時に、デバイスIDを戻り値配列に格納
        with open(path_deviceListCSV, 'a') as f:
            for i in range(dataCount):
                #print(data['items'][i].keys())
                writeLine = ''
                writeLine = writeLine + str(data['items'][i]['device_id']) + ','
                writeLine = writeLine + str(data['items'][i]['device_uid']) + ','
                writeLine = writeLine + str(data['items'][i]['description']) + ','           
                writeLine = writeLine + str(data['items'][i]['status'])
                f.write(writeLine + '\n')
                deviceList.append(str(data['items'][i]['device_id']))

        # 全ページ数を取得(全データを取得するには何回リクエストを投げれば良いかを取得)
        if(page == 0):
            totalPage = data['total_page']

        # ページ数をカウントアップ
        page = page+1

    # ログ出力
    print('デバイス数: ' + str(len(deviceList)))
    #print('--getDeviceList() - End')

    return deviceList


#---------------------------------------------------------------------
# 指定したデバイスの走行データ一覧を取得
#---------------------------------------------------------------------
def getTripList(api_token, deviceID, path_tripListCSV):
    
    # ログ出力
    #print('--getTripList() - Start')
    #print('api_token: ' + api_token)
    #print('deviceID: ' + deviceID)
    #print('path_tripListCSV: ' + path_tripListCSV)

    # CSVのヘッダ行を出力
    with open(path_tripListCSV, 'w') as f:
        f.write('device_id,trip_id,created_at(JST),device_sn,distance_km,duration_m,started_at(JST),start_lat,start_lon,start_addr,ended_at(JST),end_lat,end_lon,end_addr,fuel_cost_usd,max_speed,max_acc\n')
    
    # リクエストのヘッダ部の設定
    headers = {
        'Accept': 'application/json',
        'x-auth-token': api_token
    }

    # リクエストのURL部の指定
    url = 'https://api.cariot.jp/api/trips/' + str(deviceID)

    # リクエスト実行
    res = requests.get(url, headers=headers)

    # リクエスト実行結果の確認
    if(res.status_code != 200):
        ErrorEnd('走行データ一覧の取得に失敗しました (HTTPステータスコード:' + str(res.status_code) + ')\n' + str(res.text))

    # リクエスト実行結果(JSON形式テキスト)をデコード
    data = json.loads(res.text)
    #print(data.keys())

    # 走行データ数を取得
    dataCount = data['count']
    #print(dataCount)

    # CSVのデータ行を出力すると同時に、走行データIDを戻り値配列に格納
    tripList = []
    with open(path_tripListCSV, 'a') as f:
        for i in range(dataCount):
            #print(data['items'][i].keys())
            writeLine = ''
            writeLine = writeLine + str(deviceID) + ','
            writeLine = writeLine + str(data['items'][i]['trip_id']) + ','
            writeLine = writeLine + str(UnixTimeUTC_to_DateTimeJST(data['items'][i]['created_at'])) + ','
            writeLine = writeLine + str(data['items'][i]['device_sn']) + ','
            writeLine = writeLine + str(data['items'][i]['distance_km']) + ','
            writeLine = writeLine + str(data['items'][i]['duration_m']) + ','
            writeLine = writeLine + str(UnixTimeUTC_to_DateTimeJST(data['items'][i]['started_at'])) + ','
            writeLine = writeLine + str(data['items'][i]['start_lat']) + ','
            writeLine = writeLine + str(data['items'][i]['start_lon']) + ','
            writeLine = writeLine + str(data['items'][i]['start_addr']) + ','
            writeLine = writeLine + str(UnixTimeUTC_to_DateTimeJST(data['items'][i]['ended_at'])) + ','
            writeLine = writeLine + str(data['items'][i]['end_lat']) + ','
            writeLine = writeLine + str(data['items'][i]['end_lon']) + ','
            try: # 走行中は end_addr に値が入っておらずアクセスするとエラーになる
                writeLine = writeLine + str(data['items'][i]['end_addr']) + ','
            except:
                writeLine = writeLine + ','
            writeLine = writeLine + str(data['items'][i]['fuel_cost_usd']) + ','
            writeLine = writeLine + str(data['items'][i]['max_speed']) + ','              
            writeLine = writeLine + str(data['items'][i]['max_acc'])
            f.write(writeLine + '\n')
            tripList.append(str(data['items'][i]['trip_id']))

    # ログ出力
    if(dataCount == 0):
        ErrorEnd('指定されたデバイスの走行データは 0件でした。処理を終了します。' + str(dataCount) + '  (デバイスID:' + deviceID + ')')
    else:
        print('走行データ数: ' + str(dataCount) + '  (デバイスID:' + deviceID + ')')
    #print('--getTripList() - End')

    return tripList


#---------------------------------------------------------------------
# 指定したデバイスの指定した走行データを取得
#---------------------------------------------------------------------
def getTrip(api_token, deviceID, tripID, path_tripCSV):
    
    # ログ出力
    #print('--getTrip() - Start')
    #print('api_token: ' + api_token)
    #print('deviceID: ' + deviceID)
    #print('tripID: ' + tripID)
    #print('path_tripCSV: ' + path_tripCSV)

    # CSVのヘッダ行を出力
    with open(path_tripCSV, 'w') as f:
        f.write('device_id,trip_id,event_id,gps_time(JST),lat,lon,direction,heading,speed,acc\n')
    
    # リクエストのヘッダ部の設定
    headers = {
        'Accept': 'application/json',
        'x-auth-token': api_token
    }

    # リクエストのURL部の指定
    url = 'https://api.cariot.jp/api/trips/' + str(deviceID) + '/' + str(tripID)

    # リクエスト実行
    res = requests.get(url, headers=headers)

    # リクエスト実行結果の確認
    if(res.status_code != 200):
        ErrorEnd('走行データの取得に失敗しました (HTTPステータスコード:' + str(res.status_code) + ')\n' + str(res.text))

    # リクエスト実行結果(JSON形式テキスト)をデコード
    data = json.loads(res.text)
    #print(data.keys())

    # 走行データ数を取得
    dataCount = data['log_count']

    # CSVのデータ行を出力すると同時に、走行データを戻り値配列に格納
    tripData = []
    tripDetail = []
    with open(path_tripCSV, 'a') as f:
        for i in range(dataCount):
            #print(data['items'][i].keys())
            writeLine = ''
            writeLine = writeLine + str(data['logs'][i]['device_sn']) + ','
            writeLine = writeLine + str(tripID) + ','
            writeLine = writeLine + str(data['logs'][i]['event_id']) + ','
            writeLine = writeLine + str(UnixTimeUTC_to_DateTimeJST(data['logs'][i]['gps_time'])) + ','
            writeLine = writeLine + str(data['logs'][i]['lat']) + ','
            writeLine = writeLine + str(data['logs'][i]['lon']) + ','
            writeLine = writeLine + str(data['logs'][i]['direction']) + ','
            writeLine = writeLine + str(data['logs'][i]['heading']) + ','
            writeLine = writeLine + str(data['logs'][i]['speed']) + ','
            writeLine = writeLine + str(data['logs'][i]['acc'])
            f.write(writeLine + '\n')

            #tripDetail.append(str(data['logs'][i]['device_sn']))
            #tripDetail.append(str(tripID))
            #tripDetail.append(str(UnixTimeUTC_to_DateTimeJST(data['logs'][i]['gps_time'] / 1000)))
            #tripDetail.append(str(data['logs'][i]['speed']))
            tripDetail.append(str(data['logs'][i]['lat']))
            tripDetail.append(str(data['logs'][i]['lon']))
            tripData.append(copy.copy(tripDetail))
            tripDetail.clear()

    # ログ出力
    if(dataCount == 0):
        ErrorEnd('指定された走行データの緯度経度情報は 0件でした。処理を終了します。' + '  (デバイスID:' + deviceID + ', 走行データID:'+ tripID +')')
    else: 
        print('緯度経度個数: ' + str(len(tripData)) + '  (デバイスID:' + deviceID + ', 走行データID:'+ tripID +')')
    #print('--getTrip() - End')

    return tripData


#---------------------------------------------------------------------
# 走行データを地図上にプロットする
#---------------------------------------------------------------------
def plotTripOnMap(trip, path_tripHTML):

    # ログ出力
    #print('--plotTripOnMap() - Start')
    #print('path_tripHTML: ' + path_tripHTML)

    # 滞在判定値(何分以上同じ井戸経度にいたら滞在とするか)
    stayMinutes = 5

    # Tripデータの内容をチェック
    stayCount, prevLat, prevLon = 0,0,0
    stays = []
    for i in range(len(trip)):

        # 緯度経度を丸める(foliumが対応している桁数まで落とす)
        lat = round(float(trip[i][0]),5)
        lon = round(float(trip[i][1]),5)
        trip[i][0] = lat
        trip[i][1] = lon
        
        # 停車位置を抽出 (同じ緯度経度が連続している部分を抽出する)
        if ((lat == prevLat) and (lon == prevLon)):
            stayCount = stayCount + 1
        elif (stayCount > stayMinutes*20):
            stayCount = 1
            stays.append([prevLat,prevLon])
        else:
            stayCount = 1
        prevLat = lat
        prevLon = lon
    
    # 地図の中心座標を設定
    LatLon_at_maxLat = max(trip, key = lambda x:x[0])
    LatLon_at_minLat = min(trip, key = lambda x:x[0])
    LatLon_at_maxLon = max(trip, key = lambda x:x[1])
    LatLon_at_minLon = min(trip, key = lambda x:x[1])
    fOriginLat = (float(LatLon_at_maxLat[0]) + float(LatLon_at_minLat[0]))/2
    fOriginLon = (float(LatLon_at_maxLon[1]) + float(LatLon_at_minLon[1]))/2

    # 地図の作成
    mapStyle = ['OpenStreetMap','Stamen Terrain','Stamen Watercolor', 'CartoDB positron', 'CartoDB dark_matter']
    osm = folium.Map(location=[fOriginLat,fOriginLon], zoom_start=13, tiles=mapStyle[4])

    # 地図上に軌跡をプロット
    line = folium.PolyLine(locations=trip)
    osm.add_child(line)

    # 地図上に停車地点をプロット
    for i in range(len(stays)):
        iframe = folium.IFrame('Stayed over ' + str(stayMinutes) + ' minutes')
        popup = folium.Popup(iframe, min_width=200, max_width=500, min_height=40, max_height=40)
        folium.Marker(
            location=[float(stays[i][0]), float(stays[i][1])],
            popup=popup,
            icon=folium.Icon(color='orange', icon='briefcase')
        ).add_to(osm)
    
    # 地図上に走行開始地点をプロット
    folium.Marker(
        location=[float(trip[0][0]), float(trip[0][1])],
        popup='Start',
        icon=folium.Icon(color='purple', icon='home')
    ).add_to(osm)

    # 地図上に走行終了地点をプロット
    folium.Marker(
        location=[float(trip[len(trip)-1][0]), float(trip[len(trip)-1][1])],
        popup='Goal',
        icon=folium.Icon(color='purple', icon='flag')
    ).add_to(osm)

    # 地図上にヒートマップをプロット
    HeatMap(trip, radius=10, blur=3, gradient={'0.25':'blue', '0.50':'cyan', '1.00':'white'}).add_to(osm)

    # 地図を出力
    osm.save(path_tripHTML)

    # ログ出力
    print('出力ファイル: ' + os.path.abspath(path_tripHTML))
    #print('--plotTripOnMap() - End')


#---------------------------------------------------------------------
# UNIX Time(UTC,ミリ秒) を DateTime(JST,秒) に変換する
#---------------------------------------------------------------------
def UnixTimeUTC_to_DateTimeJST(UnixTimeUTC):

    # UNIX Time(UTC,ミリ秒)

    # DateTime(UTC,ミリ秒)
    DateTimeUTC = datetime.datetime.fromtimestamp(float(UnixTimeUTC) / 1000)

    # UNIX Time(JST,ミリ秒)
    UnixTimeJST = float(UnixTimeUTC) + 9*60*60*1000

    # DateTime(JST,秒)
    DateTimeJST = datetime.datetime.fromtimestamp(float(UnixTimeJST) / 1000)

    # ログ出力
    #print('UnixTimeUTC: ' + str(UnixTimeUTC))
    #print('DateTimeUTC: ' + str(DateTimeUTC))
    #print('UnixTimeJST: ' + str(UnixTimeJST))
    #print('DateTimeJST: ' + str(DateTimeJST))
    
    return str(DateTimeJST)


#---------------------------------------------------------------------
# エラー終了
#---------------------------------------------------------------------
def ErrorEnd(msg):

    # エラーメッセージを表示
    print('\n' + msg + '\n')

    # プロセス終了
    sys.exit()


#---------------------------------------------------------------------
# エントリーポイント
#---------------------------------------------------------------------
if __name__ == '__main__':
    main()


#---------------------------------------------------------------------
# References
#---------------------------------------------------------------------
#
# [1] Cariot 公式サイト
# https://www.cariot.jp/
#
# [2] CariotAPI 公式サイト
# https://api-doc.cariot.jp/
#
# [3] Pythonでcurlコマンドと同等の処理を実行する方法
# https://intellectual-curiosity.tokyo/2019/08/31/python%E3%81%A7curl%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89%E3%81%A8%E5%90%8C%E7%AD%89%E3%81%AE%E5%87%A6%E7%90%86%E3%82%92%E5%AE%9F%E8%A1%8C%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95/
#
# [4] 地図で利用できるアイコン
# https://fontawesome.com/icons?d=gallery&p=2
#
#---------------------------------------------------------------------
# End
