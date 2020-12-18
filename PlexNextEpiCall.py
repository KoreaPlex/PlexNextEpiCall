import requests
import time
import xmltodict
import os

baseurl = 'http://localhost:32400'
token = 'xx'
tarProgress = 0.7 # 70% 이상 시청
intervalTime = 10
fragmentTime = 20 # 앞부분 몇 초를 잘라서 다운받을지
cacheDir = "" # 캐시폴더 디렉토리. 블랭크면 현재위치

###
cannotGetDurationThenAnalyzeAndRefresh = True

directoryMapping = {
    '/mnt/g2/test/koreaDrama' : '/mnt/total/koreaDrama',
    '/mnt/exam1/2222' : '/test/test/test'
}

###


def processFFMPEG(mediaPath , nextEpisodeVideo):
    if not cacheDir :
        rootPath = os.getcwd()
    else:
        rootPath = cacheDir
    output = os.path.split(mediaPath)[-1]
    if os.path.exists(output) :
        return
    # mediaPath 처리
    for path in directoryMapping:
        if path in mediaPath:
            mediaPath = mediaPath.replace(path , directoryMapping[path])
    # analyze도 한다
    t1 = requests.put(url=baseurl + nextEpisodeVideo['@key'] + '/analyze?X-Plex-Token=' + token)
    #t2 = requests.put(url=baseurl + nextEpisodeVideo['@key']  + '/refresh?X-Plex-Token=' + token)
    command = 'ffmpeg -i "' + mediaPath + '" -ss 0 -t ' + str(fragmentTime) + ' -vcodec copy -acodec copy -n "' + str(os.path.join(rootPath , output)) + '"'
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
        try:
            sessionProgress = float(session['@viewOffset']) / float(session['@duration'])
        except: # 현재 세션이 시청중인 동영상이 analyze가 안 된 경우 duration을 call 할 수 없음. # 강제로 analyze와 refreshing해야
            if cannotGetDurationThenAnalyzeAndRefresh:
                try:mediaKey = xml['Video']['@key']
                except:continue # Vid Key 를 구할 수 없으면 외부스트림일 확률.
                t1 = requests.put(url=baseurl + mediaKey + '/analyze?X-Plex-Token=' + token)
            continue # 현재 세션 구할 수 없음
        if not sessionProgress >= tarProgress: continue
        if session['@type'] in ['movie'] : continue
        if session['@type'] not in ['episode'] : continue # 현재는 episode만 지원(드라마)
        seasonNumber = session['@parentIndex']
        episodeNumber = session['@index']
        try:
            parentKey = session['@parentKey']
            res = requests.get(baseurl + parentKey + '?X-Plex-Token=' + token)
            seasonXml = xmltodict.parse(res.text)['MediaContainer']
            if 'Directory' in seasonXml:
                childrenKey = seasonXml['Directory']['@key'] # 멀티시즌인데 단일시즌만 있는경운듯
            else:
                if not isinstance(seasonXml['Video'] , list):
                    parentKey = seasonXml['Video']['@parentKey']
                    res = requests.get(baseurl + parentKey + '?X-Plex-Token=' + token)
                    parentXml = xmltodict.parse(res.text)['MediaContainer']
                    childrenKey = parentXml['Directory']['@key'] # 이 경우 멀티시즌인데 멀티시즌이 실제로 있는 경우
                else: # 여러명이 시청하는 경운데;;;

                    parentKey = seasonXml['Video']['@parentKey']
                    res = requests.get(baseurl + parentKey + '?X-Plex-Token=' + token)
                    parentXml = xmltodict.parse(res.text)['MediaContainer']
                    childrenKey = parentXml['Directory']['@key'] # 이 경우 멀티시즌인데 멀티시즌이 실제로 있는 경우
            res = requests.get(baseurl + childrenKey + '?X-Plex-Token=' + token)
            childrenXml = xmltodict.parse(res.text)['MediaContainer']
            res = requests.get(baseurl + parentKey + '?X-Plex-Token=' + token)
        except:
            grandparentKey = session['@grandparentKey'] # 보통 단일시즌인 경우
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

                if isinstance(nextEpisodeVideo['Media'], list):
                    tarVidPaths = [item['Part']['@file'] for item in nextEpisodeVideo['Media']]
                else:
                    tarVidPaths = [nextEpisodeVideo['Media']['Part']['@file']]
                for vidPath in tarVidPaths:
                    processFFMPEG(vidPath , nextEpisodeVideo)
    return


if __name__ == '__main__':
    while True:
        start()
        time.sleep(intervalTime)
