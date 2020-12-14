import requests
import time
import xmltodict
import os

baseurl = 'http://localhost:32400'
token = 'EDLzhCqbEjXvwQuziiCz'
tarProgress = 0.9 # 90% 이상 시청
intervalTime = 10
fragmentTime = 20 # 앞부분 몇 초를 잘라서 다운받을지
cacheDir = "" # 캐시폴더 디렉토리. 블랭크면 현재위치

###


def processFFMPEG(mediaPath):
    if not cacheDir :
        rootPath = os.getcwd()
    else:
        rootPath = cacheDir
    output = os.path.split(mediaPath)[-1]
    if os.path.exists(output) :
        return
    command = 'ffmpeg -i "' + mediaPath + '" -ss 0 -t ' + str(fragmentTime) + ' -vcodec copy -acodec copy "' + str(os.path.join(rootPath , output)) + '"'
    os.system(command)

def start():
    res = requests.get(baseurl + '/status/sessions?X-Plex-Token=' + token)
    xml = xmltodict.parse(res.text)['MediaContainer']
    if 'Video' not in xml:
        return
    if not isinstance(xml['Video'], list):
        sessions = [xml['Video']]
    else:
        sessions = xml['Video']
    for session in sessions:
        try:sessionProgress = float(session['@viewOffset']) / float(session['@duration'])
        except: continue # 현재 세션 구할 수 없음
        if not sessionProgress >= tarProgress: continue
        if session['@type'] in ['movie'] : continue
        if session['@type'] not in ['episode'] : continue # 현재는 episode만 지원(드라마)
        seasonNumber = session['@parentIndex']
        episodeNumber = session['@index']
        try:
            parentKey = session['@parentKey']
            seasonXml = xmltodict.parse(res.text)['MediaContainer']
            childrenKey = seasonXml['Directory']['@key']
            res = requests.get(baseurl + childrenKey + '?X-Plex-Token=' + token)
            childrenXml = xmltodict.parse(res.text)['MediaContainer']
            res = requests.get(baseurl + parentKey + '?X-Plex-Token=' + token)
        except:
            grandparentKey = session['@grandparentKey'] # 보통 단일시즌
            res = requests.get(baseurl + grandparentKey + '?X-Plex-Token=' + token)
            grandparentSeasonXml = xmltodict.parse(res.text)['MediaContainer']
            childrenKey = grandparentSeasonXml['Directory']['@key']
            res = requests.get(baseurl + childrenKey + '?X-Plex-Token=' + token)
            childrenXml = xmltodict.parse(res.text)['MediaContainer']

            childrenKey = childrenXml['Directory']['@key']
            res = requests.get(baseurl + childrenKey + '?X-Plex-Token=' + token)
            childrenXml = xmltodict.parse(res.text)['MediaContainer']
        episodesList = childrenXml['Video']
        episodesList.sort(key=lambda x:int(x['@index']))
        for index, child in enumerate(episodesList):
            if int(child['@parentIndex']) == int(seasonNumber) and int(child['@index']) == int(episodeNumber):
                # 다음 에피소드 구한다.
                try:nextEpisodeVideo = childrenXml['Video'][index + 1]
                except:continue # 다음 에피소드 없음. (다음 시즌이라던가)
                tarVidPaths = []
                if isinstance(nextEpisodeVideo['Media'], list):
                    tarVidPaths = [item['Part']['@file'] for item in nextEpisodeVideo['Media']]
                else:
                    tarVidPaths = [nextEpisodeVideo['Media']['Part']['@file']]
                for vidPath in tarVidPaths:
                    processFFMPEG(vidPath)
    return


if __name__ == '__main__':
    while True:
        start()
        time.sleep(intervalTime)
